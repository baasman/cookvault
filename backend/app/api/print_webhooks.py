"""
Webhook endpoints for print-on-demand order status updates.

This module handles webhook events from Lulu API for tracking
order status changes, validation results, and shipping updates.
"""

import logging
import hmac
import hashlib
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import db
from app.models.print_order import PrintOrder, PrintOrderStatus, PrintOrderStatusUpdate

bp = Blueprint("print_webhooks", __name__, url_prefix="/print-webhooks")
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


def verify_webhook_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """Verify that the webhook signature matches the expected signature."""
    if not secret:
        logger.warning("No webhook secret configured - skipping signature verification")
        return True

    if not signature:
        logger.error("No signature provided in webhook request")
        return False

    try:
        # Remove 'sha256=' prefix if present
        if signature.startswith("sha256="):
            signature = signature[7:]

        # Calculate expected signature
        expected_signature = hmac.new(
            secret.encode("utf-8"), payload_body, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False


@bp.route("/lulu-status", methods=["POST"])
@limiter.limit("100/hour")
def handle_lulu_status_webhook():
    """Handle status update webhooks from Lulu."""
    try:
        # Get the raw payload for signature verification
        payload = request.get_data()
        signature = request.headers.get("X-Hub-Signature-256") or request.headers.get(
            "X-Lulu-Signature"
        )
        webhook_secret = current_app.config.get("LULU_WEBHOOK_SECRET")

        # Verify webhook signature if configured
        if not verify_webhook_signature(payload, signature, webhook_secret):
            logger.warning(f"Invalid webhook signature from IP {request.remote_addr}")
            return jsonify({"error": "Invalid signature"}), 401

        # Parse webhook data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "Empty request body"}), 400

        logger.info(f"Received Lulu webhook: {data}")

        # Extract event information
        event_type = data.get("event_type") or data.get("type")
        if not event_type:
            return jsonify({"error": "Missing event_type"}), 400

        # Get print job information
        print_job_data = data.get("print_job") or data.get("data", {})
        print_job_id = print_job_data.get("id")

        if not print_job_id:
            logger.warning(f"Webhook missing print_job.id: {data}")
            return jsonify({"error": "Missing print_job.id"}), 400

        # Find the corresponding print order
        print_order = PrintOrder.query.filter_by(
            lulu_print_job_id=str(print_job_id)
        ).first()
        if not print_order:
            logger.warning(f"No print order found for Lulu job {print_job_id}")
            return jsonify({"error": "Print order not found"}), 404

        # Process the webhook based on event type
        status_changed = False
        previous_status = print_order.status
        message = f"Received {event_type} event from Lulu"

        if event_type in ["print_job.validation.completed", "validation_completed"]:
            # File validation completed
            validation_result = print_job_data.get(
                "validation_result"
            ) or print_job_data.get("status")

            if validation_result == "APPROVED" or validation_result == "approved":
                print_order.status = PrintOrderStatus.PROCESSING
                print_order.interior_validation_status = "approved"
                print_order.cover_validation_status = "approved"
                message = "Files validated successfully - ready for printing"
                status_changed = True
            elif validation_result == "REJECTED" or validation_result == "rejected":
                print_order.status = PrintOrderStatus.FAILED
                print_order.interior_validation_status = "rejected"
                print_order.cover_validation_status = "rejected"

                # Extract validation errors
                errors = print_job_data.get("validation_errors", [])
                if errors:
                    print_order.interior_validation_errors = str(errors)
                    print_order.cover_validation_errors = str(errors)

                message = f"File validation failed: {errors}"
                status_changed = True

        elif event_type in ["print_job.printing", "printing_started"]:
            print_order.status = PrintOrderStatus.PRINTING
            message = "Order is being printed"
            status_changed = True

        elif event_type in ["print_job.shipped", "shipped"]:
            print_order.status = PrintOrderStatus.SHIPPED
            print_order.shipped_at = datetime.utcnow()

            # Update shipping information
            shipping_info = print_job_data.get("shipping", {})
            if shipping_info:
                print_order.shipping_carrier = shipping_info.get("carrier")
                print_order.tracking_number = shipping_info.get("tracking_number")
                print_order.tracking_url = shipping_info.get("tracking_url")

                # Parse estimated delivery date if provided
                estimated_delivery = shipping_info.get("estimated_delivery_date")
                if estimated_delivery:
                    try:
                        print_order.estimated_delivery_date = datetime.fromisoformat(
                            estimated_delivery.replace("Z", "+00:00")
                        )
                    except ValueError:
                        logger.warning(
                            f"Invalid delivery date format: {estimated_delivery}"
                        )

            message = f"Order shipped with tracking: {print_order.tracking_number}"
            status_changed = True

        elif event_type in ["print_job.delivered", "delivered"]:
            print_order.status = PrintOrderStatus.DELIVERED
            print_order.actual_delivery_date = datetime.utcnow()
            message = "Order delivered successfully"
            status_changed = True

        elif event_type in ["print_job.cancelled", "cancelled"]:
            print_order.status = PrintOrderStatus.CANCELLED
            print_order.cancelled_at = datetime.utcnow()
            message = "Order cancelled by Lulu"
            status_changed = True

        elif event_type in ["print_job.failed", "failed"]:
            print_order.status = PrintOrderStatus.FAILED

            # Extract failure reason
            failure_reason = print_job_data.get("failure_reason") or print_job_data.get(
                "error_message"
            )
            if failure_reason:
                message = f"Order failed: {failure_reason}"
            else:
                message = "Order failed during processing"

            status_changed = True

        else:
            # Unknown event type - log but don't change status
            logger.info(f"Received unknown Lulu event type: {event_type}")
            message = f"Unknown event type: {event_type}"

        # Update Lulu status tracking
        print_order.lulu_status = print_job_data.get("status")

        # Create status update record if status changed
        if status_changed:
            status_update = PrintOrderStatusUpdate(
                print_order_id=print_order.id,
                previous_status=previous_status,
                new_status=print_order.status,
                message=message,
                lulu_event_type=event_type,
                lulu_event_data=data,
            )
            db.session.add(status_update)

            logger.info(
                f"Print order {print_order.order_number} status changed: {previous_status.value} -> {print_order.status.value}"
            )

        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Webhook processed successfully",
                "order_number": print_order.order_number,
                "status_changed": status_changed,
            }
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing Lulu webhook: {str(e)}")
        logger.error(f"Webhook data: {request.get_json()}")
        return jsonify({"error": "Failed to process webhook"}), 500


@bp.route("/lulu-validation", methods=["POST"])
@limiter.limit("100/hour")
def handle_lulu_validation_webhook():
    """Handle file validation webhooks from Lulu."""
    try:
        # Get the raw payload for signature verification
        payload = request.get_data()
        signature = request.headers.get("X-Hub-Signature-256") or request.headers.get(
            "X-Lulu-Signature"
        )
        webhook_secret = current_app.config.get("LULU_WEBHOOK_SECRET")

        # Verify webhook signature if configured
        if not verify_webhook_signature(payload, signature, webhook_secret):
            logger.warning(f"Invalid webhook signature from IP {request.remote_addr}")
            return jsonify({"error": "Invalid signature"}), 401

        # Parse webhook data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "Empty request body"}), 400

        logger.info(f"Received Lulu validation webhook: {data}")

        # Extract validation information
        print_job_id = data.get("print_job_id") or data.get("id")
        if not print_job_id:
            return jsonify({"error": "Missing print_job_id"}), 400

        # Find the corresponding print order
        print_order = PrintOrder.query.filter_by(
            lulu_print_job_id=str(print_job_id)
        ).first()
        if not print_order:
            logger.warning(f"No print order found for Lulu job {print_job_id}")
            return jsonify({"error": "Print order not found"}), 404

        # Update validation status
        previous_status = print_order.status

        # Process interior file validation
        interior = data.get("interior", {})
        if interior:
            print_order.interior_validation_status = interior.get("status")
            if interior.get("errors"):
                print_order.interior_validation_errors = str(interior["errors"])

        # Process cover file validation
        cover = data.get("cover", {})
        if cover:
            print_order.cover_validation_status = cover.get("status")
            if cover.get("errors"):
                print_order.cover_validation_errors = str(cover["errors"])

        # Update overall status based on validation results
        interior_approved = print_order.interior_validation_status == "approved"
        cover_approved = print_order.cover_validation_status == "approved"
        interior_rejected = print_order.interior_validation_status == "rejected"
        cover_rejected = print_order.cover_validation_status == "rejected"

        status_changed = False
        message = "Validation status updated"

        if interior_approved and cover_approved:
            print_order.status = PrintOrderStatus.PROCESSING
            message = "All files validated successfully - ready for printing"
            status_changed = True
        elif interior_rejected or cover_rejected:
            print_order.status = PrintOrderStatus.FAILED
            message = "File validation failed - order cannot proceed"
            status_changed = True

        # Create status update record if status changed
        if status_changed:
            status_update = PrintOrderStatusUpdate(
                print_order_id=print_order.id,
                previous_status=previous_status,
                new_status=print_order.status,
                message=message,
                lulu_event_type="validation_update",
                lulu_event_data=data,
            )
            db.session.add(status_update)

            logger.info(
                f"Print order {print_order.order_number} validation status updated"
            )

        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Validation webhook processed successfully",
                "order_number": print_order.order_number,
                "interior_status": print_order.interior_validation_status,
                "cover_status": print_order.cover_validation_status,
            }
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing Lulu validation webhook: {str(e)}")
        logger.error(f"Webhook data: {request.get_json()}")
        return jsonify({"error": "Failed to process validation webhook"}), 500


@bp.route("/test", methods=["POST", "GET"])
def test_webhook():
    """Test endpoint for webhook development and debugging. Development only."""
    if not current_app.debug:
        return jsonify({"error": "Not found"}), 404
    if request.method == "GET":
        return jsonify(
            {
                "status": "ok",
                "message": "Webhook endpoint is working",
                "endpoints": [
                    "/print-webhooks/lulu-status - Handle order status updates",
                    "/print-webhooks/lulu-validation - Handle file validation results",
                    "/print-webhooks/test - This test endpoint",
                ],
            }
        )

    # POST method - log the webhook data
    data = request.get_json() if request.is_json else {}
    headers = dict(request.headers)

    logger.info("Test webhook received:")
    logger.info(f"Headers: {headers}")
    logger.info(f"Data: {data}")

    return jsonify(
        {
            "status": "received",
            "message": "Test webhook data logged",
            "received_data": data,
            "received_headers": headers,
        }
    )
