import logging
import traceback
from flask import Blueprint, request, jsonify, current_app
from functools import wraps

from app import db
from app.models.user import User
from app.models.recipe import Cookbook
from app.models.payment import Payment, PaymentStatus, Subscription
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
    """Create payment intent for premium subscription upgrade."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if user is already premium
        if user.is_premium():
            return jsonify({'error': 'User already has premium subscription'}), 400

        stripe_service = StripeService()
        payment_intent_data = stripe_service.create_subscription_payment_intent(user)

        return jsonify({
            'success': True,
            'payment_intent': payment_intent_data
        }), 200

    except Exception as e:
        logger.error(f"Failed to create subscription upgrade for user {user_id}: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to create payment intent'}), 500


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
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to create payment intent'}), 500


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
        logger.error(f"Full traceback: {traceback.format_exc()}")
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

        return jsonify({
            'success': True,
            'subscription': subscription.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Failed to get subscription for user {user_id}: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
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
        logger.error(f"Full traceback: {traceback.format_exc()}")
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
        logger.error(f"Full traceback: {traceback.format_exc()}")
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
        logger.error(f"Full traceback: {traceback.format_exc()}")
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
        logger.error(f"Full traceback: {traceback.format_exc()}")
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
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to get payment status'}), 500