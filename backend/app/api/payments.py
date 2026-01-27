import logging
from flask import Blueprint, request, jsonify, current_app
from functools import wraps

from app import db
from app.models.user import User
from app.models.recipe import Cookbook
from app.models.payment import Payment, PaymentStatus, PaymentType, Subscription
from app.services.stripe_service import StripeService
from app.api import bp
from app.api.auth import get_current_user


logger = logging.getLogger(__name__)


def jwt_required(f):
    """Decorator to require JWT authentication using the existing auth system."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        # Add user to request context
        request.current_user = user
        return f(*args, **kwargs)
    return wrapper


def get_jwt_identity():
    """Get current user ID from the authenticated user."""
    return request.current_user.id if hasattr(request, 'current_user') else None


@bp.route('/payments/subscription/upgrade', methods=['POST'])
@jwt_required
def create_subscription_upgrade():
    """Create Stripe subscription for premium upgrade."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if user is already premium
        if user.is_premium():
            return jsonify({'error': 'User already has premium subscription'}), 400

        stripe_service = StripeService()
        subscription_data = stripe_service.create_subscription(user)

        return jsonify({
            'success': True,
            'subscription': subscription_data,
            # Include client_secret at top level for frontend compatibility
            'client_secret': subscription_data.get('client_secret')
        }), 200

    except ValueError as e:
        logger.error(f"Configuration error for subscription upgrade: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Failed to create subscription upgrade for user {user_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to create subscription'}), 500


@bp.route('/payments/cookbook/<int:cookbook_id>/purchase', methods=['POST'])
@jwt_required
def create_cookbook_purchase():
    """Create payment intent for cookbook purchase."""
    try:
        user_id = get_jwt_identity()
        cookbook_id = request.view_args['cookbook_id']

        user = User.query.get(user_id)
        cookbook = Cookbook.query.get(cookbook_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not cookbook:
            return jsonify({'error': 'Cookbook not found'}), 404

        if not cookbook.is_available_for_purchase():
            return jsonify({'error': 'Cookbook is not available for purchase'}), 400

        if user.has_purchased_cookbook(cookbook_id):
            return jsonify({'error': 'User has already purchased this cookbook'}), 400

        stripe_service = StripeService()
        payment_intent_data = stripe_service.create_cookbook_payment_intent(user, cookbook)

        return jsonify({
            'success': True,
            'payment_intent': payment_intent_data
        }), 200

    except Exception as e:
        logger.error(f"Failed to create cookbook purchase for user {user_id}, cookbook {cookbook_id}: {str(e)}")
        return jsonify({'error': 'Failed to create payment intent'}), 500


@bp.route('/payments/subscription/confirm', methods=['POST'])
@jwt_required
def confirm_subscription():
    """Confirm subscription after successful payment - pays the invoice and activates subscription."""
    import stripe
    from datetime import datetime
    from app.models.payment import SubscriptionTier, SubscriptionStatus

    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        subscription = user.get_or_create_subscription()

        if not subscription.stripe_subscription_id:
            return jsonify({'error': 'No subscription found to confirm'}), 400

        # Get the subscription and its invoice
        stripe_sub = stripe.Subscription.retrieve(
            subscription.stripe_subscription_id,
            expand=['latest_invoice']
        )
        logger.info(f"Subscription {stripe_sub.id} status: {stripe_sub.status}")

        # If already active, just update local DB
        if stripe_sub.status in ['active', 'trialing']:
            subscription.tier = SubscriptionTier.PREMIUM
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.monthly_upload_count = 0

            # Safely get period dates
            period_start = getattr(stripe_sub, 'current_period_start', None)
            period_end = getattr(stripe_sub, 'current_period_end', None)
            if period_start:
                subscription.current_period_start = datetime.fromtimestamp(period_start)
            if period_end:
                subscription.current_period_end = datetime.fromtimestamp(period_end)

            db.session.commit()
            logger.info(f"User {user_id} subscription already active")

            return jsonify({
                'success': True,
                'message': 'Subscription confirmed',
                'subscription': subscription.to_dict()
            }), 200

        # Subscription is incomplete - need to pay the invoice
        latest_invoice = stripe_sub.latest_invoice
        if not latest_invoice:
            return jsonify({'error': 'No invoice found for subscription'}), 400

        invoice_id = latest_invoice.id
        invoice_status = latest_invoice.status
        logger.info(f"Invoice {invoice_id} status: {invoice_status}")

        # If invoice is already paid, activate subscription
        if invoice_status == 'paid':
            subscription.tier = SubscriptionTier.PREMIUM
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.monthly_upload_count = 0

            period_start = getattr(stripe_sub, 'current_period_start', None)
            period_end = getattr(stripe_sub, 'current_period_end', None)
            if period_start:
                subscription.current_period_start = datetime.fromtimestamp(period_start)
            if period_end:
                subscription.current_period_end = datetime.fromtimestamp(period_end)

            db.session.commit()
            logger.info(f"User {user_id} invoice already paid, subscription activated")

            return jsonify({
                'success': True,
                'message': 'Subscription confirmed',
                'subscription': subscription.to_dict()
            }), 200

        # Find the most recent successful payment for this user
        # (the one just completed by the frontend)
        recent_payments = Payment.query.filter_by(
            user_id=user_id,
            payment_type=PaymentType.SUBSCRIPTION
        ).order_by(Payment.created_at.desc()).limit(5).all()

        payment_method_id = None
        for payment in recent_payments:
            if payment.stripe_payment_intent_id:
                try:
                    pi = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
                    logger.info(f"Found PaymentIntent {pi.id} with status {pi.status}")
                    if pi.status == 'succeeded' and pi.payment_method:
                        payment_method_id = pi.payment_method
                        logger.info(f"Found successful payment method: {payment_method_id}")
                        break
                except stripe.error.StripeError as e:
                    logger.warning(f"Could not retrieve payment intent: {e}")
                    continue

        if payment_method_id:
            # Attach payment method to customer if needed
            try:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=subscription.stripe_customer_id or stripe_sub.customer,
                )
                logger.info(f"Attached payment method {payment_method_id} to customer")
            except stripe.error.StripeError as e:
                # May already be attached
                logger.info(f"Payment method attach result: {e}")

            # Set as default payment method for invoices
            stripe.Customer.modify(
                stripe_sub.customer,
                invoice_settings={'default_payment_method': payment_method_id}
            )
            logger.info(f"Set default payment method for customer")

            # Now pay the invoice
            try:
                paid_invoice = stripe.Invoice.pay(invoice_id)
                logger.info(f"Invoice {invoice_id} paid, status: {paid_invoice.status}")

                if paid_invoice.status == 'paid':
                    # Refresh subscription status
                    stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)

                    subscription.tier = SubscriptionTier.PREMIUM
                    subscription.status = SubscriptionStatus.ACTIVE
                    subscription.monthly_upload_count = 0

                    period_start = getattr(stripe_sub, 'current_period_start', None)
                    period_end = getattr(stripe_sub, 'current_period_end', None)
                    if period_start:
                        subscription.current_period_start = datetime.fromtimestamp(period_start)
                    if period_end:
                        subscription.current_period_end = datetime.fromtimestamp(period_end)

                    db.session.commit()
                    logger.info(f"User {user_id} subscription activated after invoice payment")

                    return jsonify({
                        'success': True,
                        'message': 'Subscription confirmed and activated',
                        'subscription': subscription.to_dict()
                    }), 200

            except stripe.error.StripeError as e:
                logger.error(f"Failed to pay invoice: {e}")
                return jsonify({
                    'success': False,
                    'message': f'Failed to pay invoice: {str(e)}',
                    'status': 'incomplete'
                }), 200

        # No payment method found
        return jsonify({
            'success': False,
            'message': 'No successful payment found to activate subscription',
            'status': stripe_sub.status
        }), 200

    except Exception as e:
        logger.error(f"Failed to confirm subscription for user {user_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to confirm subscription'}), 500


@bp.route('/payments/subscription/cancel', methods=['POST'])
@jwt_required
def cancel_subscription():
    """Cancel user's premium subscription."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.is_premium():
            return jsonify({'error': 'User does not have an active premium subscription'}), 400

        stripe_service = StripeService()
        success = stripe_service.cancel_subscription(user)

        if success:
            return jsonify({
                'success': True,
                'message': 'Subscription canceled successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to cancel subscription'}), 500

    except Exception as e:
        logger.error(f"Failed to cancel subscription for user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500


@bp.route('/payments/user/subscription', methods=['GET'])
@jwt_required
def get_user_subscription():
    """Get user's current subscription details."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        subscription = user.get_or_create_subscription()
        sub_dict = subscription.to_dict()

        # Override with User model methods that include admin check
        sub_dict['can_upload'] = user.can_upload_recipe()
        sub_dict['remaining_uploads'] = user.get_remaining_uploads()

        return jsonify({
            'success': True,
            'subscription': sub_dict
        }), 200

    except Exception as e:
        logger.error(f"Failed to get subscription for user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to get subscription details'}), 500


@bp.route('/payments/user/payments', methods=['GET'])
@jwt_required
def get_user_payments():
    """Get user's payment history."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        # Query payments with pagination
        payments_query = Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc())
        payments_paginated = payments_query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'success': True,
            'payments': [payment.to_dict() for payment in payments_paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': payments_paginated.total,
                'pages': payments_paginated.pages,
                'has_next': payments_paginated.has_next,
                'has_prev': payments_paginated.has_prev
            }
        }), 200

    except Exception as e:
        logger.error(f"Failed to get payments for user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to get payment history'}), 500


@bp.route('/payments/user/purchases', methods=['GET'])
@jwt_required
def get_user_purchases():
    """Get user's cookbook purchases."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get all active cookbook purchases
        purchases = [
            {
                **purchase.to_dict(),
                'cookbook': purchase.cookbook.to_dict(current_user_id=user_id)
            }
            for purchase in user.cookbook_purchases
            if purchase.has_access()
        ]

        return jsonify({
            'success': True,
            'purchases': purchases
        }), 200

    except Exception as e:
        logger.error(f"Failed to get purchases for user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to get purchase history'}), 500


@bp.route('/payments/user/payment-methods', methods=['GET'])
@jwt_required
def get_user_payment_methods():
    """Get user's saved payment methods."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        stripe_service = StripeService()
        payment_methods = stripe_service.get_user_payment_methods(user)

        return jsonify({
            'success': True,
            'payment_methods': payment_methods
        }), 200

    except Exception as e:
        logger.error(f"Failed to get payment methods for user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to get payment methods'}), 500


@bp.route('/payments/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    try:
        payload = request.get_data()
        signature = request.headers.get('Stripe-Signature')

        if not signature:
            logger.warning("Webhook received without signature")
            return jsonify({'error': 'Missing signature'}), 400

        stripe_service = StripeService()
        success = stripe_service.handle_webhook(payload, signature)

        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Webhook processing failed'}), 400

    except Exception as e:
        logger.error(f"Failed to process webhook: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500


@bp.route('/payments/payment/<payment_intent_id>/status', methods=['GET'])
@jwt_required
def get_payment_status():
    """Get payment status for a specific payment intent."""
    try:
        user_id = get_jwt_identity()
        payment_intent_id = request.view_args['payment_intent_id']

        # Find payment belonging to current user
        payment = Payment.query.filter_by(
            stripe_payment_intent_id=payment_intent_id,
            user_id=user_id
        ).first()

        if not payment:
            return jsonify({'error': 'Payment not found'}), 404

        return jsonify({
            'success': True,
            'payment': payment.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Failed to get payment status for {payment_intent_id}: {str(e)}")
        return jsonify({'error': 'Failed to get payment status'}), 500
