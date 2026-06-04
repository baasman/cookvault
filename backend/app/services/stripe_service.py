import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List

import stripe
from flask import current_app

from app import db
from app.models.payment import (
    Subscription,
    SubscriptionTier,
    SubscriptionStatus,
    Payment,
    PaymentType,
    PaymentStatus,
    CookbookPurchase,
)
from app.models.user import User
from app.models.recipe import Cookbook


logger = logging.getLogger(__name__)


class StripeService:
    """Service for handling all Stripe payment operations."""

    def __init__(self):
        """Initialize Stripe with API key from config."""
        stripe_key = current_app.config.get("STRIPE_SECRET_KEY")
        logger.info(f"Initializing StripeService - API key present: {bool(stripe_key)}")
        if stripe_key:
            logger.info(f"Stripe API key starts with: {stripe_key[:7]}...")

        stripe.api_key = stripe_key
        self.webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")

        if not stripe.api_key:
            logger.error("Stripe API key not configured")
            raise ValueError("Stripe API key not configured")

    def create_customer(self, user: User) -> str:
        """Create a Stripe customer for a user."""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.username,
                metadata={"user_id": str(user.id), "username": user.username},
            )

            # Update user with Stripe customer ID
            user.stripe_customer_id = customer.id
            db.session.commit()

            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id

        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to create Stripe customer for user {user.id}: {str(e)}"
            )
            raise

    def get_or_create_customer(self, user: User) -> str:
        """Get existing Stripe customer ID or create a new customer."""
        if user.stripe_customer_id:
            try:
                # Verify customer still exists in Stripe
                stripe.Customer.retrieve(user.stripe_customer_id)
                return user.stripe_customer_id
            except stripe.error.InvalidRequestError:
                logger.warning(
                    f"Stripe customer {user.stripe_customer_id} not found, creating new one"
                )
                user.stripe_customer_id = None

        return self.create_customer(user)

    def create_subscription(self, user: User) -> Dict[str, Any]:
        """Create a Stripe subscription for premium upgrade."""
        try:
            customer_id = self.get_or_create_customer(user)
            price_id = current_app.config.get("STRIPE_PREMIUM_PRICE_ID")

            if not price_id:
                logger.error("STRIPE_PREMIUM_PRICE_ID not configured")
                raise ValueError("Stripe premium price ID not configured")

            # Create subscription - it will be incomplete until first payment
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
                expand=["latest_invoice"],
                metadata={"user_id": str(user.id)},
            )

            logger.info(
                f"Subscription created: {subscription.id}, status: {subscription.status}"
            )

            # Get the invoice
            latest_invoice = subscription.latest_invoice
            if not latest_invoice:
                raise ValueError("Subscription has no invoice")

            invoice_id = latest_invoice.id
            invoice_amount = latest_invoice.amount_due
            logger.info(f"Invoice ID: {invoice_id}, amount_due: {invoice_amount}")

            # Create a PaymentIntent for the invoice amount
            # This will be used to collect payment, and then we'll pay the invoice
            payment_intent = stripe.PaymentIntent.create(
                amount=invoice_amount,
                currency="usd",
                customer=customer_id,
                setup_future_usage="off_session",
                metadata={
                    "user_id": str(user.id),
                    "subscription_id": subscription.id,
                    "invoice_id": invoice_id,
                    "payment_type": PaymentType.SUBSCRIPTION.value,
                },
                automatic_payment_methods={"enabled": True},
            )

            client_secret = payment_intent.client_secret
            payment_intent_id = payment_intent.id
            logger.info(
                f"Created PaymentIntent {payment_intent_id} for invoice {invoice_id}"
            )

            if not client_secret:
                raise ValueError("Could not obtain client_secret for payment")

            premium_price = current_app.config.get("STRIPE_PREMIUM_PRICE", 299)

            # Create payment record
            payment = Payment(
                user_id=user.id,
                stripe_payment_intent_id=payment_intent_id,
                payment_type=PaymentType.SUBSCRIPTION,
                status=PaymentStatus.PENDING,
                amount=Decimal(premium_price) / 100,
                currency="usd",
                description=f"Premium subscription upgrade for {user.username}",
            )
            db.session.add(payment)

            # Update user's subscription record with Stripe subscription ID
            user_subscription = user.get_or_create_subscription()
            user_subscription.stripe_subscription_id = subscription.id

            db.session.commit()

            logger.info(f"Created subscription {subscription.id} for user {user.id}")

            return {
                "subscription_id": subscription.id,
                "client_secret": client_secret,
                "status": subscription.status,
                "amount": premium_price,
                "currency": "usd",
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription for user {user.id}: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def create_cookbook_payment_intent(
        self, user: User, cookbook: Cookbook
    ) -> Dict[str, Any]:
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

                discount_percent = current_app.config.get(
                    "PREMIUM_COOKBOOK_DISCOUNT_PERCENT", 20
                )
                discount_amount = cookbook.price * (discount_percent / 100)
                final_price = cookbook.price - discount_amount
                discount_applied = True
                logger.info(
                    f"Applied {discount_percent}% premium discount to cookbook {cookbook.id} for user {user.id}: ${cookbook.price:.2f} -> ${final_price:.2f}"
                )

            amount_cents = int(final_price * 100)  # Convert to cents

            metadata = {
                "user_id": str(user.id),
                "cookbook_id": str(cookbook.id),
                "payment_type": PaymentType.COOKBOOK.value,
                "original_price": str(cookbook.price),
                "final_price": str(final_price),
            }

            if discount_applied:
                discount_percent = current_app.config.get(
                    "PREMIUM_COOKBOOK_DISCOUNT_PERCENT", 20
                )
                metadata["discount_applied"] = "true"
                metadata["discount_percent"] = str(discount_percent)
                metadata["is_premium_purchase"] = "true"

            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                customer=customer_id,
                metadata=metadata,
                automatic_payment_methods={"enabled": True},
            )

            # Create payment record
            description = f"Purchase of cookbook '{cookbook.title}' by {user.username}"
            if discount_applied:
                discount_percent = current_app.config.get(
                    "PREMIUM_COOKBOOK_DISCOUNT_PERCENT", 20
                )
                description += f" (Premium discount: {discount_percent}% off)"

            payment = Payment(
                user_id=user.id,
                cookbook_id=cookbook.id,
                stripe_payment_intent_id=payment_intent.id,
                payment_type=PaymentType.COOKBOOK,
                status=PaymentStatus.PENDING,
                amount=final_price,  # Use discounted price
                currency="usd",
                description=description,
            )
            db.session.add(payment)
            db.session.commit()

            logger.info(
                f"Created cookbook payment intent {payment_intent.id} for user {user.id}, cookbook {cookbook.id}"
            )

            response_data = {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
                "amount": amount_cents,
                "currency": "usd",
                "cookbook": cookbook.to_dict(),
                "original_price": cookbook.price,
                "final_price": final_price,
            }

            if discount_applied:
                discount_percent = current_app.config.get(
                    "PREMIUM_COOKBOOK_DISCOUNT_PERCENT", 20
                )
                response_data.update(
                    {
                        "discount_applied": True,
                        "discount_percent": discount_percent,
                        "discount_amount": cookbook.price - final_price,
                        "is_premium_purchase": True,
                    }
                )
            else:
                response_data["discount_applied"] = False

            return response_data

        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to create cookbook payment intent for user {user.id}, cookbook {cookbook.id}: {str(e)}"
            )
            raise

    def create_print_order_payment_intent(
        self, user: User, print_order: "PrintOrder"
    ) -> Dict[str, Any]:
        """Create a payment intent for print order."""
        try:
            from app.models.print_order import PrintOrderStatus

            if print_order.status != PrintOrderStatus.DRAFT:
                raise ValueError(
                    "Print order must be in draft status to create payment"
                )

            if print_order.user_id != user.id:
                raise ValueError("Print order does not belong to user")

            customer_id = self.get_or_create_customer(user)

            # Use the calculated total cost from the order
            amount_cents = int(print_order.total_cost * 100)  # Convert to cents

            metadata = {
                "user_id": str(user.id),
                "print_order_id": str(print_order.id),
                "payment_type": PaymentType.PRINT_ORDER.value,
                "order_number": print_order.order_number,
                "cookbook_id": str(print_order.cookbook_id),
                "quantity": str(print_order.quantity),
                "printing_cost": str(print_order.printing_cost),
                "shipping_cost": str(print_order.shipping_cost),
                "platform_fee": str(print_order.platform_fee),
                "total_cost": str(print_order.total_cost),
            }

            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                customer=customer_id,
                metadata=metadata,
                automatic_payment_methods={"enabled": True},
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
                currency="usd",
                description=description,
            )
            db.session.add(payment)
            db.session.commit()

            logger.info(
                f"Created print order payment intent {payment_intent.id} for user {user.id}, order {print_order.order_number}"
            )

            return {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
                "amount": amount_cents,
                "currency": "usd",
                "print_order": print_order.to_dict(include_shipping=True),
                "cost_breakdown": {
                    "printing_cost": float(print_order.printing_cost),
                    "shipping_cost": float(print_order.shipping_cost),
                    "platform_fee": float(print_order.platform_fee),
                    "tax_amount": float(print_order.tax_amount),
                    "total_cost": float(print_order.total_cost),
                },
            }

        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to create print order payment intent for user {user.id}, order {print_order.id}: {str(e)}"
            )
            raise

    def handle_payment_succeeded(self, payment_intent: Dict[str, Any]) -> None:
        """Handle successful payment completion."""
        try:
            payment_intent_id = payment_intent["id"]
            metadata = payment_intent.get("metadata", {})

            # Find the payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id
            ).first()

            if not payment:
                logger.error(
                    f"Payment record not found for payment intent {payment_intent_id}"
                )
                return

            # Update payment status
            payment.status = PaymentStatus.SUCCEEDED

            payment_type = metadata.get("payment_type")

            if payment_type == PaymentType.SUBSCRIPTION.value:
                self._handle_subscription_payment_success(payment, metadata)
            elif payment_type == PaymentType.COOKBOOK.value:
                self._handle_cookbook_payment_success(payment, metadata)
            elif payment_type == PaymentType.PRINT_ORDER.value:
                self._handle_print_order_payment_success(payment, metadata)
            elif payment_type == PaymentType.BOOK_PROJECT_EXPORT.value:
                self._handle_book_project_export_payment_success(payment, metadata)

            db.session.commit()
            logger.info(f"Successfully processed payment {payment_intent_id}")

        except Exception as e:
            logger.error(
                f"Failed to handle payment success for {payment_intent['id']}: {str(e)}"
            )
            db.session.rollback()
            raise

    def _handle_subscription_payment_success(
        self, payment: Payment, metadata: Dict[str, Any]
    ) -> None:
        """Handle successful subscription payment."""
        user = payment.user
        subscription = user.get_or_create_subscription()

        # Upgrade to premium
        subscription.tier = SubscriptionTier.PREMIUM
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.monthly_upload_count = 0  # Reset upload count
        payment.subscription_id = subscription.id

        logger.info(f"Upgraded user {user.id} to premium subscription")

    def _handle_cookbook_payment_success(
        self, payment: Payment, metadata: Dict[str, Any]
    ) -> None:
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
            access_granted=True,
        )
        db.session.add(purchase)

        # Increment cookbook purchase count
        cookbook.increment_purchase_count()

        # Automatically add all cookbook recipes to user's collection
        self._add_cookbook_recipes_to_collection(user.id, cookbook)

        logger.info(
            f"Created cookbook purchase for user {user.id}, cookbook {cookbook_id}"
        )

    def _handle_print_order_payment_success(
        self, payment: Payment, metadata: Dict[str, Any]
    ) -> None:
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
            message="Payment completed successfully. Order ready for processing.",
        )
        db.session.add(status_update)

        # Link payment to print order
        print_order.payment_id = payment.id

        logger.info(
            f"Print order {print_order.order_number} payment completed for user {user.id}"
        )

    def create_book_project_export_payment_intent(
        self, user: User, project, export_id: int
    ) -> Dict[str, Any]:
        """Create a Stripe PaymentIntent for the paid clean PDF export of a
        BookProject. ``export_id`` references a pre-created BookProjectExport row
        that the webhook handler will populate with the rendered PDF path once
        payment succeeds.
        """
        try:
            customer_id = self.get_or_create_customer(user)

            price = current_app.config.get("BOOK_PROJECT_EXPORT_PRICE_USD", 19.0)
            try:
                price_decimal = Decimal(str(price))
            except Exception:
                price_decimal = Decimal("19.0")

            amount_cents = int(price_decimal * 100)

            metadata = {
                "user_id": str(user.id),
                "book_project_id": str(project.id),
                "book_project_export_id": str(export_id),
                "payment_type": PaymentType.BOOK_PROJECT_EXPORT.value,
            }

            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                customer=customer_id,
                metadata=metadata,
                automatic_payment_methods={"enabled": True},
            )

            description = (
                f"Clean PDF export of '{project.title}' (BookProject {project.id})"
            )

            payment = Payment(
                user_id=user.id,
                stripe_payment_intent_id=payment_intent.id,
                payment_type=PaymentType.BOOK_PROJECT_EXPORT,
                status=PaymentStatus.PENDING,
                amount=price_decimal,
                currency="usd",
                description=description,
            )
            db.session.add(payment)
            db.session.commit()

            logger.info(
                f"Created BookProject export payment intent {payment_intent.id} "
                f"for user {user.id}, project {project.id}, export {export_id}"
            )

            return {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
                "amount": amount_cents,
                "currency": "usd",
                "export_id": export_id,
                "project_id": project.id,
                "price": float(price_decimal),
            }

        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to create BookProject export payment intent for user {user.id}, "
                f"project {project.id}: {str(e)}"
            )
            raise

    def _handle_book_project_export_payment_success(
        self, payment: Payment, metadata: Dict[str, Any]
    ) -> None:
        """Handle successful BookProject export payment: render the clean PDF
        and link it to the BookProjectExport row that was created at checkout
        time.
        """
        from app.models import BookProject, BookProjectExport
        from app.services.book_project_pdf_service import render_book_project_pdf

        export_id_raw = metadata.get("book_project_export_id")
        if not export_id_raw:
            logger.error(
                f"BOOK_PROJECT_EXPORT payment {payment.id} is missing export_id metadata"
            )
            return

        try:
            export_id = int(export_id_raw)
        except (TypeError, ValueError):
            logger.error(
                f"BOOK_PROJECT_EXPORT payment {payment.id} has invalid export_id metadata: {export_id_raw}"
            )
            return

        export = db.session.get(BookProjectExport, export_id)
        if not export:
            logger.error(
                f"BookProjectExport {export_id} not found for payment {payment.id}"
            )
            return

        # Link payment to export so future lookups work both directions.
        export.payment_id = payment.id

        project = db.session.get(BookProject, export.project_id)
        if not project:
            logger.error(
                f"BookProject {export.project_id} not found for export {export_id}"
            )
            return

        # Render the clean (non-watermarked) PDF. If WeasyPrint fails (e.g.
        # missing system libs in the deployment) we still mark the payment as
        # succeeded — the user can re-download via a regeneration endpoint
        # rather than losing their purchase.
        try:
            pdf_bytes = render_book_project_pdf(project, watermarked=False)
            export.pdf_data = pdf_bytes
            export.is_watermarked = False
            logger.info(
                f"Rendered clean PDF for BookProjectExport {export_id}: "
                f"{len(pdf_bytes):,} bytes stored inline"
            )

            # Notify the owner — they're typically no longer on the page when
            # the webhook completes, so email is the primary signal. Failure
            # is non-fatal; the user can still download from the dashboard.
            owner = project.owner
            if owner and owner.email:
                from app.services.email_service import get_email_service

                get_email_service().send_book_project_export_ready(
                    email=owner.email,
                    username=owner.username or owner.email.split("@")[0],
                    project_title=project.title,
                    project_id=project.id,
                )
        except Exception as render_err:
            logger.error(
                f"Failed to render PDF for BookProjectExport {export_id}: {render_err}",
                exc_info=True,
            )
            # Leave storage fields null; the download endpoint will return 202
            # with a "pending" message and a retry-able regenerate route.

    def _add_cookbook_recipes_to_collection(
        self, user_id: int, cookbook: "Cookbook"
    ) -> None:
        """Add all recipes from a purchased cookbook to the user's collection."""
        try:
            from app.models.recipe import UserRecipeCollection

            recipes_added = 0
            for recipe in cookbook.recipes:
                # Check if recipe is already in user's collection
                existing = UserRecipeCollection.query.filter_by(
                    user_id=user_id, recipe_id=recipe.id
                ).first()

                if not existing:
                    collection_item = UserRecipeCollection(
                        user_id=user_id,
                        recipe_id=recipe.id,
                        notes=f"Added automatically from purchased cookbook: {cookbook.title}",
                    )
                    db.session.add(collection_item)
                    recipes_added += 1

            logger.info(
                f"Added {recipes_added} recipes from cookbook {cookbook.id} to user {user_id}'s collection"
            )

        except Exception as e:
            logger.error(
                f"Failed to add cookbook recipes to collection for user {user_id}, cookbook {cookbook.id}: {str(e)}"
            )
            # Don't raise the exception - we don't want to fail the payment if collection addition fails

    def handle_payment_failed(self, payment_intent: Dict[str, Any]) -> None:
        """Handle failed payment."""
        try:
            payment_intent_id = payment_intent["id"]
            failure_message = payment_intent.get("last_payment_error", {}).get(
                "message", "Unknown error"
            )

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
                logger.error(
                    f"Payment record not found for failed payment {payment_intent_id}"
                )

        except Exception as e:
            logger.error(
                f"Failed to handle payment failure for {payment_intent['id']}: {str(e)}"
            )
            db.session.rollback()

    def handle_webhook(self, payload: bytes, signature: str) -> bool:
        """Handle Stripe webhook events."""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )

            event_type = event["type"]
            event_data = event["data"]["object"]

            # Payment intent events (for one-time payments like cookbooks)
            if event_type == "payment_intent.succeeded":
                self.handle_payment_succeeded(event_data)
            elif event_type == "payment_intent.payment_failed":
                self.handle_payment_failed(event_data)
            # Subscription events
            elif event_type == "customer.subscription.created":
                self._handle_subscription_created(event_data)
            elif event_type == "customer.subscription.updated":
                self._handle_subscription_updated(event_data)
            elif event_type == "customer.subscription.deleted":
                self._handle_subscription_deleted(event_data)
            # Invoice events (for recurring subscription payments)
            elif event_type == "invoice.payment_succeeded":
                self._handle_invoice_paid(event_data)
            elif event_type == "invoice.payment_failed":
                self._handle_invoice_failed(event_data)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")

            return True

        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to process webhook: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def _handle_subscription_created(self, subscription_data: Dict[str, Any]) -> None:
        """Handle subscription created event."""
        try:
            subscription_id = subscription_data["id"]
            customer_id = subscription_data["customer"]
            user_id = subscription_data.get("metadata", {}).get("user_id")
            status = subscription_data["status"]

            logger.info(
                f"Subscription created: {subscription_id}, status: {status}, user_id: {user_id}"
            )

            if not user_id:
                # Try to find user by customer ID
                user = User.query.filter_by(stripe_customer_id=customer_id).first()
                if user:
                    user_id = user.id
                else:
                    logger.warning(
                        f"Could not find user for subscription {subscription_id}"
                    )
                    return

            user = User.query.get(int(user_id))
            if not user:
                logger.error(
                    f"User {user_id} not found for subscription {subscription_id}"
                )
                return

            # Update subscription record
            user_subscription = user.get_or_create_subscription()
            user_subscription.stripe_subscription_id = subscription_id

            # If subscription is active, upgrade to premium
            if status == "active":
                user_subscription.tier = SubscriptionTier.PREMIUM
                user_subscription.status = SubscriptionStatus.ACTIVE
                user_subscription.monthly_upload_count = 0
                logger.info(f"User {user_id} upgraded to premium (subscription active)")

            db.session.commit()

        except Exception as e:
            logger.error(
                f"Failed to handle subscription created for {subscription_data.get('id')}: {str(e)}"
            )
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()

    def _handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> None:
        """Handle subscription updated event."""
        try:
            subscription_id = subscription_data["id"]
            status = subscription_data["status"]
            cancel_at_period_end = subscription_data.get("cancel_at_period_end", False)
            current_period_end = subscription_data.get("current_period_end")

            logger.info(f"Subscription updated: {subscription_id}, status: {status}")

            # Find user subscription by Stripe subscription ID
            user_subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()

            if not user_subscription:
                logger.warning(f"Subscription record not found for {subscription_id}")
                return

            # Update subscription status based on Stripe status
            if status == "active":
                user_subscription.tier = SubscriptionTier.PREMIUM
                user_subscription.status = SubscriptionStatus.ACTIVE
            elif status == "past_due":
                user_subscription.status = SubscriptionStatus.PAST_DUE
            elif status == "canceled":
                user_subscription.status = SubscriptionStatus.CANCELED
                user_subscription.tier = SubscriptionTier.FREE
            elif status == "unpaid":
                user_subscription.status = SubscriptionStatus.PAST_DUE

            # Handle cancellation at period end
            user_subscription.cancel_at_period_end = cancel_at_period_end

            # Update period dates
            if current_period_end:
                user_subscription.current_period_end = datetime.fromtimestamp(
                    current_period_end
                )

            current_period_start = subscription_data.get("current_period_start")
            if current_period_start:
                user_subscription.current_period_start = datetime.fromtimestamp(
                    current_period_start
                )

            db.session.commit()
            logger.info(f"Updated subscription {subscription_id} to status {status}")

        except Exception as e:
            logger.error(
                f"Failed to handle subscription updated for {subscription_data.get('id')}: {str(e)}"
            )
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()

    def _handle_subscription_deleted(self, subscription_data: Dict[str, Any]) -> None:
        """Handle subscription deleted/canceled event."""
        try:
            subscription_id = subscription_data["id"]
            logger.info(f"Subscription deleted: {subscription_id}")

            # Find user subscription by Stripe subscription ID
            user_subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()

            if not user_subscription:
                logger.warning(f"Subscription record not found for {subscription_id}")
                return

            # Downgrade to free tier
            user_subscription.tier = SubscriptionTier.FREE
            user_subscription.status = SubscriptionStatus.CANCELED
            user_subscription.canceled_at = datetime.utcnow()

            db.session.commit()
            logger.info(f"Downgraded user {user_subscription.user_id} to free tier")

        except Exception as e:
            logger.error(
                f"Failed to handle subscription deleted for {subscription_data.get('id')}: {str(e)}"
            )
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()

    def _handle_invoice_paid(self, invoice_data: Dict[str, Any]) -> None:
        """Handle successful invoice payment (subscription renewal)."""
        try:
            invoice_id = invoice_data["id"]
            subscription_id = invoice_data.get("subscription")
            billing_reason = invoice_data.get("billing_reason")

            logger.info(
                f"Invoice paid: {invoice_id}, subscription: {subscription_id}, reason: {billing_reason}"
            )

            if not subscription_id:
                logger.info(f"Invoice {invoice_id} is not for a subscription, skipping")
                return

            # Find user subscription
            user_subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()

            if not user_subscription:
                logger.warning(f"Subscription record not found for {subscription_id}")
                return

            # Ensure subscription is active and premium
            user_subscription.tier = SubscriptionTier.PREMIUM
            user_subscription.status = SubscriptionStatus.ACTIVE

            # Update payment record if exists
            payment_intent_id = invoice_data.get("payment_intent")
            if payment_intent_id:
                payment = Payment.query.filter_by(
                    stripe_payment_intent_id=payment_intent_id
                ).first()
                if payment:
                    payment.status = PaymentStatus.SUCCEEDED
                    payment.subscription_id = user_subscription.id

            db.session.commit()
            logger.info(f"Processed invoice payment for subscription {subscription_id}")

        except Exception as e:
            logger.error(
                f"Failed to handle invoice paid for {invoice_data.get('id')}: {str(e)}"
            )
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()

    def _handle_invoice_failed(self, invoice_data: Dict[str, Any]) -> None:
        """Handle failed invoice payment."""
        try:
            invoice_id = invoice_data["id"]
            subscription_id = invoice_data.get("subscription")

            logger.warning(
                f"Invoice payment failed: {invoice_id}, subscription: {subscription_id}"
            )

            if not subscription_id:
                return

            # Find user subscription
            user_subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()

            if not user_subscription:
                logger.warning(f"Subscription record not found for {subscription_id}")
                return

            # Mark subscription as past due
            user_subscription.status = SubscriptionStatus.PAST_DUE

            # Update payment record if exists
            payment_intent_id = invoice_data.get("payment_intent")
            if payment_intent_id:
                payment = Payment.query.filter_by(
                    stripe_payment_intent_id=payment_intent_id
                ).first()
                if payment:
                    payment.status = PaymentStatus.FAILED
                    payment.failure_reason = "Invoice payment failed"

            db.session.commit()
            logger.warning(f"Marked subscription {subscription_id} as past due")

        except Exception as e:
            logger.error(
                f"Failed to handle invoice failed for {invoice_data.get('id')}: {str(e)}"
            )
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()

    def cancel_subscription(self, user: User) -> bool:
        """Cancel user's premium subscription."""
        try:
            subscription = user.subscription
            if not subscription or not subscription.is_premium():
                logger.warning(
                    f"No active premium subscription found for user {user.id}"
                )
                return False

            # Cancel Stripe subscription if exists
            if subscription.stripe_subscription_id:
                try:
                    # Cancel at period end so user keeps access until current period ends
                    stripe.Subscription.modify(
                        subscription.stripe_subscription_id, cancel_at_period_end=True
                    )
                    logger.info(
                        f"Set Stripe subscription {subscription.stripe_subscription_id} to cancel at period end"
                    )
                except stripe.error.InvalidRequestError as e:
                    # Subscription may already be canceled
                    logger.warning(
                        f"Could not modify Stripe subscription {subscription.stripe_subscription_id}: {str(e)}"
                    )

            # Update local subscription status
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            subscription.cancel_at_period_end = True

            db.session.commit()
            logger.info(f"Canceled subscription for user {user.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel subscription for user {user.id}: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return False

    def get_user_payment_methods(self, user: User) -> List[Dict[str, Any]]:
        """Get user's saved payment methods."""
        try:
            if not user.stripe_customer_id:
                return []

            payment_methods = stripe.PaymentMethod.list(
                customer=user.stripe_customer_id, type="card"
            )

            return [
                {
                    "id": pm.id,
                    "card": {
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year,
                    },
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
        metadata: Optional[Dict[str, str]] = None,
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
                raise ValueError(
                    f"Payment record not found for payment intent {payment_intent_id}"
                )

            if payment.status != PaymentStatus.SUCCEEDED:
                raise ValueError(
                    f"Cannot refund payment with status {payment.status.value}"
                )

            # Create refund in Stripe
            refund_data = {
                "payment_intent": payment_intent_id,
                "reason": reason,
                "metadata": metadata or {},
            }

            if amount is not None:
                refund_data["amount"] = amount

            refund = stripe.Refund.create(**refund_data)

            # Update payment record
            if refund.amount == int(payment.amount * 100):  # Full refund
                payment.status = PaymentStatus.REFUNDED
            # For partial refunds, we might want a different status or tracking

            db.session.commit()

            logger.info(
                f"Created refund {refund.id} for payment intent {payment_intent_id}"
            )

            return {
                "refund_id": refund.id,
                "amount": refund.amount,
                "currency": refund.currency,
                "status": refund.status,
                "payment_intent_id": payment_intent_id,
                "created": refund.created,
            }

        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to create refund for payment intent {payment_intent_id}: {str(e)}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Error processing refund for payment intent {payment_intent_id}: {str(e)}"
            )
            db.session.rollback()
            raise

    def create_print_order_refund(
        self,
        print_order: "PrintOrder",
        refund_reason: str = "Order cancelled before processing",
        partial_amount: Optional[Decimal] = None,
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
            if (
                not print_order.payment
                or not print_order.payment.stripe_payment_intent_id
            ):
                logger.warning(
                    f"No payment found to refund for print order {print_order.order_number}"
                )
                return None

            payment = print_order.payment

            # Calculate refund amount
            refund_amount_cents = None
            if partial_amount:
                refund_amount_cents = int(partial_amount * 100)

            # Create metadata for tracking
            metadata = {
                "print_order_id": str(print_order.id),
                "order_number": print_order.order_number,
                "refund_reason": refund_reason,
            }

            # Create the refund
            refund_info = self.create_refund(
                payment_intent_id=payment.stripe_payment_intent_id,
                amount=refund_amount_cents,
                reason="requested_by_customer",
                metadata=metadata,
            )

            # Update order with refund information
            print_order.refund_amount = partial_amount or print_order.total_cost
            print_order.refund_reason = refund_reason
            print_order.stripe_refund_id = refund_info["refund_id"]
            print_order.refunded_at = datetime.utcnow()

            # Update order status
            if partial_amount is None or partial_amount >= print_order.total_cost:
                # Full refund - update order status
                print_order.status = PrintOrderStatus.REFUNDED

            db.session.commit()

            logger.info(
                f"Processed refund for print order {print_order.order_number}: {refund_info['refund_id']}"
            )
            return refund_info

        except Exception as e:
            logger.error(
                f"Failed to create refund for print order {print_order.order_number}: {str(e)}"
            )
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
                "refund_id": refund.id,
                "amount": refund.amount,
                "currency": refund.currency,
                "status": refund.status,
                "payment_intent_id": refund.payment_intent,
                "reason": refund.reason,
                "created": refund.created,
                "metadata": refund.metadata,
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
                    "eligible": False,
                    "reason": "No payment found for this order",
                    "refund_amount": 0,
                }

            if print_order.payment.status != PaymentStatus.SUCCEEDED:
                return {
                    "eligible": False,
                    "reason": "Payment was not successful",
                    "refund_amount": 0,
                }

            # Check order status for refund eligibility
            if print_order.status in [PrintOrderStatus.REFUNDED]:
                return {
                    "eligible": False,
                    "reason": "Order has already been refunded",
                    "refund_amount": 0,
                }

            # Calculate refund amount based on order status
            refund_amount = print_order.total_cost
            refund_percentage = 100

            if print_order.status == PrintOrderStatus.PRINTING:
                # Partial refund - printing has started
                refund_percentage = 50  # 50% refund
                refund_amount = print_order.total_cost * Decimal("0.5")
            elif print_order.status in [
                PrintOrderStatus.SHIPPED,
                PrintOrderStatus.DELIVERED,
            ]:
                # No refund after shipping
                return {
                    "eligible": False,
                    "reason": "Order has already been shipped",
                    "refund_amount": 0,
                }

            return {
                "eligible": True,
                "refund_amount": float(refund_amount),
                "refund_percentage": refund_percentage,
                "order_status": print_order.status.value,
                "reason": f"{refund_percentage}% refund available for {print_order.status.value} order",
            }

        except Exception as e:
            logger.error(
                f"Error calculating refund eligibility for order {print_order.order_number}: {str(e)}"
            )
            return {
                "eligible": False,
                "reason": "Error calculating refund eligibility",
                "refund_amount": 0,
            }
