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


class TestStripeWebhookBookProjectExport:
    """End-to-end: HTTP POST to /api/payments/webhook for a BOOK_PROJECT_EXPORT
    payment_intent.succeeded event runs through the full stack — webhook route
    → StripeService.handle_webhook → handle_payment_succeeded → BOOK_PROJECT_
    EXPORT routing → _handle_book_project_export_payment_success — and lands
    the right state on the BookProjectExport row.

    Mocks stripe.Webhook.construct_event (so we don't need a real
    STRIPE_WEBHOOK_SECRET + signed payload in the test env) and the PDF render
    (so WeasyPrint isn't required). Everything else runs for real.
    """

    def test_webhook_missing_signature_header_returns_400(self, client):
        """Sanity-check: the route guards on the signature header before
        touching the Stripe SDK at all."""
        response = client.post("/api/payments/webhook", data=b"{}")
        assert response.status_code == 400

    @patch("app.services.book_project_pdf_service.render_book_project_pdf")
    @patch("stripe.Webhook.construct_event")
    def test_payment_intent_succeeded_updates_export(
        self, mock_construct_event, mock_render, client, app, test_user, tmp_path
    ):
        from app.models import (
            BookProject,
            BookProjectExport,
            ProjectType,
        )
        from app.models.payment import (
            Payment,
            PaymentStatus,
            PaymentType,
        )

        # Place a rendered PDF on disk so the render mock returns a real path
        # the handler can store on the export row.
        fake_pdf = tmp_path / "clean.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\nclean export\n")
        mock_render.return_value = str(fake_pdf)

        with app.app_context():
            project = BookProject(
                owner_user_id=test_user.id,
                title="Webhook Test Project",
                project_type=ProjectType.WEDDING,
            )
            db.session.add(project)
            db.session.flush()

            export = BookProjectExport(
                project_id=project.id,
                user_id=test_user.id,
                payment_id=None,
                pdf_file_path=None,
                is_watermarked=False,
            )
            db.session.add(export)
            db.session.flush()

            payment = Payment(
                user_id=test_user.id,
                stripe_payment_intent_id="pi_test_e2e_webhook",
                payment_type=PaymentType.BOOK_PROJECT_EXPORT,
                status=PaymentStatus.PENDING,
                amount=19,
                currency="usd",
            )
            db.session.add(payment)
            db.session.commit()

            export_id = export.id
            payment_id = payment.id

        # Mock what stripe.Webhook.construct_event returns after verifying
        # the signature. Shape matches what handle_webhook reads.
        mock_construct_event.return_value = {
            "id": "evt_test_e2e",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_e2e_webhook",
                    "metadata": {
                        "payment_type": PaymentType.BOOK_PROJECT_EXPORT.value,
                        "book_project_export_id": str(export_id),
                    },
                }
            },
        }

        response = client.post(
            "/api/payments/webhook",
            data=b"raw-payload-mocked-construct_event-ignores-it",
            headers={"Stripe-Signature": "fake-but-non-empty"},
        )

        assert response.status_code == 200, response.get_data(as_text=True)

        with app.app_context():
            refreshed_payment = db.session.get(Payment, payment_id)
            refreshed_export = db.session.get(BookProjectExport, export_id)

            assert refreshed_payment.status == PaymentStatus.SUCCEEDED
            assert refreshed_export.payment_id == payment_id
            assert refreshed_export.pdf_file_path == str(fake_pdf)
            assert refreshed_export.is_watermarked is False

        # Render was called with watermarked=False — clean PDF, not preview.
        assert mock_render.call_count == 1
        assert mock_render.call_args.kwargs.get("watermarked") is False
