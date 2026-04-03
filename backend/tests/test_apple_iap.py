"""
Tests for Apple In-App Purchase API endpoints and service.
Tests receipt validation and subscription update flow with mocked data.
"""

import base64
import json
from datetime import datetime, timedelta


from app import db
from app.models.payment import SubscriptionTier, SubscriptionStatus
from app.models.user import User


def make_test_transaction(
    product_id="com.cookle.app.premium.monthly", bundle_id="com.cookle.app"
):
    """Create a base64-encoded test transaction payload (simulates StoreKit testing)."""
    payload = {
        "transactionId": "12345",
        "originalTransactionId": "12345",
        "productId": product_id,
        "bundleId": bundle_id,
        "purchaseDate": int(datetime.utcnow().timestamp() * 1000),
        "expiresDate": int((datetime.utcnow() + timedelta(days=30)).timestamp() * 1000),
        "environment": "Xcode",
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


class TestValidateReceipt:
    """Test POST /api/apple/validate-receipt endpoint."""

    def test_validate_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.post(
            "/api/apple/validate-receipt",
            json={"jwsTransaction": "test"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_validate_missing_transaction(self, auth_client):
        """Should return 400 when jwsTransaction is missing."""
        response = auth_client.post(
            "/api/apple/validate-receipt",
            json={},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_validate_invalid_transaction(self, auth_client):
        """Should return 400 for completely invalid transaction data."""
        response = auth_client.post(
            "/api/apple/validate-receipt",
            json={"jwsTransaction": "not-valid-base64-or-jwt!!!"},
        )
        assert response.status_code in [400, 500]

    def test_validate_valid_test_transaction(self, auth_client, app, test_user):
        """Should successfully validate a StoreKit test transaction and upgrade user."""
        jws = make_test_transaction()

        response = auth_client.post(
            "/api/apple/validate-receipt",
            json={"jwsTransaction": jws},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["subscription"]["is_premium"] is True
        assert data["subscription"]["tier"].upper() == "PREMIUM"

        # Verify database was updated
        with app.app_context():
            user = db.session.get(User, test_user.id)
            sub = user.subscription
            assert sub is not None
            assert sub.tier == SubscriptionTier.PREMIUM
            assert sub.status == SubscriptionStatus.ACTIVE
            assert sub.payment_provider == "apple"
            assert sub.apple_product_id == "com.cookle.app.premium.monthly"

    def test_validate_wrong_bundle_id(self, auth_client):
        """Should reject transaction with wrong bundle ID."""
        jws = make_test_transaction(bundle_id="com.wrong.app")

        response = auth_client.post(
            "/api/apple/validate-receipt",
            json={"jwsTransaction": jws},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "Bundle ID mismatch" in data.get("error", "")


class TestAppleWebhook:
    """Test POST /api/apple/webhook endpoint."""

    def test_webhook_missing_payload(self, client):
        """Should return 400 when signedPayload is missing."""
        response = client.post(
            "/api/apple/webhook",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_webhook_invalid_payload(self, client):
        """Should return 400 for invalid signed payload."""
        response = client.post(
            "/api/apple/webhook",
            json={"signedPayload": "invalid"},
            content_type="application/json",
        )
        assert response.status_code == 400


class TestSubscriptionStatus:
    """Test GET /api/apple/subscription-status endpoint."""

    def test_status_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/api/apple/subscription-status")
        assert response.status_code == 401

    def test_status_no_subscription(self, auth_client):
        """Should return no subscription for new user."""
        response = auth_client.get("/api/apple/subscription-status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["has_subscription"] is False

    def test_status_with_apple_subscription(self, auth_client, app, test_user):
        """Should return Apple subscription details."""
        with app.app_context():
            user = db.session.get(User, test_user.id)
            sub = user.get_or_create_subscription()
            sub.tier = SubscriptionTier.PREMIUM
            sub.status = SubscriptionStatus.ACTIVE
            sub.payment_provider = "apple"
            sub.apple_product_id = "com.cookle.app.premium.monthly"
            sub.apple_original_transaction_id = "12345"
            db.session.commit()

        response = auth_client.get("/api/apple/subscription-status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["has_subscription"] is True
        assert data["payment_provider"] == "apple"
        assert data["is_apple_managed"] is True
        assert data["is_premium"] is True


class TestRestorePurchases:
    """Test POST /api/apple/restore endpoint."""

    def test_restore_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.post(
            "/api/apple/restore",
            json={"transactions": []},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_restore_empty_transactions(self, auth_client):
        """Should return 400 when no transactions provided."""
        response = auth_client.post(
            "/api/apple/restore",
            json={"transactions": []},
        )
        assert response.status_code == 400

    def test_restore_valid_transaction(self, auth_client, app, test_user):
        """Should restore a valid test transaction."""
        jws = make_test_transaction()

        response = auth_client.post(
            "/api/apple/restore",
            json={"transactions": [{"jwsRepresentation": jws}]},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["restored_count"] == 1
