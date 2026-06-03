"""Tests for the BookProject branch of the print order endpoints (Phase 2C).

Only covers the new book_project_id path — the existing cookbook path is
exercised separately and a passing full-suite run confirms it didn't
regress. Heavy LuluService / WeasyPrint calls are mocked so these stay as
unit-level tests.
"""

from unittest.mock import patch, MagicMock

from app import db
from app.models import BookProject, ProjectType
from app.models.print_order import (
    PrintOrder,
    PrintOrderStatus,
    PrintSpecification,
    TrimSize,
    BindingType,
    PaperType,
    CoverFinish,
)


def _make_book_project_print_order(
    test_user, project, status=PrintOrderStatus.PROCESSING
):
    """Helper that creates a persisted PrintOrder linked to a BookProject."""
    spec = PrintSpecification(
        trim_size=TrimSize.A5,
        binding_type=BindingType.PERFECT_BOUND,
        paper_type=PaperType.STANDARD_WHITE,
        cover_finish=CoverFinish.MATTE,
        page_count=60,
    )
    db.session.add(spec)
    db.session.flush()

    order = PrintOrder(
        user_id=test_user.id,
        book_project_id=project.id,
        specification_id=spec.id,
        order_number="BPJ-WEBHOOK-001",
        quantity=1,
        status=status,
        lulu_print_job_id="lulu_job_test_webhook",
        shipping_name="Sarah",
        shipping_address_line1="1 Main St",
        shipping_city="Boston",
        shipping_state_code="MA",
        shipping_postal_code="02118",
        shipping_country_code="US",
        shipping_email="s@example.com",
        printing_cost=12,
        shipping_cost=4,
        tax_amount=1,
        platform_fee=1,
        total_cost=18,
    )
    db.session.add(order)
    db.session.commit()
    return order


def _make_project(test_user, **kwargs):
    defaults = {
        "owner_user_id": test_user.id,
        "title": "Sarah & Maya's Wedding Book",
        "project_type": ProjectType.WEDDING,
        "honorees": ["Sarah", "Maya"],
    }
    defaults.update(kwargs)
    project = BookProject(**defaults)
    db.session.add(project)
    db.session.commit()
    return project


class TestWebhooksWithBookProjectOrder:
    """Lulu status + validation webhooks should work identically for
    BookProject-linked PrintOrders (no cookbook-specific logic in the
    handlers). Lightweight regression test.

    Signature verification is bypassed at the route level — the verification
    logic itself is tested elsewhere, and our concern here is the
    entity-agnostic state machine that runs after verification passes."""

    @patch("app.api.print_webhooks.verify_webhook_signature", return_value=True)
    def test_status_webhook_marks_book_project_order_shipped(
        self, _mock_verify, client, test_user
    ):
        project = _make_project(test_user)
        order = _make_book_project_print_order(test_user, project)
        order_id = order.id

        response = client.post(
            "/api/print-webhooks/lulu-status",
            json={
                "event_type": "print_job.shipped",
                "print_job": {
                    "id": "lulu_job_test_webhook",
                    "shipping": {
                        "carrier": "UPS",
                        "tracking_number": "1Z999AA1",
                        "tracking_url": "https://example.com/track",
                    },
                },
            },
        )
        assert response.status_code == 200, response.get_data(as_text=True)

        refreshed = db.session.get(PrintOrder, order_id)
        assert refreshed.status == PrintOrderStatus.SHIPPED
        assert refreshed.tracking_number == "1Z999AA1"
        # Book project linkage preserved.
        assert refreshed.book_project_id == project.id
        assert refreshed.cookbook_id is None

    @patch("app.api.print_webhooks.verify_webhook_signature", return_value=True)
    def test_validation_webhook_marks_book_project_order_failed(
        self, _mock_verify, client, test_user
    ):
        project = _make_project(test_user)
        order = _make_book_project_print_order(
            test_user, project, status=PrintOrderStatus.PROCESSING
        )
        order_id = order.id

        response = client.post(
            "/api/print-webhooks/lulu-validation",
            json={
                "print_job_id": "lulu_job_test_webhook",
                "interior": {
                    "status": "rejected",
                    "errors": ["Bleed area exceeded"],
                },
                "cover": {"status": "approved"},
            },
        )
        assert response.status_code == 200, response.get_data(as_text=True)

        refreshed = db.session.get(PrintOrder, order_id)
        assert refreshed.status == PrintOrderStatus.FAILED
        assert refreshed.interior_validation_status == "rejected"


class TestSpecifications:
    def test_specifications_accepts_book_project_id(self, auth_client, test_user):
        project = _make_project(test_user)
        response = auth_client.get(
            f"/api/print-orders/specifications?book_project_id={project.id}"
        )
        assert response.status_code == 200
        body = response.get_json()
        # No recipes included → 0; estimated_page_count still computed.
        assert body["recipe_count"] == 0
        assert "estimated_page_count" in body

    def test_specifications_rejects_both_ids(
        self, auth_client, test_user, sample_cookbook
    ):
        project = _make_project(test_user)
        response = auth_client.get(
            "/api/print-orders/specifications"
            f"?cookbook_id={sample_cookbook.id}&book_project_id={project.id}"
        )
        assert response.status_code == 400

    def test_specifications_rejects_unauthorized_project(
        self, auth_client, second_user
    ):
        # Project belongs to the OTHER user.
        project = _make_project(second_user)
        response = auth_client.get(
            f"/api/print-orders/specifications?book_project_id={project.id}"
        )
        assert response.status_code == 403


class TestQuoteAndCreate:
    def _mock_lulu_quote(self):
        return {
            "printing_cost": "12.00",
            "shipping_cost": "4.50",
            "tax_amount": "1.30",
            "platform_fee": "1.00",
            "total_cost": "18.80",
            "estimated_delivery_days": 7,
            "valid_until": "2030-01-01T00:00:00Z",
            "quote_id": "q_test",
        }

    @patch("app.api.print_orders.LuluService")
    def test_quote_book_project(self, mock_lulu_cls, auth_client, test_user):
        mock_lulu = MagicMock()
        mock_lulu.get_print_quote.return_value = self._mock_lulu_quote()
        mock_lulu_cls.return_value = mock_lulu

        project = _make_project(test_user)
        response = auth_client.post(
            "/api/print-orders/quote",
            json={
                "book_project_id": project.id,
                "quantity": 1,
                "specification": {
                    "trim_size": "A5",
                    "binding_type": "perfect_bound",
                    "paper_type": "standard_white",
                    "cover_finish": "matte",
                    "page_count": 60,
                },
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["entity_type"] == "book_project"
        assert data["book_project_id"] == project.id
        assert data["book_project_title"] == project.title

    @patch("app.api.print_orders.LuluService")
    def test_create_order_sets_book_project_id(
        self, mock_lulu_cls, auth_client, test_user
    ):
        mock_lulu = MagicMock()
        mock_lulu.get_print_quote.return_value = self._mock_lulu_quote()
        mock_lulu_cls.return_value = mock_lulu

        project = _make_project(test_user)
        response = auth_client.post(
            "/api/print-orders/",
            json={
                "book_project_id": project.id,
                "quantity": 1,
                "specification": {
                    "trim_size": "A5",
                    "binding_type": "perfect_bound",
                    "paper_type": "standard_white",
                    "cover_finish": "matte",
                    "page_count": 60,
                },
                "shipping_address": {
                    "name": "Boudewijn Aasman",
                    "address_line1": "123 Test St",
                    "city": "Boston",
                    "state_code": "MA",
                    "postal_code": "02118",
                    "country_code": "US",
                    "email": "test@example.com",
                },
            },
        )
        assert response.status_code == 201
        body = response.get_json()
        assert body["order"]["book_project_id"] == project.id
        assert body["order"]["cookbook_id"] is None
        assert body["order"]["content_type"] == "book_project"
        # Order number prefix encodes entity type.
        assert body["order"]["order_number"].startswith("BPJ-")

        # Persisted with the right FKs.
        order = db.session.get(PrintOrder, body["order"]["id"])
        assert order.book_project_id == project.id
        assert order.cookbook_id is None
        assert order.content_type == "book_project"

    def test_create_rejects_neither_id(self, auth_client, test_user):
        response = auth_client.post(
            "/api/print-orders/",
            json={
                "quantity": 1,
                "specification": {
                    "trim_size": "A5",
                    "binding_type": "perfect_bound",
                    "paper_type": "standard_white",
                    "cover_finish": "matte",
                    "page_count": 60,
                },
                "shipping_address": {
                    "name": "X",
                    "address_line1": "1",
                    "city": "Boston",
                    "state_code": "MA",
                    "postal_code": "02118",
                    "country_code": "US",
                    "email": "t@example.com",
                },
            },
        )
        assert response.status_code == 400


class TestSubmitBookProjectOrder:
    @patch("app.api.print_orders.render_book_project_pdf_to_bytes")
    @patch("app.api.print_orders.CoverGenerationService")
    @patch("app.api.print_orders.LuluService")
    def test_submit_renders_via_weasyprint_and_uploads(
        self,
        mock_lulu_cls,
        mock_cover_cls,
        mock_render,
        auth_client,
        test_user,
    ):
        """The submit endpoint should route a BookProject order through the
        WeasyPrint print renderer (not ReportLab), upload both PDFs, and
        create the Lulu print job."""
        # Interior PDF mock — return raw bytes that look like a PDF.
        mock_render.return_value = b"%PDF-1.4\nbook project interior\n"

        # Cover service mock.
        mock_cover = MagicMock()
        mock_cover.estimate_page_count.return_value = 60
        mock_cover.generate_cover_pdf.return_value = b"%PDF-1.4\ncover\n"
        mock_cover_cls.return_value = mock_cover

        # Lulu mock.
        mock_lulu = MagicMock()
        mock_lulu.upload_interior_pdf.return_value = "https://lulu.test/interior"
        mock_lulu.upload_cover_pdf.return_value = "https://lulu.test/cover"
        mock_lulu.create_print_job.return_value = {
            "print_job_id": "pj_test_123",
            "line_item_id": "li_test_456",
            "status": "CREATED",
        }
        mock_lulu_cls.return_value = mock_lulu

        # Set up a paid BookProject print order ready for submit.
        from app.models.print_order import (
            PrintSpecification,
            TrimSize,
            BindingType,
            PaperType,
            CoverFinish,
        )

        project = _make_project(test_user)
        spec = PrintSpecification(
            trim_size=TrimSize.A5,
            binding_type=BindingType.PERFECT_BOUND,
            paper_type=PaperType.STANDARD_WHITE,
            cover_finish=CoverFinish.MATTE,
            page_count=60,
        )
        db.session.add(spec)
        db.session.flush()

        order = PrintOrder(
            user_id=test_user.id,
            book_project_id=project.id,
            specification_id=spec.id,
            order_number="BPJ-TEST-001",
            quantity=1,
            status=PrintOrderStatus.PAID,
            shipping_name="Sarah",
            shipping_address_line1="1 Main St",
            shipping_city="Boston",
            shipping_state_code="MA",
            shipping_postal_code="02118",
            shipping_country_code="US",
            shipping_email="s@example.com",
            printing_cost=12,
            shipping_cost=4,
            tax_amount=1,
            platform_fee=1,
            total_cost=18,
        )
        db.session.add(order)
        db.session.commit()

        response = auth_client.post(f"/api/print-orders/{order.id}/submit")
        assert response.status_code == 200, response.get_data(as_text=True)

        # WeasyPrint was called with the right kwargs.
        assert mock_render.call_count == 1
        kwargs = mock_render.call_args.kwargs
        assert kwargs.get("watermarked") is False
        assert kwargs.get("print_ready") is True
        assert kwargs.get("trim_size") == TrimSize.A5

        # Lulu uploads + job creation happened.
        mock_lulu.upload_interior_pdf.assert_called_once()
        mock_lulu.upload_cover_pdf.assert_called_once()
        mock_lulu.create_print_job.assert_called_once()

        # Order moved to PROCESSING with Lulu IDs filled in.
        refreshed = db.session.get(PrintOrder, order.id)
        assert refreshed.status == PrintOrderStatus.PROCESSING
        assert refreshed.lulu_print_job_id == "pj_test_123"
        assert refreshed.interior_file_url == "https://lulu.test/interior"
        assert refreshed.cover_file_url == "https://lulu.test/cover"
