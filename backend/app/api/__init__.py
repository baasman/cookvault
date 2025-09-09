from flask import Blueprint

bp = Blueprint("api", __name__)

from app.api import recipes, auth, cookbooks, public, recipe_groups, payments, exports, print_orders, print_webhooks

# Register sub-blueprints
bp.register_blueprint(exports.bp)
bp.register_blueprint(print_orders.bp)
bp.register_blueprint(print_webhooks.bp)