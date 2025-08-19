import logging
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
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
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
            amount_cents = int(cookbook.price * 100)  # Convert to cents
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                customer=customer_id,
                metadata={
                    'user_id': str(user.id),
                    'cookbook_id': str(cookbook.id),
                    'payment_type': PaymentType.COOKBOOK.value
                },
                automatic_payment_methods={'enabled': True}
            )
            
            # Create payment record
            payment = Payment(
                user_id=user.id,
                cookbook_id=cookbook.id,
                stripe_payment_intent_id=payment_intent.id,
                payment_type=PaymentType.COOKBOOK,
                status=PaymentStatus.PENDING,
                amount=cookbook.price,
                currency='usd',
                description=f"Purchase of cookbook '{cookbook.title}' by {user.username}"
            )
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"Created cookbook payment intent {payment_intent.id} for user {user.id}, cookbook {cookbook.id}")
            
            return {
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'amount': amount_cents,
                'currency': 'usd',
                'cookbook': cookbook.to_dict()
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create cookbook payment intent for user {user.id}, cookbook {cookbook.id}: {str(e)}")
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