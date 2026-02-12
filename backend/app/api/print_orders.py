"""
API endpoints for print-on-demand orders via Lulu.

This module provides REST endpoints for managing cookbook print orders,
including cost estimation, order creation, and status tracking.
"""

import logging
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import db
from app.api.auth import require_auth
from app.models.recipe import Cookbook
from app.models.print_order import (
    PrintOrder,
    PrintSpecification,
    PrintOrderStatus,
    TrimSize,
    BindingType,
    PaperType,
    CoverFinish,
)
from app.services.lulu_service import LuluService
from app.services.pdf_service import PDFService
from app.services.cover_generation_service import CoverGenerationService
from app.services.stripe_service import StripeService
from app.utils.validation import validate_json_data

bp = Blueprint("print_orders", __name__, url_prefix="/print-orders")
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


@bp.route("/specifications", methods=["GET"])
@require_auth
def get_print_specifications(current_user):
    """Get available print specifications and options.

    Query params:
        cookbook_id: Optional cookbook ID to get estimated page count
    """
    try:
        cover_service = CoverGenerationService()

        # Get bulk pricing information
        lulu_service = LuluService()
        bulk_pricing_tiers = lulu_service.get_bulk_pricing_tiers()

        response_data = {
            "trim_sizes": [
                {"value": size.value, "name": size.value} for size in TrimSize
            ],
            "binding_types": [
                {"value": bt.value, "name": bt.value} for bt in BindingType
            ],
            "paper_types": [{"value": pt.value, "name": pt.value} for pt in PaperType],
            "cover_finishes": [
                {"value": cf.value, "name": cf.value} for cf in CoverFinish
            ],
            "templates": [
                {
                    "value": "modern",
                    "label": "Modern Minimalist",
                    "description": "Clean, contemporary design with Inter and Lora fonts",
                },
                {
                    "value": "classic",
                    "label": "Classic",
                    "description": "Traditional professional layout with Helvetica",
                },
                {
                    "value": "book",
                    "label": "Book Style",
                    "description": "Elegant two-column layout with serif fonts",
                },
            ],
            "cover_templates": cover_service.get_available_templates(),
            "bulk_pricing_tiers": bulk_pricing_tiers,
        }

        # If cookbook_id provided, calculate estimated page count
        cookbook_id = request.args.get("cookbook_id", type=int)
        if cookbook_id:
            cookbook = Cookbook.query.get(cookbook_id)
            # Reject Google Books cookbooks - print orders only allowed for user-owned cookbooks
            if cookbook and cookbook.google_books_id is not None:
                return jsonify(
                    {
                        "error": "Print orders are not available for Google Books cookbooks"
                    }
                ), 400
            if cookbook and cookbook.user_id == current_user.id:
                recipe_count = len(cookbook.get_recipes_for_user(current_user.id))
                response_data["estimated_page_count"] = (
                    cover_service.estimate_page_count(recipe_count)
                )
                response_data["recipe_count"] = recipe_count

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error getting print specifications: {str(e)}")
        return jsonify({"error": "Failed to get print specifications"}), 500


@bp.route("/validate-cover", methods=["POST"])
@require_auth
def validate_cover_data(current_user):
    """Validate cookbook data for cover generation."""
    try:
        required_fields = ["cookbook_id", "trim_size"]
        data = validate_json_data(request, required_fields)
        if isinstance(data, tuple):  # Error response
            return data

        # Check cookbook access
        cookbook = Cookbook.query.get(data["cookbook_id"])
        if not cookbook:
            return jsonify({"error": "Cookbook not found"}), 404

        if cookbook.user_id != current_user.id:
            return jsonify({"error": "Access denied"}), 403

        # Validate trim size
        try:
            trim_size = TrimSize(data["trim_size"])
        except ValueError:
            return jsonify({"error": "Invalid trim size"}), 400

        # Get cookbook data
        cookbook_dict = cookbook.to_dict(current_user_id=current_user.id)

        # Validate with cover service
        cover_service = CoverGenerationService()
        validation_result = cover_service.validate_cover_content(
            cookbook_dict, trim_size
        )

        return jsonify(validation_result)

    except Exception as e:
        logger.error(f"Error validating cover data: {str(e)}")
        return jsonify({"error": "Failed to validate cover data"}), 500


@bp.route("/quote", methods=["POST"])
@require_auth
@limiter.limit("10/minute")
def get_print_quote(current_user):
    """Get a quote for printing a cookbook."""
    try:
        # Validate request data
        required_fields = ["cookbook_id", "quantity", "specification"]
        data = validate_json_data(request, required_fields)
        if isinstance(data, tuple):  # Error response
            return data

        # Validate specification fields
        spec_required = [
            "trim_size",
            "binding_type",
            "paper_type",
            "cover_finish",
            "page_count",
        ]
        spec_data = data.get("specification", {})
        for field in spec_required:
            if field not in spec_data:
                return jsonify({"error": f"Missing specification field: {field}"}), 400

        # Check cookbook access
        cookbook = Cookbook.query.get(data["cookbook_id"])
        if not cookbook:
            return jsonify({"error": "Cookbook not found"}), 404

        if cookbook.user_id != current_user.id:
            return jsonify({"error": "Access denied"}), 403

        # Reject Google Books cookbooks - print orders only allowed for user-owned cookbooks
        if cookbook.google_books_id is not None:
            return jsonify(
                {"error": "Print orders are not available for Google Books cookbooks"}
            ), 400

        # Validate template if provided
        template = spec_data.get("template", "modern")
        if template not in ("modern", "classic", "book"):
            return jsonify(
                {
                    "error": f"Invalid template: {template}. Must be modern, classic, or book."
                }
            ), 400

        # Create specification object for quote
        try:
            specification = PrintSpecification(
                trim_size=TrimSize(spec_data["trim_size"]),
                binding_type=BindingType(spec_data["binding_type"]),
                paper_type=PaperType(spec_data["paper_type"]),
                cover_finish=CoverFinish(spec_data["cover_finish"]),
                page_count=int(spec_data["page_count"]),
                color_pages=spec_data.get("color_pages", False),
                template=template,
            )
        except ValueError as e:
            return jsonify({"error": f"Invalid specification value: {str(e)}"}), 400

        # Extract shipping information for accurate pricing
        shipping_country = "US"  # Default
        shipping_state = None

        if "shipping_address" in data:
            shipping_data = data["shipping_address"]
            shipping_country = shipping_data.get("country_code", "US")
            shipping_state = shipping_data.get("state_code")

        # Get quote from Lulu
        lulu_service = LuluService()
        quote = lulu_service.get_print_quote(
            specification=specification,
            quantity=data["quantity"],
            shipping_country=shipping_country,
            shipping_state=shipping_state,
        )

        if not quote:
            return jsonify({"error": "Failed to get quote from Lulu"}), 500

        return jsonify(
            {
                "cookbook_id": cookbook.id,
                "cookbook_title": cookbook.title,
                "quantity": data["quantity"],
                "specification": {
                    "trim_size": spec_data["trim_size"],
                    "binding_type": spec_data["binding_type"],
                    "paper_type": spec_data["paper_type"],
                    "cover_finish": spec_data["cover_finish"],
                    "template": template,
                    "page_count": spec_data["page_count"],
                    "color_pages": spec_data.get("color_pages", False),
                },
                "costs": {
                    "printing_cost": float(quote["printing_cost"]),
                    "shipping_cost": float(quote["shipping_cost"]),
                    "tax_amount": float(quote["tax_amount"]),
                    "platform_fee": float(quote["platform_fee"]),
                    "total_cost": float(quote["total_cost"]),
                },
                "estimated_delivery_days": quote["estimated_delivery_days"],
                "valid_until": quote["valid_until"],
                "quote_id": quote["quote_id"],
                "shipping_destination": {
                    "country": shipping_country,
                    "state": shipping_state,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting print quote: {str(e)}")
        logger.error(f"Quote request data: {request.get_json()}")
        return jsonify({"error": "Failed to get print quote"}), 500


@bp.route("/", methods=["POST"])
@require_auth
@limiter.limit("5/minute")
def create_print_order(current_user):
    """Create a new print order."""
    try:
        # Validate request data
        required_fields = [
            "cookbook_id",
            "quantity",
            "specification",
            "shipping_address",
        ]
        data = validate_json_data(request, required_fields)
        if isinstance(data, tuple):  # Error response
            return data

        # Check cookbook access
        cookbook = Cookbook.query.get(data["cookbook_id"])
        if not cookbook:
            return jsonify({"error": "Cookbook not found"}), 404

        if cookbook.user_id != current_user.id:
            return jsonify({"error": "Access denied"}), 403

        # Reject Google Books cookbooks - print orders only allowed for user-owned cookbooks
        if cookbook.google_books_id is not None:
            return jsonify(
                {"error": "Print orders are not available for Google Books cookbooks"}
            ), 400

        # Validate shipping address
        shipping_required = [
            "name",
            "address_line1",
            "city",
            "state_code",
            "postal_code",
            "country_code",
            "email",
        ]
        shipping_data = data.get("shipping_address", {})
        for field in shipping_required:
            if field not in shipping_data:
                return jsonify({"error": f"Missing shipping field: {field}"}), 400

        # Create and save specification
        spec_data = data["specification"]

        # Validate template if provided
        template = spec_data.get("template", "modern")
        if template not in ("modern", "classic", "book"):
            return jsonify(
                {
                    "error": f"Invalid template: {template}. Must be modern, classic, or book."
                }
            ), 400

        try:
            specification = PrintSpecification(
                trim_size=TrimSize(spec_data["trim_size"]),
                binding_type=BindingType(spec_data["binding_type"]),
                paper_type=PaperType(spec_data["paper_type"]),
                cover_finish=CoverFinish(spec_data["cover_finish"]),
                page_count=int(spec_data["page_count"]),
                color_pages=spec_data.get("color_pages", False),
                template=template,
            )
            db.session.add(specification)
            db.session.flush()  # Get the ID
        except ValueError as e:
            return jsonify({"error": f"Invalid specification value: {str(e)}"}), 400

        # Get fresh quote for pricing using shipping information
        lulu_service = LuluService()
        quote = lulu_service.get_print_quote(
            specification=specification,
            quantity=data["quantity"],
            shipping_country=shipping_data.get("country_code", "US"),
            shipping_state=shipping_data.get("state_code"),
        )

        if not quote:
            return jsonify({"error": "Failed to get current pricing"}), 500

        # Generate unique order number
        order_number = f"CKB-{datetime.utcnow().strftime('%Y%m%d')}-{current_user.id:04d}-{len(current_user.print_orders) + 1:03d}"

        # Create print order
        print_order = PrintOrder(
            user_id=current_user.id,
            cookbook_id=cookbook.id,
            specification_id=specification.id,
            order_number=order_number,
            quantity=data["quantity"],
            status=PrintOrderStatus.DRAFT,
            # Shipping info
            shipping_name=shipping_data["name"],
            shipping_address_line1=shipping_data["address_line1"],
            shipping_address_line2=shipping_data.get("address_line2"),
            shipping_city=shipping_data["city"],
            shipping_state_code=shipping_data["state_code"],
            shipping_postal_code=shipping_data["postal_code"],
            shipping_country_code=shipping_data["country_code"],
            shipping_phone=shipping_data.get("phone"),
            shipping_email=shipping_data["email"],
            # Costs
            printing_cost=quote["printing_cost"],
            shipping_cost=quote["shipping_cost"],
            tax_amount=quote["tax_amount"],
            platform_fee=quote["platform_fee"],
            total_cost=quote["total_cost"],
            # Metadata
            order_metadata=data.get("metadata", {}),
        )

        db.session.add(print_order)
        db.session.commit()

        logger.info(f"Created print order {order_number} for user {current_user.id}")

        return jsonify(
            {
                "order": print_order.to_dict(include_shipping=True),
                "message": "Print order created successfully",
            }
        ), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating print order: {str(e)}")
        logger.error(f"Order creation data: {request.get_json()}")
        return jsonify({"error": "Failed to create print order"}), 500


@bp.route("/<int:order_id>/payment", methods=["POST"])
@require_auth
@limiter.limit("5/minute")
def create_print_order_payment(current_user, order_id):
    """Create a payment intent for a print order."""
    try:
        order = PrintOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({"error": "Print order not found"}), 404

        if order.status != PrintOrderStatus.DRAFT:
            return jsonify(
                {"error": "Payment can only be created for draft orders"}
            ), 400

        # Create Stripe payment intent
        stripe_service = StripeService()
        payment_intent_data = stripe_service.create_print_order_payment_intent(
            current_user, order
        )

        # Update order status to pending payment
        order.status = PrintOrderStatus.PENDING_PAYMENT
        order.stripe_payment_intent_id = payment_intent_data["payment_intent_id"]

        # Create status update
        from app.models.print_order import PrintOrderStatusUpdate

        status_update = PrintOrderStatusUpdate(
            print_order_id=order.id,
            previous_status=PrintOrderStatus.DRAFT,
            new_status=PrintOrderStatus.PENDING_PAYMENT,
            message="Payment intent created - awaiting payment completion",
        )
        db.session.add(status_update)

        db.session.commit()

        logger.info(f"Created payment intent for print order {order.order_number}")

        return jsonify({"payment_intent": payment_intent_data}), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Error creating payment intent for print order {order_id}: {str(e)}"
        )
        return jsonify({"error": "Failed to create payment intent"}), 500


@bp.route("/", methods=["GET"])
@require_auth
def list_print_orders(current_user):
    """List user's print orders."""
    try:
        # Get pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 10, type=int), 50)
        status_filter = request.args.get("status")

        # Build query
        query = PrintOrder.query.filter_by(user_id=current_user.id)

        if status_filter:
            try:
                status_enum = PrintOrderStatus(status_filter)
                query = query.filter_by(status=status_enum)
            except ValueError:
                return jsonify({"error": f"Invalid status: {status_filter}"}), 400

        # Order by most recent first
        query = query.order_by(PrintOrder.created_at.desc())

        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        orders = [order.to_dict() for order in pagination.items]

        return jsonify(
            {
                "orders": orders,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error listing print orders: {str(e)}")
        return jsonify({"error": "Failed to list print orders"}), 500


@bp.route("/<int:order_id>", methods=["GET"])
@require_auth
def get_print_order(current_user, order_id):
    """Get a specific print order."""
    try:
        order = PrintOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({"error": "Print order not found"}), 404

        return jsonify(
            {
                "order": order.to_dict(include_shipping=True),
                "status_updates": [update.to_dict() for update in order.status_updates],
            }
        )

    except Exception as e:
        logger.error(f"Error getting print order {order_id}: {str(e)}")
        return jsonify({"error": "Failed to get print order"}), 500


@bp.route("/<int:order_id>/submit", methods=["POST"])
@require_auth
@limiter.limit("3/minute")
def submit_print_order(current_user, order_id):
    """Submit a print order for processing (initiate payment and print job)."""
    try:
        order = PrintOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({"error": "Print order not found"}), 404

        if order.status != PrintOrderStatus.PAID:
            return jsonify(
                {"error": "Order can only be submitted after payment is completed"}
            ), 400

        # Generate PDF files for the cookbook
        pdf_service = PDFService()
        lulu_service = LuluService()

        # Get cookbook data
        cookbook_dict = order.cookbook.to_dict(current_user_id=current_user.id)
        recipes = order.cookbook.get_recipes_for_user(current_user.id)
        recipes_dict = [
            recipe.to_dict(current_user_id=current_user.id, is_admin=True)
            for recipe in recipes
        ]

        # Generate print-ready interior PDF
        try:
            # Create print-ready configuration with selected template
            from app.services.pdf_service import PDFConfig, PDFTemplate

            # Map specification template to PDFTemplate enum
            template_map = {
                "classic": PDFTemplate.CLASSIC,
                "modern": PDFTemplate.MODERN,
                "book": PDFTemplate.BOOK,
            }
            selected_template = template_map.get(
                order.specification.template, PDFTemplate.MODERN
            )

            print_config = PDFConfig(
                template=selected_template
            ).enable_print_ready_mode(
                trim_size=order.specification.trim_size.value, include_marks=True
            )
            print_config.gutter_adjustment = True  # Add binding margin

            interior_pdf = pdf_service.generate_cookbook_pdf(
                cookbook_dict, recipes_dict, print_config
            )

            # Upload interior PDF using new method
            interior_filename = f"interior_{order.order_number}"
            interior_url = lulu_service.upload_interior_pdf(
                interior_pdf, interior_filename
            )

            if not interior_url:
                return jsonify({"error": "Failed to upload interior PDF"}), 500

            order.interior_file_url = interior_url

            logger.info(
                f"Generated and uploaded print-ready interior PDF for order {order.order_number}"
            )
        except Exception as e:
            lulu_service.handle_api_error(e, "interior PDF generation/upload")
            return jsonify({"error": "Failed to prepare interior file"}), 500

        # Generate print-ready cover PDF
        try:
            from app.services.cover_generation_service import CoverGenerationService

            cover_service = CoverGenerationService()

            # Estimate page count for spine calculation
            estimated_pages = cover_service.estimate_page_count(len(recipes_dict))

            # Map specification template to cover template name
            cover_template_map = {
                "classic": "classic",
                "modern": "minimalist",  # Modern uses minimalist cover
                "book": "book",
            }
            cover_template = cover_template_map.get(
                order.specification.template, "minimalist"
            )

            cover_pdf = cover_service.generate_cover_pdf(
                cookbook_data=cookbook_dict,
                trim_size=order.specification.trim_size,
                page_count=estimated_pages,
                template_name=cover_template,
                binding_type=order.specification.binding_type.value.lower(),
            )

            # Upload cover PDF using new method
            cover_filename = f"cover_{order.order_number}"
            cover_url = lulu_service.upload_cover_pdf(cover_pdf, cover_filename)

            if not cover_url:
                return jsonify({"error": "Failed to upload cover PDF"}), 500

            order.cover_file_url = cover_url

            logger.info(
                f"Generated and uploaded print-ready cover PDF for order {order.order_number}"
            )
        except Exception as e:
            lulu_service.handle_api_error(e, "cover PDF generation/upload")
            return jsonify({"error": "Failed to prepare cover file"}), 500

        # Submit to Lulu for validation and print job creation
        try:
            print_job_result = lulu_service.create_print_job(order)

            # Update order with Lulu details
            order.lulu_print_job_id = print_job_result.get("print_job_id")
            order.lulu_line_item_id = print_job_result.get("line_item_id")
            order.lulu_status = print_job_result.get("status")
            order.status = PrintOrderStatus.PROCESSING
            order.submitted_at = datetime.utcnow()

            logger.info(
                f"Successfully created Lulu print job {order.lulu_print_job_id} for order {order.order_number}"
            )

        except Exception as e:
            lulu_service.handle_api_error(e, "print job creation")
            return jsonify({"error": "Failed to submit print job to Lulu"}), 500

        # Create status update
        from app.models.print_order import PrintOrderStatusUpdate

        status_update = PrintOrderStatusUpdate(
            print_order_id=order.id,
            previous_status=PrintOrderStatus.PAID,
            new_status=PrintOrderStatus.PROCESSING,
            message="Order submitted for processing and validation",
        )
        db.session.add(status_update)

        db.session.commit()

        logger.info(
            f"Submitted print order {order.order_number} (Lulu job: {order.lulu_print_job_id})"
        )

        return jsonify(
            {
                "order": order.to_dict(include_shipping=True),
                "message": "Print order submitted successfully",
            }
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting print order {order_id}: {str(e)}")
        return jsonify({"error": "Failed to submit print order"}), 500


@bp.route("/<int:order_id>/refund-eligibility", methods=["GET"])
@require_auth
def check_refund_eligibility(current_user, order_id):
    """Check refund eligibility for a print order."""
    try:
        order = PrintOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({"error": "Print order not found"}), 404

        # Check refund eligibility
        stripe_service = StripeService()
        refund_eligibility = stripe_service.calculate_refund_eligibility(order)

        return jsonify(
            {
                "order_id": order.id,
                "order_number": order.order_number,
                "order_status": order.status.value,
                "can_cancel": order.can_cancel(),
                "refund_eligibility": refund_eligibility,
                "total_paid": float(order.total_cost),
            }
        )

    except Exception as e:
        logger.error(
            f"Error checking refund eligibility for order {order_id}: {str(e)}"
        )
        return jsonify({"error": "Failed to check refund eligibility"}), 500


@bp.route("/<int:order_id>/refund", methods=["POST"])
@require_auth
def create_manual_refund(current_user, order_id):
    """Create a manual refund for a print order."""
    try:
        order = PrintOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({"error": "Print order not found"}), 404

        # Parse request data for refund details
        data = request.get_json()
        refund_amount = data.get("amount")  # Amount in dollars
        refund_reason = data.get("reason", "Manual refund requested")

        # Validate refund amount if provided
        if refund_amount is not None:
            refund_amount = Decimal(str(refund_amount))
            if refund_amount <= 0 or refund_amount > order.total_cost:
                return jsonify({"error": "Invalid refund amount"}), 400

        # Check refund eligibility
        stripe_service = StripeService()
        refund_eligibility = stripe_service.calculate_refund_eligibility(order)

        if not refund_eligibility["eligible"]:
            return jsonify(
                {"error": f"Refund not eligible: {refund_eligibility['reason']}"}
            ), 400

        # Process refund
        try:
            refund_info = stripe_service.create_print_order_refund(
                print_order=order,
                refund_reason=refund_reason,
                partial_amount=refund_amount,
            )

            if not refund_info:
                return jsonify({"error": "No payment found to refund"}), 400

            # Create status update
            from app.models.print_order import PrintOrderStatusUpdate

            amount_text = (
                f"${refund_amount:.2f}" if refund_amount else f"${order.total_cost:.2f}"
            )
            status_update = PrintOrderStatusUpdate(
                print_order_id=order.id,
                previous_status=order.status,
                new_status=order.status,  # Status might have been updated by refund processing
                message=f"Manual refund processed: {amount_text} - {refund_reason}",
            )
            db.session.add(status_update)
            db.session.commit()

            logger.info(
                f"Manual refund processed for order {order.order_number}: {refund_info.get('refund_id')}"
            )

            return jsonify(
                {
                    "order": order.to_dict(include_shipping=True),
                    "refund_info": refund_info,
                    "message": "Refund processed successfully",
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to process manual refund for order {order.order_number}: {str(e)}"
            )
            return jsonify({"error": "Failed to process refund"}), 500

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing manual refund for order {order_id}: {str(e)}")
        return jsonify({"error": "Failed to process refund request"}), 500


@bp.route("/<int:order_id>/cancel", methods=["POST"])
@require_auth
def cancel_print_order(current_user, order_id):
    """Cancel a print order."""
    try:
        order = PrintOrder.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({"error": "Print order not found"}), 404

        if not order.can_cancel():
            return jsonify(
                {"error": f"Order cannot be cancelled in {order.status.value} status"}
            ), 400

        # Initialize Stripe service for refund processing
        stripe_service = StripeService()
        refund_info = None

        # Check refund eligibility
        refund_eligibility = stripe_service.calculate_refund_eligibility(order)

        # Process refund if eligible and payment exists
        if refund_eligibility["eligible"]:
            try:
                refund_info = stripe_service.create_print_order_refund(
                    print_order=order,
                    refund_reason="Order cancelled by user",
                    partial_amount=Decimal(str(refund_eligibility["refund_amount"]))
                    if refund_eligibility["refund_percentage"] < 100
                    else None,
                )
            except Exception as e:
                logger.error(
                    f"Failed to process refund for order {order.order_number}: {str(e)}"
                )
                # Continue with cancellation even if refund fails
                refund_info = {"error": str(e)}

        # Cancel with Lulu if needed
        lulu_cancel_success = True
        if order.lulu_print_job_id:
            lulu_service = LuluService()
            cancel_result = lulu_service.cancel_print_job(order.lulu_print_job_id)
            if not cancel_result:
                logger.warning(
                    f"Failed to cancel print job {order.lulu_print_job_id} with Lulu"
                )
                lulu_cancel_success = False

        # Update order status (may have been updated by refund processing)
        previous_status = order.status
        final_status = (
            PrintOrderStatus.REFUNDED
            if (refund_info and "refund_id" in refund_info)
            else PrintOrderStatus.CANCELLED
        )
        order.status = final_status
        order.cancelled_at = datetime.utcnow()

        # Create status update
        from app.models.print_order import PrintOrderStatusUpdate

        if refund_info and "refund_id" in refund_info:
            message = f"Order cancelled and refunded (${refund_eligibility['refund_amount']:.2f})"
        else:
            message = "Order cancelled by user"

        status_update = PrintOrderStatusUpdate(
            print_order_id=order.id,
            previous_status=previous_status,
            new_status=final_status,
            message=message,
        )
        db.session.add(status_update)

        db.session.commit()

        logger.info(
            f"Cancelled print order {order.order_number} - Status: {final_status.value}"
        )

        response_data = {
            "order": order.to_dict(include_shipping=True),
            "message": "Print order cancelled successfully",
            "refund_eligibility": refund_eligibility,
            "lulu_cancel_success": lulu_cancel_success,
        }

        if refund_info:
            response_data["refund_info"] = refund_info

        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling print order {order_id}: {str(e)}")
        return jsonify({"error": "Failed to cancel print order"}), 500


@bp.route("/<int:order_id>/reorder", methods=["POST"])
@require_auth
def reorder_print_order(current_user, order_id):
    """Create a new order based on an existing order."""
    try:
        original_order = PrintOrder.query.filter_by(
            id=order_id, user_id=current_user.id
        ).first()
        if not original_order:
            return jsonify({"error": "Original print order not found"}), 404

        if not original_order.can_reorder():
            return jsonify(
                {
                    "error": f"Order cannot be reordered from {original_order.status.value} status"
                }
            ), 400

        # Get updated pricing using original shipping information
        lulu_service = LuluService()
        quote = lulu_service.get_print_quote(
            specification=original_order.specification,
            quantity=original_order.quantity,
            shipping_country=original_order.shipping_country_code,
            shipping_state=original_order.shipping_state_code,
        )

        if not quote:
            return jsonify({"error": "Failed to get current pricing for reorder"}), 500

        # Generate new order number
        order_number = f"CKB-{datetime.utcnow().strftime('%Y%m%d')}-{current_user.id:04d}-{len(current_user.print_orders) + 1:03d}"

        # Create new order
        new_order = PrintOrder(
            user_id=current_user.id,
            cookbook_id=original_order.cookbook_id,
            specification_id=original_order.specification_id,
            order_number=order_number,
            quantity=original_order.quantity,
            status=PrintOrderStatus.DRAFT,
            # Copy shipping info
            shipping_name=original_order.shipping_name,
            shipping_address_line1=original_order.shipping_address_line1,
            shipping_address_line2=original_order.shipping_address_line2,
            shipping_city=original_order.shipping_city,
            shipping_state_code=original_order.shipping_state_code,
            shipping_postal_code=original_order.shipping_postal_code,
            shipping_country_code=original_order.shipping_country_code,
            shipping_phone=original_order.shipping_phone,
            shipping_email=original_order.shipping_email,
            # Updated costs
            printing_cost=quote["printing_cost"],
            shipping_cost=quote["shipping_cost"],
            tax_amount=quote["tax_amount"],
            platform_fee=quote["platform_fee"],
            total_cost=quote["total_cost"],
            # Copy metadata
            order_metadata=original_order.order_metadata,
        )

        db.session.add(new_order)
        db.session.commit()

        logger.info(
            f"Created reorder {order_number} based on {original_order.order_number}"
        )

        return jsonify(
            {
                "order": new_order.to_dict(include_shipping=True),
                "message": "Reorder created successfully",
            }
        ), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating reorder from {order_id}: {str(e)}")
        return jsonify({"error": "Failed to create reorder"}), 500
