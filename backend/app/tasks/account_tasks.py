"""
Celery tasks for account management operations.

These tasks handle background account operations like scheduled deletions
and data exports.
"""

import logging
import traceback
from datetime import datetime

from celery import shared_task

from app import db
from app.models.user import User, UserStatus

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def purge_scheduled_accounts_task(self):
    """
    Celery task to permanently delete accounts that have passed their deletion date.

    This task should be run periodically (e.g., daily via cron or Celery Beat).
    It finds all accounts where:
    - deletion_scheduled_for is not None
    - deletion_scheduled_for <= now
    - deleted_at is None (not already deleted)

    For each account, it:
    1. Deletes all user data (recipes, cookbooks, images, etc.)
    2. Anonymizes payment records (keeping them for legal/accounting)
    3. Marks the account as deleted

    Returns:
        Dict with status and count of deleted accounts
    """
    logger.info(f"[Task {self.request.id}] Starting scheduled account purge task")

    deleted_count = 0
    errors = []

    try:
        # Find accounts due for deletion
        accounts_to_delete = User.query.filter(
            User.deletion_scheduled_for <= datetime.utcnow(),
            User.deletion_scheduled_for.isnot(None),
            User.deleted_at.is_(None),
        ).all()

        logger.info(
            f"[Task {self.request.id}] Found {len(accounts_to_delete)} accounts to purge"
        )

        for user in accounts_to_delete:
            try:
                _purge_user_account(user)
                deleted_count += 1
                logger.info(
                    f"[Task {self.request.id}] Successfully purged account {user.id}"
                )
            except Exception as e:
                error_msg = f"Failed to purge account {user.id}: {str(e)}"
                logger.error(
                    f"[Task {self.request.id}] {error_msg}\n"
                    f"Traceback: {traceback.format_exc()}"
                )
                errors.append(error_msg)
                # Continue with other accounts even if one fails
                db.session.rollback()

        logger.info(
            f"[Task {self.request.id}] Completed account purge task. "
            f"Deleted: {deleted_count}, Errors: {len(errors)}"
        )

        return {
            "status": "success" if not errors else "partial",
            "deleted_count": deleted_count,
            "error_count": len(errors),
            "errors": errors[:5],  # Limit error details
        }

    except Exception as e:
        logger.error(
            f"[Task {self.request.id}] Account purge task failed: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        raise self.retry(exc=e)


def _purge_user_account(user: User) -> None:
    """
    Permanently delete all user data while preserving anonymized payment records.

    This function handles the actual deletion logic, including:
    - Deleting recipe images from Cloudinary
    - Removing all recipes, cookbooks, collections, etc.
    - Anonymizing payment records
    - Marking the account as deleted

    Args:
        user: The User object to purge

    Raises:
        Exception: If any deletion step fails
    """
    from app.services.cloudinary_service import CloudinaryService

    logger.info(f"Starting purge for user {user.id} ({user.email})")

    # Get cloudinary service for image deletion
    try:
        cloudinary_service = CloudinaryService()
    except Exception as e:
        logger.warning(
            f"Cloudinary service unavailable, images may not be deleted: {e}"
        )
        cloudinary_service = None

    # Delete recipe images from Cloudinary
    if cloudinary_service:
        for recipe in user.recipes:
            for image in recipe.images:
                if image.public_id:
                    try:
                        cloudinary_service.delete_image(image.public_id)
                        logger.debug(
                            f"Deleted image {image.public_id} for recipe {recipe.id}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to delete image {image.public_id}: {e}")

    # Delete avatar from Cloudinary if it's a Cloudinary URL
    if user.avatar_url and cloudinary_service and "cloudinary" in user.avatar_url:
        try:
            # Extract public_id from URL
            # Cloudinary URLs typically have format: .../upload/v123/public_id.ext
            parts = user.avatar_url.split("/upload/")
            if len(parts) > 1:
                public_id = parts[1].rsplit(".", 1)[0]  # Remove extension
                if public_id.startswith("v"):
                    # Remove version prefix
                    public_id = "/".join(public_id.split("/")[1:])
                cloudinary_service.delete_image(public_id)
                logger.debug(f"Deleted avatar for user {user.id}")
        except Exception as e:
            logger.warning(f"Failed to delete avatar for user {user.id}: {e}")

    # Anonymize payment records (keep for legal/accounting purposes)
    for payment in user.payments:
        payment.user_id = None  # Orphan the payment record
        # Keep: amount, currency, status, stripe_payment_intent_id, created_at
        # The payment is now anonymous but preserved for accounting

    # Delete subscriptions
    if user.subscription:
        db.session.delete(user.subscription)

    # Delete cookbook purchases (keep payment records, just remove access)
    for purchase in user.cookbook_purchases:
        db.session.delete(purchase)

    # Delete print orders (or orphan them if you need to keep for fulfillment)
    for order in user.print_orders:
        order.user_id = None  # Orphan but keep for fulfillment tracking

    # Delete all recipes (cascade should handle images, notes, comments)
    for recipe in list(user.recipes):
        db.session.delete(recipe)

    # Delete all cookbooks
    for cookbook in list(user.cookbooks):
        db.session.delete(cookbook)

    # Delete recipe groups
    for group in list(user.recipe_groups):
        db.session.delete(group)

    # Delete recipe collections
    for collection in list(user.recipe_collections):
        db.session.delete(collection)

    # Delete recipe notes and comments (should cascade, but be explicit)
    for note in list(user.recipe_notes):
        db.session.delete(note)
    for comment in list(user.recipe_comments):
        db.session.delete(comment)

    # Delete copyright consents
    for consent in list(user.copyright_consents):
        db.session.delete(consent)

    # Delete user sessions
    for session in list(user.user_sessions):
        db.session.delete(session)

    # Delete password history
    for password in list(user.passwords):
        db.session.delete(password)

    # Mark user as deleted (don't actually delete the row for audit purposes)
    user.deleted_at = datetime.utcnow()
    user.status = UserStatus.INACTIVE
    user.email = f"deleted_{user.id}@deleted.local"  # Anonymize email
    user.username = f"deleted_user_{user.id}"  # Anonymize username
    user.password_hash = ""  # Clear password
    user.first_name = None
    user.last_name = None
    user.bio = None
    user.avatar_url = None
    user.phone_number = None
    user.stripe_customer_id = None  # Disconnect from Stripe

    db.session.commit()
    logger.info(f"Successfully purged user {user.id}")
