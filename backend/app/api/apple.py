"""API endpoints for Apple In-App Purchase integration."""

import logging
import traceback

from flask import Blueprint, request, jsonify

from app.api.payments import jwt_required, get_jwt_identity
from app.models.user import User

logger = logging.getLogger(__name__)

apple_bp = Blueprint("apple", __name__, url_prefix="/apple")


@apple_bp.route("/validate-receipt", methods=["POST"])
@jwt_required
def validate_receipt():
    """
    Validate Apple IAP receipt and update subscription.

    Expects JSON body:
    {
        "jwsTransaction": "<JWS signed transaction from StoreKit 2>"
    }

    Returns subscription info on success.
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    jws_transaction = data.get("jwsTransaction")
    if not jws_transaction:
        return jsonify({"error": "Missing jwsTransaction"}), 400

    try:
        from app.services.apple_iap_service import AppleIAPService

        service = AppleIAPService()
        transaction = service.validate_transaction(jws_transaction)

        # Update subscription with Apple IAP data
        subscription = service.update_subscription_from_transaction(
            user_id, transaction
        )

        logger.info(
            f"Successfully validated Apple receipt for user {user_id}, "
            f"product: {transaction['product_id']}"
        )

        return jsonify(
            {
                "success": True,
                "subscription": {
                    "tier": subscription.tier.value,
                    "is_premium": subscription.is_premium(),
                    "expires_date": transaction["expires_date"].isoformat()
                    if transaction["expires_date"]
                    else None,
                    "product_id": transaction["product_id"],
                },
            }
        )

    except ValueError as e:
        logger.error(f"Receipt validation failed for user {user_id}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.error(f"Receipt validation error for user {user_id}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Validation failed"}), 500


@apple_bp.route("/webhook", methods=["POST"])
def apple_webhook():
    """
    Handle App Store Server Notifications V2.

    Apple sends notifications for subscription lifecycle events:
    - SUBSCRIBED: New subscription
    - DID_RENEW: Subscription renewed
    - DID_FAIL_TO_RENEW: Billing problem
    - EXPIRED: Subscription expired
    - GRACE_PERIOD_EXPIRED: Grace period ended
    - REFUND: User was refunded
    - REVOKE: Family sharing revoked

    Expects JSON body:
    {
        "signedPayload": "<JWS signed notification>"
    }
    """
    try:
        data = request.get_json()
        signed_payload = data.get("signedPayload")

        if not signed_payload:
            logger.warning("Apple webhook received without signedPayload")
            return jsonify({"error": "Missing signedPayload"}), 400

        from app.services.apple_iap_service import AppleIAPService

        service = AppleIAPService()
        notification = service.process_webhook(signed_payload)

        logger.info(
            f"Apple webhook received: {notification['notification_type']}, "
            f"transaction: {notification['original_transaction_id']}"
        )

        # Handle the notification
        success = service.handle_webhook_notification(notification)

        if success:
            return jsonify({"success": True})
        else:
            # Return success to Apple even if we couldn't find the subscription
            # This prevents Apple from retrying endlessly
            logger.warning(
                f"Could not handle webhook for transaction "
                f"{notification['original_transaction_id']}"
            )
            return jsonify({"success": True, "handled": False})

    except ValueError as e:
        logger.error(f"Apple webhook validation error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.error(f"Apple webhook error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Webhook processing failed"}), 500


@apple_bp.route("/subscription-status", methods=["GET"])
@jwt_required
def get_subscription_status():
    """
    Get current Apple IAP subscription status for the authenticated user.

    Returns subscription info if user has an Apple-managed subscription.
    """
    user_id = get_jwt_identity()

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        subscription = user.subscription
        if not subscription:
            return jsonify(
                {
                    "has_subscription": False,
                    "payment_provider": None,
                }
            )

        # Check if this is an Apple-managed subscription
        if subscription.payment_provider != "apple":
            return jsonify(
                {
                    "has_subscription": True,
                    "payment_provider": subscription.payment_provider,
                    "is_apple_managed": False,
                }
            )

        return jsonify(
            {
                "has_subscription": True,
                "payment_provider": "apple",
                "is_apple_managed": True,
                "tier": subscription.tier.value,
                "status": subscription.status.value,
                "is_premium": subscription.is_premium(),
                "product_id": subscription.apple_product_id,
                "expires_date": subscription.apple_expires_date.isoformat()
                if subscription.apple_expires_date
                else None,
            }
        )

    except Exception as e:
        logger.error(f"Error getting subscription status for user {user_id}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Failed to get subscription status"}), 500


@apple_bp.route("/restore", methods=["POST"])
@jwt_required
def restore_purchases():
    """
    Restore purchases for a user.

    This endpoint is called when a user restores purchases on a new device
    or after reinstalling the app. It accepts multiple transactions.

    Expects JSON body:
    {
        "transactions": [
            {"jwsRepresentation": "<JWS signed transaction>"},
            ...
        ]
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    transactions = data.get("transactions", [])
    if not transactions:
        return jsonify({"error": "No transactions to restore"}), 400

    try:
        from app.services.apple_iap_service import AppleIAPService

        service = AppleIAPService()
        restored_count = 0
        latest_subscription = None

        for tx in transactions:
            jws = tx.get("jwsRepresentation")
            if not jws:
                continue

            try:
                transaction = service.validate_transaction(jws)
                subscription = service.update_subscription_from_transaction(
                    user_id, transaction
                )
                latest_subscription = subscription
                restored_count += 1
            except ValueError as e:
                logger.warning(f"Failed to restore transaction: {e}")
                continue

        logger.info(f"Restored {restored_count} purchases for user {user_id}")

        if latest_subscription and latest_subscription.is_premium():
            return jsonify(
                {
                    "success": True,
                    "restored_count": restored_count,
                    "subscription": {
                        "tier": latest_subscription.tier.value,
                        "is_premium": True,
                        "expires_date": latest_subscription.apple_expires_date.isoformat()
                        if latest_subscription.apple_expires_date
                        else None,
                    },
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "restored_count": restored_count,
                    "subscription": None,
                    "message": "No active subscriptions found to restore",
                }
            )

    except Exception as e:
        logger.error(f"Error restoring purchases for user {user_id}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Failed to restore purchases"}), 500
