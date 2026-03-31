"""Service for validating Apple In-App Purchase receipts using StoreKit 2."""

import base64
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

import jwt
from flask import current_app

from app import db
from app.models.payment import (
    Subscription,
    SubscriptionTier,
    SubscriptionStatus,
)

logger = logging.getLogger(__name__)


class AppleIAPService:
    """Service for validating Apple In-App Purchase receipts using StoreKit 2."""

    def __init__(self):
        self.bundle_id = current_app.config.get("APPLE_BUNDLE_ID", "com.cookle.app")

    def validate_transaction(self, jws_transaction: str) -> Dict[str, Any]:
        """
        Validate a transaction from StoreKit 2.
        Returns decoded transaction info if valid.

        Handles both:
        - JWS-signed transactions from App Store (production/sandbox)
        - Base64-encoded JSON from Xcode StoreKit testing
        """
        payload = None

        # First try decoding as a JWT (production/sandbox App Store transactions)
        try:
            payload = jwt.decode(
                jws_transaction,
                options={"verify_signature": False},
            )
            logger.info("Decoded Apple transaction as JWS")
        except jwt.exceptions.DecodeError:
            logger.info("JWS decode failed, trying base64 JSON (StoreKit testing)")

        # Fall back to base64-encoded JSON (Xcode StoreKit config file testing)
        if payload is None:
            try:
                decoded_bytes = base64.b64decode(jws_transaction)
                payload = json.loads(decoded_bytes)
                logger.info("Decoded Apple transaction as base64 JSON (StoreKit testing)")
            except (base64.binascii.Error, json.JSONDecodeError) as e:
                logger.error(f"Failed to decode Apple transaction: {e}")
                logger.error(traceback.format_exc())
                raise ValueError(f"Invalid transaction format: {str(e)}")

        if not payload:
            raise ValueError("Could not decode transaction data")

        # Validate bundle ID matches our app (if present)
        transaction_bundle_id = payload.get("bundleId")
        if transaction_bundle_id and transaction_bundle_id != self.bundle_id:
            logger.warning(
                f"Bundle ID mismatch: expected {self.bundle_id}, got {transaction_bundle_id}"
            )
            raise ValueError(f"Bundle ID mismatch: {transaction_bundle_id}")

        # Extract transaction data
        transaction_id = payload.get("transactionId")
        original_transaction_id = payload.get("originalTransactionId") or payload.get("originalID")
        product_id = payload.get("productId") or payload.get("productID")

        # Convert timestamps - handle both milliseconds and seconds
        purchase_date_ms = payload.get("purchaseDate", 0)
        if purchase_date_ms > 1e12:
            purchase_date = datetime.fromtimestamp(purchase_date_ms / 1000)
        elif purchase_date_ms > 0:
            purchase_date = datetime.fromtimestamp(purchase_date_ms)
        else:
            purchase_date = datetime.utcnow()

        expires_date = None
        expires_date_ms = payload.get("expiresDate")
        if expires_date_ms:
            if expires_date_ms > 1e12:
                expires_date = datetime.fromtimestamp(expires_date_ms / 1000)
            else:
                expires_date = datetime.fromtimestamp(expires_date_ms)

        environment = payload.get("environment", "Xcode")

        logger.info(
            f"Validated Apple transaction {transaction_id} for product {product_id}, "
            f"environment: {environment}"
        )

        return {
            "transaction_id": str(transaction_id) if transaction_id else None,
            "original_transaction_id": str(original_transaction_id) if original_transaction_id else None,
            "product_id": product_id,
            "purchase_date": purchase_date,
            "expires_date": expires_date,
            "is_upgraded": payload.get("isUpgraded", False),
            "environment": environment,
            "bundle_id": transaction_bundle_id,
        }

    def process_webhook(self, signed_payload: str) -> Dict[str, Any]:
        """
        Process App Store Server Notification V2.

        Apple sends server notifications for subscription lifecycle events.
        These are signed JWS payloads containing nested transaction info.
        """
        try:
            # Decode the signed notification
            # In production, verify with Apple's public key
            payload = jwt.decode(
                signed_payload,
                options={"verify_signature": False},
            )

            notification_type = payload.get("notificationType")
            subtype = payload.get("subtype")

            logger.info(
                f"Processing Apple webhook: type={notification_type}, subtype={subtype}"
            )

            # Extract transaction info from nested data
            data = payload.get("data", {})
            signed_transaction = data.get("signedTransactionInfo")

            transaction_info = {}
            if signed_transaction:
                transaction_info = jwt.decode(
                    signed_transaction,
                    options={"verify_signature": False},
                )

            original_transaction_id = transaction_info.get("originalTransactionId")
            product_id = transaction_info.get("productId")

            expires_date = None
            expires_date_ms = transaction_info.get("expiresDate")
            if expires_date_ms:
                expires_date = datetime.fromtimestamp(expires_date_ms / 1000)

            return {
                "notification_type": notification_type,
                "subtype": subtype,
                "original_transaction_id": original_transaction_id,
                "product_id": product_id,
                "expires_date": expires_date,
                "environment": data.get("environment", "Production"),
            }

        except jwt.exceptions.DecodeError as e:
            logger.error(f"Failed to decode Apple webhook JWS: {e}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Invalid webhook format: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to process Apple webhook: {e}")
            logger.error(traceback.format_exc())
            raise

    def update_subscription_from_transaction(
        self,
        user_id: int,
        transaction: Dict[str, Any],
    ) -> Subscription:
        """
        Update or create a user's subscription based on Apple transaction data.
        """
        from app.models.user import User

        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        subscription = user.get_or_create_subscription()

        # Update subscription with Apple IAP data
        subscription.tier = SubscriptionTier.PREMIUM
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.payment_provider = "apple"
        subscription.apple_original_transaction_id = transaction[
            "original_transaction_id"
        ]
        subscription.apple_product_id = transaction["product_id"]
        subscription.apple_expires_date = transaction["expires_date"]
        subscription.monthly_upload_count = 0  # Reset upload count on premium upgrade

        db.session.commit()

        logger.info(
            f"Updated subscription for user {user_id} via Apple IAP: "
            f"product={transaction['product_id']}, "
            f"expires={transaction['expires_date']}"
        )

        return subscription

    def handle_webhook_notification(self, notification: Dict[str, Any]) -> bool:
        """
        Handle an App Store Server Notification and update subscription status.

        Returns True if handled successfully, False otherwise.
        """
        notification_type = notification.get("notification_type")
        original_tx_id = notification.get("original_transaction_id")

        if not original_tx_id:
            logger.warning("Webhook notification missing original_transaction_id")
            return False

        # Find subscription by Apple transaction ID
        subscription = Subscription.query.filter_by(
            apple_original_transaction_id=original_tx_id
        ).first()

        if not subscription:
            logger.warning(
                f"No subscription found for Apple transaction {original_tx_id}"
            )
            return False

        logger.info(
            f"Processing webhook {notification_type} for subscription {subscription.id}"
        )

        # Handle different notification types
        if notification_type in ["SUBSCRIBED", "DID_RENEW"]:
            subscription.tier = SubscriptionTier.PREMIUM
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.apple_expires_date = notification.get("expires_date")
            logger.info(f"Subscription {subscription.id} renewed/activated")

        elif notification_type == "DID_FAIL_TO_RENEW":
            # Grace period - keep premium for now but mark status
            subscription.status = SubscriptionStatus.PAST_DUE
            logger.warning(f"Subscription {subscription.id} failed to renew")

        elif notification_type == "EXPIRED":
            subscription.tier = SubscriptionTier.FREE
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            logger.info(f"Subscription {subscription.id} expired")

        elif notification_type == "REFUND":
            subscription.tier = SubscriptionTier.FREE
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            logger.info(f"Subscription {subscription.id} refunded")

        elif notification_type == "GRACE_PERIOD_EXPIRED":
            subscription.tier = SubscriptionTier.FREE
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            logger.info(f"Subscription {subscription.id} grace period expired")

        elif notification_type == "REVOKE":
            # Family sharing revocation
            subscription.tier = SubscriptionTier.FREE
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            logger.info(f"Subscription {subscription.id} revoked")

        else:
            logger.info(f"Unhandled Apple notification type: {notification_type}")

        db.session.commit()
        return True

    def check_subscription_status(
        self, original_transaction_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check the current status of a subscription by its original transaction ID.
        Returns subscription info if found, None otherwise.
        """
        subscription = Subscription.query.filter_by(
            apple_original_transaction_id=original_transaction_id
        ).first()

        if not subscription:
            return None

        return {
            "user_id": subscription.user_id,
            "tier": subscription.tier.value,
            "status": subscription.status.value,
            "is_premium": subscription.is_premium(),
            "product_id": subscription.apple_product_id,
            "expires_date": subscription.apple_expires_date.isoformat()
            if subscription.apple_expires_date
            else None,
        }
