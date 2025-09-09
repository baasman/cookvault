import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List

import stripe
from flask import current_app

from app import db
from app.models.payment import (
    Subscription, SubscriptionTier, SubscriptionStatus,
    Payment, PaymentType, PaymentStatus,
    CookbookPurchase
)
from app.models.user import User
from app.models.recipe import Cookbook


logger = logging.getLogger(__name__)


class StripeService:
    """Service for handling all Stripe payment operations."""
    
    def __init__(self):
        """Initialize Stripe with API key from config."""
        stripe_key = current_app.config.get('STRIPE_SECRET_KEY')
        logger.info(f"Initializing StripeService - API key present: {bool(stripe_key)}")
        if stripe_key:
            logger.info(f"Stripe API key starts with: {stripe_key[:7]}...")
        
        stripe.api_key = stripe_key
        self.webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
        
        if not stripe.api_key:
            logger.error("Stripe API key not configured")
            raise ValueError("Stripe API key not configured")

    def create_customer(self, user: User) -> str:
        """Create a Stripe customer for a user."""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.username,
                metadata={
                    'user_id': str(user.id),
                    'username': user.username
                }
            )
            
            # Update user with Stripe customer ID
            user.stripe_customer_id = customer.id
            db.session.commit()
            
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for user {user.id}: {str(e)}")
            raise

    def get_or_create_customer(self, user: User) -> str:
        """Get existing Stripe customer ID or create a new customer."""
        if user.stripe_customer_id:
            try:
                # Verify customer still exists in Stripe
                stripe.Customer.retrieve(user.stripe_customer_id)
                return user.stripe_customer_id
            except stripe.error.InvalidRequestError:
                logger.warning(f"Stripe customer {user.stripe_customer_id} not found, creating new one")
                user.stripe_customer_id = None
        
        return self.create_customer(user)

    def create_subscription_payment_intent(self, user: User) -> Dict[str, Any]:
        """Create a payment intent for premium subscription upgrade."""
        try:
            customer_id = self.get_or_create_customer(user)
            
            # Get premium price from config
            premium_price = current_app.config.get('STRIPE_PREMIUM_PRICE', 299)  # $2.99 in cents
            
            payment_intent = stripe.PaymentIntent.create(
                amount=premium_price,
                currency='usd',
                customer=customer_id,
                metadata={
                    'user_id': str(user.id),
                    'payment_type': PaymentType.SUBSCRIPTION.value,
                    'tier': SubscriptionTier.PREMIUM.value
                },
                automatic_payment_methods={'enabled': True}
            )
            
            # Create payment record
            payment = Payment(
                user_id=user.id,
                stripe_payment_intent_id=payment_intent.id,
                payment_type=PaymentType.SUBSCRIPTION,
                status=PaymentStatus.PENDING,
                amount=Decimal(premium_price) / 100,
                currency='usd',
                description=f"Premium subscription upgrade for {user.username}"
            )
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"Created subscription payment intent {payment_intent.id} for user {user.id}")
            
            return {
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'amount': premium_price,
                'currency': 'usd'
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription payment intent for user {user.id}: {str(e)}")
            raise

    def create_cookbook_payment_intent(self, user: User, cookbook: Cookbook) -> Dict[str, Any]:
        """Create a payment intent for cookbook purchase."""
        try:
            if not cookbook.is_available_for_purchase():
                raise ValueError("Cookbook is not available for purchase")
            
            if user.has_purchased_cookbook(cookbook.id):
                raise ValueError("User has already purchased this cookbook")
            
            customer_id = self.get_or_create_customer(user)
            
            # Calculate price with premium discount if applicable
            final_price = cookbook.price
            discount_applied = False
            
            if user.is_premium():
                from flask import current_app
                discount_percent = current_app.config.get('PREMIUM_COOKBOOK_DISCOUNT_PERCENT', 20)
                discount_amount = cookbook.price * (discount_percent / 100)
                final_price = cookbook.price - discount_amount
                discount_applied = True
                logger.info(f"Applied {discount_percent}% premium discount to cookbook {cookbook.id} for user {user.id}: ${cookbook.price:.2f} -> ${final_price:.2f}")
            
            amount_cents = int(final_price * 100)  # Convert to cents
            
            metadata = {
                'user_id': str(user.id),
                'cookbook_id': str(cookbook.id),
                'payment_type': PaymentType.COOKBOOK.value,
                'original_price': str(cookbook.price),
                'final_price': str(final_price)
            }
            
            if discount_applied:
                discount_percent = current_app.config.get('PREMIUM_COOKBOOK_DISCOUNT_PERCENT', 20)
                metadata['discount_applied'] = 'true'
                metadata['discount_percent'] = str(discount_percent)
                metadata['is_premium_purchase'] = 'true'
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                customer=customer_id,
                metadata=metadata,
                automatic_payment_methods={'enabled': True}
            )
            
            # Create payment record
            description = f"Purchase of cookbook '{cookbook.title}' by {user.username}"
            if discount_applied:
                discount_percent = current_app.config.get('PREMIUM_COOKBOOK_DISCOUNT_PERCENT', 20)
                description += f" (Premium discount: {discount_percent}% off)"
            
            payment = Payment(
                user_id=user.id,
                cookbook_id=cookbook.id,
                stripe_payment_intent_id=payment_intent.id,
                payment_type=PaymentType.COOKBOOK,
                status=PaymentStatus.PENDING,
                amount=final_price,  # Use discounted price
                currency='usd',
                description=description
            )
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"Created cookbook payment intent {payment_intent.id} for user {user.id}, cookbook {cookbook.id}")
            
            response_data = {
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'amount': amount_cents,
                'currency': 'usd',
                'cookbook': cookbook.to_dict(),
                'original_price': cookbook.price,
                'final_price': final_price
            }
            
            if discount_applied:
                discount_percent = current_app.config.get('PREMIUM_COOKBOOK_DISCOUNT_PERCENT', 20)
                response_data.update({
                    'discount_applied': True,
                    'discount_percent': discount_percent,
                    'discount_amount': cookbook.price - final_price,
                    'is_premium_purchase': True
                })
            else:
                response_data['discount_applied'] = False
            
            return response_data
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create cookbook payment intent for user {user.id}, cookbook {cookbook.id}: {str(e)}")
            raise

    def create_print_order_payment_intent(self, user: User, print_order: "PrintOrder") -> Dict[str, Any]:
        """Create a payment intent for print order."""
        try:
            from app.models.print_order import PrintOrderStatus
            
            if print_order.status != PrintOrderStatus.DRAFT:
                raise ValueError("Print order must be in draft status to create payment")
            
            if print_order.user_id != user.id:
                raise ValueError("Print order does not belong to user")
            
            customer_id = self.get_or_create_customer(user)
            
            # Use the calculated total cost from the order
            amount_cents = int(print_order.total_cost * 100)  # Convert to cents
            
            metadata = {
                'user_id': str(user.id),
                'print_order_id': str(print_order.id),
                'payment_type': PaymentType.PRINT_ORDER.value,
                'order_number': print_order.order_number,
                'cookbook_id': str(print_order.cookbook_id),
                'quantity': str(print_order.quantity),
                'printing_cost': str(print_order.printing_cost),
                'shipping_cost': str(print_order.shipping_cost),
                'platform_fee': str(print_order.platform_fee),
                'total_cost': str(print_order.total_cost)
            }
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                customer=customer_id,
                metadata=metadata,
                automatic_payment_methods={'enabled': True}
            )
            
            # Create payment record
            description = f"Print order {print_order.order_number} - {print_order.cookbook.title} (Qty: {print_order.quantity})"
            
            payment = Payment(
                user_id=user.id,
                print_order_id=print_order.id,
                stripe_payment_intent_id=payment_intent.id,
                payment_type=PaymentType.PRINT_ORDER,
                status=PaymentStatus.PENDING,
                amount=print_order.total_cost,
                currency='usd',
                description=description
            )
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"Created print order payment intent {payment_intent.id} for user {user.id}, order {print_order.order_number}")
            
            return {
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'amount': amount_cents,
                'currency': 'usd',
                'print_order': print_order.to_dict(include_shipping=True),
                'cost_breakdown': {
                    'printing_cost': float(print_order.printing_cost),
                    'shipping_cost': float(print_order.shipping_cost),
                    'platform_fee': float(print_order.platform_fee),
                    'tax_amount': float(print_order.tax_amount),
                    'total_cost': float(print_order.total_cost)
                }
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create print order payment intent for user {user.id}, order {print_order.id}: {str(e)}")
            raise

    def handle_payment_succeeded(self, payment_intent: Dict[str, Any]) -> None:
        """Handle successful payment completion."""
        try:
            payment_intent_id = payment_intent['id']
            metadata = payment_intent.get('metadata', {})
            
            # Find the payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            
            if not payment:
                logger.error(f"Payment record not found for payment intent {payment_intent_id}")
                return
            
            # Update payment status
            payment.status = PaymentStatus.SUCCEEDED
            
            payment_type = metadata.get('payment_type')
            
            if payment_type == PaymentType.SUBSCRIPTION.value:
                self._handle_subscription_payment_success(payment, metadata)
            elif payment_type == PaymentType.COOKBOOK.value:
                self._handle_cookbook_payment_success(payment, metadata)
            elif payment_type == PaymentType.PRINT_ORDER.value:
                self._handle_print_order_payment_success(payment, metadata)
            
            db.session.commit()
            logger.info(f"Successfully processed payment {payment_intent_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle payment success for {payment_intent['id']}: {str(e)}")
            db.session.rollback()
            raise

    def _handle_subscription_payment_success(self, payment: Payment, metadata: Dict[str, Any]) -> None:
        """Handle successful subscription payment."""
        user = payment.user
        subscription = user.get_or_create_subscription()
        
        # Upgrade to premium
        subscription.tier = SubscriptionTier.PREMIUM
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.monthly_upload_count = 0  # Reset upload count
        payment.subscription_id = subscription.id
        
        logger.info(f"Upgraded user {user.id} to premium subscription")

    def _handle_cookbook_payment_success(self, payment: Payment, metadata: Dict[str, Any]) -> None:
        """Handle successful cookbook payment."""
        cookbook_id = payment.cookbook_id
        user = payment.user
        cookbook = payment.cookbook
        
        # Create cookbook purchase record
        purchase = CookbookPurchase(
            user_id=user.id,
            cookbook_id=cookbook_id,
            payment_id=payment.id,
            purchase_price=payment.amount,
            access_granted=True
        )
        db.session.add(purchase)
        
        # Increment cookbook purchase count
        cookbook.increment_purchase_count()
        
        # Automatically add all cookbook recipes to user's collection
        self._add_cookbook_recipes_to_collection(user.id, cookbook)
        
        logger.info(f"Created cookbook purchase for user {user.id}, cookbook {cookbook_id}")

    def _handle_print_order_payment_success(self, payment: Payment, metadata: Dict[str, Any]) -> None:
        """Handle successful print order payment."""
        from app.models.print_order import PrintOrderStatus
        from app.models.print_order import PrintOrderStatusUpdate
        
        print_order = payment.print_order
        user = payment.user
        
        if not print_order:
            logger.error(f"Print order not found for payment {payment.id}")
            return
        
        # Update order status to PAID - ready for processing/submission
        previous_status = print_order.status
        print_order.status = PrintOrderStatus.PAID
        print_order.paid_at = db.func.now()
        
        # Create status update
        status_update = PrintOrderStatusUpdate(
            print_order_id=print_order.id,
            previous_status=previous_status,
            new_status=PrintOrderStatus.PAID,
            message="Payment completed successfully. Order ready for processing."
        )
        db.session.add(status_update)
        
        # Link payment to print order
        print_order.payment_id = payment.id
        
        logger.info(f"Print order {print_order.order_number} payment completed for user {user.id}")

    def _add_cookbook_recipes_to_collection(self, user_id: int, cookbook: "Cookbook") -> None:
        """Add all recipes from a purchased cookbook to the user's collection."""
        try:
            from app.models.recipe import UserRecipeCollection
            
            recipes_added = 0
            for recipe in cookbook.recipes:
                # Check if recipe is already in user's collection
                existing = UserRecipeCollection.query.filter_by(
                    user_id=user_id,
                    recipe_id=recipe.id
                ).first()
                
                if not existing:
                    collection_item = UserRecipeCollection(
                        user_id=user_id,
                        recipe_id=recipe.id,
                        notes=f"Added automatically from purchased cookbook: {cookbook.title}"
                    )
                    db.session.add(collection_item)
                    recipes_added += 1
            
            logger.info(f"Added {recipes_added} recipes from cookbook {cookbook.id} to user {user_id}'s collection")
            
        except Exception as e:
            logger.error(f"Failed to add cookbook recipes to collection for user {user_id}, cookbook {cookbook.id}: {str(e)}")
            # Don't raise the exception - we don't want to fail the payment if collection addition fails

    def handle_payment_failed(self, payment_intent: Dict[str, Any]) -> None:
        """Handle failed payment."""
        try:
            payment_intent_id = payment_intent['id']
            failure_message = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
            
            # Find and update payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            
            if payment:
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = failure_message
                db.session.commit()
                
                logger.warning(f"Payment {payment_intent_id} failed: {failure_message}")
            else:
                logger.error(f"Payment record not found for failed payment {payment_intent_id}")
                
        except Exception as e:
            logger.error(f"Failed to handle payment failure for {payment_intent['id']}: {str(e)}")
            db.session.rollback()

    def handle_webhook(self, payload: bytes, signature: str) -> bool:
        """Handle Stripe webhook events."""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            event_type = event['type']
            
            if event_type == 'payment_intent.succeeded':
                self.handle_payment_succeeded(event['data']['object'])
            elif event_type == 'payment_intent.payment_failed':
                self.handle_payment_failed(event['data']['object'])
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
            
            return True
            
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            return False
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to process webhook: {str(e)}")
            return False

    def cancel_subscription(self, user: User) -> bool:
        """Cancel user's premium subscription."""
        try:
            subscription = user.subscription
            if not subscription or not subscription.is_premium():
                logger.warning(f"No active premium subscription found for user {user.id}")
                return False
            
            # Update subscription status
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = db.func.now()
            subscription.cancel_at_period_end = True
            
            db.session.commit()
            logger.info(f"Canceled subscription for user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel subscription for user {user.id}: {str(e)}")
            db.session.rollback()
            return False

    def get_user_payment_methods(self, user: User) -> List[Dict[str, Any]]:
        """Get user's saved payment methods."""
        try:
            if not user.stripe_customer_id:
                return []
            
            payment_methods = stripe.PaymentMethod.list(
                customer=user.stripe_customer_id,
                type='card'
            )
            
            return [
                {
                    'id': pm.id,
                    'card': {
                        'brand': pm.card.brand,
                        'last4': pm.card.last4,
                        'exp_month': pm.card.exp_month,
                        'exp_year': pm.card.exp_year
                    }
                }
                for pm in payment_methods.data
            ]
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get payment methods for user {user.id}: {str(e)}")
            return []

    def create_refund(
        self, 
        payment_intent_id: str, 
        amount: Optional[int] = None, 
        reason: str = "requested_by_customer",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a refund for a payment intent.
        
        Args:
            payment_intent_id: Stripe payment intent ID
            amount: Amount to refund in cents (None for full refund)
            reason: Reason for refund (requested_by_customer, duplicate, fraudulent)
            metadata: Additional metadata for the refund
            
        Returns:
            Dict with refund information
        """
        try:
            # Find the payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()
            
            if not payment:
                raise ValueError(f"Payment record not found for payment intent {payment_intent_id}")
            
            if payment.status != PaymentStatus.SUCCEEDED:
                raise ValueError(f"Cannot refund payment with status {payment.status.value}")
            
            # Create refund in Stripe
            refund_data = {
                'payment_intent': payment_intent_id,
                'reason': reason,
                'metadata': metadata or {}
            }
            
            if amount is not None:
                refund_data['amount'] = amount
            
            refund = stripe.Refund.create(**refund_data)
            
            # Update payment record
            if refund.amount == int(payment.amount * 100):  # Full refund
                payment.status = PaymentStatus.REFUNDED
            # For partial refunds, we might want a different status or tracking
            
            db.session.commit()
            
            logger.info(f"Created refund {refund.id} for payment intent {payment_intent_id}")
            
            return {
                'refund_id': refund.id,
                'amount': refund.amount,
                'currency': refund.currency,
                'status': refund.status,
                'payment_intent_id': payment_intent_id,
                'created': refund.created
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create refund for payment intent {payment_intent_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing refund for payment intent {payment_intent_id}: {str(e)}")
            db.session.rollback()
            raise

    def create_print_order_refund(
        self, 
        print_order: "PrintOrder", 
        refund_reason: str = "Order cancelled before processing",
        partial_amount: Optional[Decimal] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a refund for a print order.
        
        Args:
            print_order: The print order to refund
            refund_reason: Reason for the refund
            partial_amount: Amount to refund (None for full refund)
            
        Returns:
            Dict with refund information or None if no payment to refund
        """
        try:
            # Check if order has a payment
            if not print_order.payment or not print_order.payment.stripe_payment_intent_id:
                logger.warning(f"No payment found to refund for print order {print_order.order_number}")
                return None
            
            payment = print_order.payment
            
            # Calculate refund amount
            refund_amount_cents = None
            if partial_amount:
                refund_amount_cents = int(partial_amount * 100)
            
            # Create metadata for tracking
            metadata = {
                'print_order_id': str(print_order.id),
                'order_number': print_order.order_number,
                'refund_reason': refund_reason
            }
            
            # Create the refund
            refund_info = self.create_refund(
                payment_intent_id=payment.stripe_payment_intent_id,
                amount=refund_amount_cents,
                reason="requested_by_customer",
                metadata=metadata
            )
            
            # Update order with refund information
            print_order.refund_amount = partial_amount or print_order.total_cost
            print_order.refund_reason = refund_reason
            print_order.stripe_refund_id = refund_info['refund_id']
            print_order.refunded_at = datetime.utcnow()
            
            # Update order status
            if partial_amount is None or partial_amount >= print_order.total_cost:
                # Full refund - update order status
                print_order.status = PrintOrderStatus.REFUNDED
            
            db.session.commit()
            
            logger.info(f"Processed refund for print order {print_order.order_number}: {refund_info['refund_id']}")
            return refund_info
            
        except Exception as e:
            logger.error(f"Failed to create refund for print order {print_order.order_number}: {str(e)}")
            db.session.rollback()
            raise

    def get_refund_info(self, refund_id: str) -> Dict[str, Any]:
        """
        Get information about a refund.
        
        Args:
            refund_id: Stripe refund ID
            
        Returns:
            Dict with refund information
        """
        try:
            refund = stripe.Refund.retrieve(refund_id)
            
            return {
                'refund_id': refund.id,
                'amount': refund.amount,
                'currency': refund.currency,
                'status': refund.status,
                'payment_intent_id': refund.payment_intent,
                'reason': refund.reason,
                'created': refund.created,
                'metadata': refund.metadata
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get refund info for {refund_id}: {str(e)}")
            raise

    def calculate_refund_eligibility(self, print_order: "PrintOrder") -> Dict[str, Any]:
        """
        Calculate refund eligibility and amount for a print order.
        
        Args:
            print_order: The print order to check
            
        Returns:
            Dict with eligibility information
        """
        try:
            from app.models.print_order import PrintOrderStatus
            
            if not print_order.payment:
                return {
                    'eligible': False,
                    'reason': 'No payment found for this order',
                    'refund_amount': 0
                }
            
            if print_order.payment.status != PaymentStatus.SUCCEEDED:
                return {
                    'eligible': False,
                    'reason': 'Payment was not successful',
                    'refund_amount': 0
                }
            
            # Check order status for refund eligibility
            if print_order.status in [PrintOrderStatus.REFUNDED]:
                return {
                    'eligible': False,
                    'reason': 'Order has already been refunded',
                    'refund_amount': 0
                }
            
            # Calculate refund amount based on order status
            refund_amount = print_order.total_cost
            refund_percentage = 100
            
            if print_order.status == PrintOrderStatus.PRINTING:
                # Partial refund - printing has started
                refund_percentage = 50  # 50% refund
                refund_amount = print_order.total_cost * Decimal('0.5')
            elif print_order.status in [PrintOrderStatus.SHIPPED, PrintOrderStatus.DELIVERED]:
                # No refund after shipping
                return {
                    'eligible': False,
                    'reason': 'Order has already been shipped',
                    'refund_amount': 0
                }
            
            return {
                'eligible': True,
                'refund_amount': float(refund_amount),
                'refund_percentage': refund_percentage,
                'order_status': print_order.status.value,
                'reason': f'{refund_percentage}% refund available for {print_order.status.value} order'
            }
            
        except Exception as e:
            logger.error(f"Error calculating refund eligibility for order {print_order.order_number}: {str(e)}")
            return {
                'eligible': False,
                'reason': 'Error calculating refund eligibility',
                'refund_amount': 0
            }