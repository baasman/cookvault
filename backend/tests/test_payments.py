"""
Tests for payment API endpoints.
Tests Stripe subscription upgrade flow with mocked Stripe API.
"""

from unittest.mock import patch, MagicMock


from app import db
from app.models.payment import SubscriptionTier, SubscriptionStatus
from app.models.user import User


class TestGetUserSubscription:
    """Test GET /api/payments/user/subscription endpoint."""

    def test_get_subscription_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/api/payments/user/subscription")
        assert response.status_code == 401

    def test_get_subscription_new_user(self, auth_client, app, test_user):
        """Should return free tier for user without subscription."""
        response = auth_client.get("/api/payments/user/subscription")
        assert response.status_code == 200
        data = response.get_json()
        sub = data["subscription"]
        assert sub["tier"].upper() == "FREE"
        assert sub["is_premium"] is False

    def test_get_subscription_premium_user(self, auth_client, app, test_user):
        """Should return premium tier for premium user."""
        with app.app_context():
            user = db.session.get(User, test_user.id)
            sub = user.get_or_create_subscription()
            sub.tier = SubscriptionTier.PREMIUM
            sub.status = SubscriptionStatus.ACTIVE
            sub.payment_provider = "stripe"
            db.session.commit()

        response = auth_client.get("/api/payments/user/subscription")
        assert response.status_code == 200
        data = response.get_json()
        sub = data["subscription"]
        assert sub["tier"].upper() == "PREMIUM"
        assert sub["is_premium"] is True


class TestCreateSubscriptionUpgrade:
    """Test POST /api/payments/subscription/upgrade endpoint."""

    def test_upgrade_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.post("/api/payments/subscription/upgrade")
        assert response.status_code == 401

    @patch("app.api.payments.StripeService")
    def test_upgrade_creates_payment_intent(
        self, mock_stripe_cls, auth_client, app, test_user
    ):
        """Should create a Stripe payment intent for upgrade."""
        mock_stripe = MagicMock()
        mock_stripe.create_subscription.return_value = {
            "client_secret": "pi_test_secret",
            "payment_intent_id": "pi_test_123",
        }
        mock_stripe_cls.return_value = mock_stripe

        response = auth_client.post("/api/payments/subscription/upgrade")
        assert response.status_code == 200
        data = response.get_json()
        assert "client_secret" in data

    def test_upgrade_already_premium(self, auth_client, app, test_user):
        """Should reject upgrade if already premium."""
        with app.app_context():
            user = db.session.get(User, test_user.id)
            sub = user.get_or_create_subscription()
            sub.tier = SubscriptionTier.PREMIUM
            sub.status = SubscriptionStatus.ACTIVE
            db.session.commit()

        response = auth_client.post("/api/payments/subscription/upgrade")
        assert response.status_code in [400, 409]


class TestCancelSubscription:
    """Test POST /api/payments/subscription/cancel endpoint."""

    def test_cancel_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.post("/api/payments/subscription/cancel")
        assert response.status_code == 401

    def test_cancel_no_subscription(self, auth_client):
        """Should handle cancel when no subscription exists."""
        response = auth_client.post("/api/payments/subscription/cancel")
        # Should not crash — either 400 or 404
        assert response.status_code in [400, 404, 200]
