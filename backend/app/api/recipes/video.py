"""
Video and YouTube processing endpoints for recipes.
"""

import traceback
import uuid
from datetime import datetime
from typing import Tuple

from flask import Response, current_app, jsonify, request
from werkzeug.utils import secure_filename

from app import db
from app.api import bp
from app.api.auth import require_auth
from app.models import Cookbook, Recipe
from app.utils.rate_limiting import rate_limit_upload


# Video file constants
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "avi"}
ALLOWED_VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
}


def allowed_video_file(filename: str) -> bool:
    """Check if a filename has an allowed video extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS
    )


@bp.route("/recipes/upload-video", methods=["POST"])
@require_auth
@rate_limit_upload
def upload_recipe_video(current_user) -> Tuple[Response, int]:
    """
    Upload a video file for recipe extraction.

    Accepts video uploads (MP4, MOV, WebM), creates a VideoProcessingJob,
    and queues async processing via Celery.
    """
    from app.models.video_job import VideoProcessingJob, VideoProcessingStatus

    current_app.logger.info(
        f"Video recipe upload request from user {current_user.id} ({current_user.username})"
    )

    try:
        # Check upload limit for free users
        subscription = current_user.get_or_create_subscription()
        if not current_user.can_upload_recipe():
            current_app.logger.warning(
                f"User {current_user.id} ({current_user.username}) reached upload limit"
            )
            return jsonify(
                {
                    "error": "Upload limit reached",
                    "message": f"You've used all {subscription.monthly_upload_count} of your free uploads this month. Upgrade to Premium for unlimited uploads.",
                    "remaining_uploads": 0,
                    "upgrade_required": True,
                }
            ), 403

        # Check for video file in request
        if "video" not in request.files:
            return jsonify({"error": "No video file provided"}), 400

        video_file = request.files["video"]
        if not video_file or video_file.filename == "":
            return jsonify({"error": "No video file selected"}), 400

        # Validate file extension
        if not allowed_video_file(video_file.filename):
            return jsonify(
                {
                    "error": f"Invalid video format. Supported formats: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
                }
            ), 400

        # Validate content type
        content_type = video_file.content_type or ""
        if content_type and content_type not in ALLOWED_VIDEO_CONTENT_TYPES:
            current_app.logger.warning(f"Invalid video content type: {content_type}")
            return jsonify(
                {"error": f"Invalid video content type: {content_type}"}
            ), 400

        # Check file size
        video_file.seek(0, 2)  # Seek to end
        file_size = video_file.tell()
        video_file.seek(0)  # Reset to beginning

        max_size_mb = current_app.config.get("VIDEO_MAX_SIZE_MB", 100)
        max_size_bytes = max_size_mb * 1024 * 1024

        if file_size > max_size_bytes:
            return jsonify(
                {
                    "error": f"Video too large. Maximum size: {max_size_mb}MB, your file: {file_size / (1024 * 1024):.1f}MB"
                }
            ), 400

        # Get optional parameters
        cookbook_id = request.form.get("cookbook_id", type=int)
        is_original_recipe = (
            request.form.get("is_original_recipe", "false").lower() == "true"
        )
        translate_to_english = (
            request.form.get("translate_to_english", "false").lower() == "true"
        )

        # Handle cookbook creation if requested
        create_new_cookbook = (
            request.form.get("create_new_cookbook", "false").lower() == "true"
        )
        if create_new_cookbook:
            new_cookbook_title = request.form.get("new_cookbook_title", "").strip()
            if not new_cookbook_title:
                return jsonify(
                    {"error": "Cookbook title required when creating new cookbook"}
                ), 400

            cookbook = Cookbook(
                title=new_cookbook_title,
                author=request.form.get("new_cookbook_author", "").strip() or None,
                description=request.form.get("new_cookbook_description", "").strip()
                or None,
                publisher=request.form.get("new_cookbook_publisher", "").strip()
                or None,
                isbn=request.form.get("new_cookbook_isbn", "").strip() or None,
                user_id=current_user.id,
            )
            db.session.add(cookbook)
            db.session.flush()
            cookbook_id = cookbook.id

        # Upload video to Cloudinary for cross-service access
        import cloudinary
        import cloudinary.uploader

        original_filename = secure_filename(video_file.filename)
        video_filename = f"{uuid.uuid4().hex}_{original_filename}"

        current_app.logger.info(
            f"Uploading video to Cloudinary: {video_filename} ({file_size / (1024 * 1024):.1f}MB)"
        )

        # Upload to Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(
                video_file,
                resource_type="video",
                public_id=f"cookle-videos/{video_filename}",
                folder="cookle-videos",
            )
            cloudinary_url = upload_result.get("secure_url")
            cloudinary_public_id = upload_result.get("public_id")
            current_app.logger.info(
                f"Video uploaded to Cloudinary: {cloudinary_public_id}"
            )
        except Exception as cloud_err:
            current_app.logger.error(f"Cloudinary upload failed: {str(cloud_err)}")
            return jsonify({"error": f"Failed to upload video: {str(cloud_err)}"}), 500

        # Create VideoProcessingJob
        video_job = VideoProcessingJob(
            user_id=current_user.id,
            video_filename=video_filename,
            video_original_filename=original_filename,
            video_path=None,  # No local path - using Cloudinary
            video_size_bytes=file_size,
            video_content_type=content_type or "video/mp4",
            cloudinary_public_id=cloudinary_public_id,
            cloudinary_url=cloudinary_url,
            status=VideoProcessingStatus.PENDING,
            progress_message="Queued for processing",
            progress_percentage=0,
            is_original_recipe=is_original_recipe,
            translate_to_english=translate_to_english,
            cookbook_id=cookbook_id,
        )

        db.session.add(video_job)
        db.session.commit()

        current_app.logger.info(
            f"Created VideoProcessingJob {video_job.id} for user {current_user.id}"
        )

        # Queue Celery task
        from app.tasks.recipe_tasks import process_video_recipe_task

        process_video_recipe_task.delay(video_job.id)

        return jsonify(
            {
                "message": "Video uploaded successfully. Processing will begin shortly.",
                "video_job_id": video_job.id,
                "status": video_job.status.value,
            }
        ), 202

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Video upload error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Video upload failed: {str(e)}"}), 500


@bp.route("/recipes/video-job-status/<int:job_id>", methods=["GET"])
@require_auth
def get_video_job_status(current_user, job_id: int) -> Tuple[Response, int]:
    """
    Get the status of a video processing job.

    Returns detailed progress information including current step,
    progress percentage, and the resulting recipe when complete.
    """
    from app.models.video_job import VideoProcessingJob, VideoProcessingStatus

    try:
        # Find the video job belonging to this user
        video_job = VideoProcessingJob.query.filter_by(
            id=job_id, user_id=current_user.id
        ).first()

        if not video_job:
            return jsonify({"error": "Video processing job not found"}), 404

        response_data = video_job.to_dict()

        # If completed and recipe created, include recipe info
        if video_job.status == VideoProcessingStatus.COMPLETED and video_job.recipe_id:
            recipe = Recipe.query.get(video_job.recipe_id)
            if recipe:
                response_data["recipe"] = recipe.to_dict(
                    current_user_id=current_user.id, is_admin=False
                )

        return jsonify(response_data), 200

    except Exception as e:
        current_app.logger.error(f"Error getting video job status: {e}")
        traceback.print_exc()
        return jsonify({"error": "Failed to get job status"}), 500


@bp.route("/recipes/video-job/<int:job_id>/cancel", methods=["POST"])
@require_auth
def cancel_video_job(current_user, job_id: int) -> Tuple[Response, int]:
    """
    Cancel a video recipe processing job.

    Only jobs that haven't completed or failed can be cancelled.
    """
    from app.models.video_job import VideoProcessingJob, VideoProcessingStatus

    try:
        video_job = VideoProcessingJob.query.filter_by(
            id=job_id, user_id=current_user.id
        ).first()

        if not video_job:
            return jsonify({"error": "Video processing job not found"}), 404

        # Check if job can be cancelled (not already completed or failed)
        terminal_states = [
            VideoProcessingStatus.COMPLETED,
            VideoProcessingStatus.FAILED,
            VideoProcessingStatus.CANCELLED
        ]
        if video_job.status in terminal_states:
            return jsonify({
                "error": f"Cannot cancel job with status: {video_job.status.value}"
            }), 400

        # Mark as cancelled
        video_job.status = VideoProcessingStatus.CANCELLED
        video_job.progress_message = "Cancelled by user"
        video_job.completed_at = datetime.utcnow()
        db.session.commit()

        current_app.logger.info(f"Video job {job_id} cancelled by user {current_user.id}")

        return jsonify({"message": "Job cancelled successfully", "status": "cancelled"}), 200

    except Exception as e:
        current_app.logger.error(f"Error cancelling video job: {e}")
        traceback.print_exc()
        return jsonify({"error": "Failed to cancel job"}), 500


@bp.route("/recipes/upload-youtube", methods=["POST"])
@require_auth
@rate_limit_upload
def upload_recipe_youtube(current_user) -> Tuple[Response, int]:
    """
    Import a recipe from a YouTube video URL.

    Accepts JSON with a YouTube URL, creates a VideoProcessingJob,
    and queues async processing via Celery (yt-dlp + captions/audio).
    """
    # Check if YouTube import is enabled
    if not current_app.config.get("YOUTUBE_IMPORT_ENABLED", False):
        return jsonify({
            "error": "YouTube import is temporarily disabled. Please upload video files directly."
        }), 503

    from app.models.video_job import VideoProcessingJob, VideoProcessingStatus
    from app.services.youtube_recipe_service import (
        YouTubeRecipeService,
        YouTubeValidationError,
    )

    current_app.logger.info(
        f"YouTube recipe import request from user {current_user.id} "
        f"({current_user.username})"
    )

    try:
        # Check upload limit for free users
        subscription = current_user.get_or_create_subscription()
        if not current_user.can_upload_recipe():
            current_app.logger.warning(
                f"User {current_user.id} ({current_user.username}) reached upload limit"
            )
            return jsonify(
                {
                    "error": "Upload limit reached",
                    "message": (
                        f"You've used all {subscription.monthly_upload_count} "
                        f"of your free uploads this month. "
                        f"Upgrade to Premium for unlimited uploads."
                    ),
                    "remaining_uploads": 0,
                    "upgrade_required": True,
                }
            ), 403

        # Parse JSON body
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "YouTube URL is required"}), 400

        # Validate URL and extract video ID
        try:
            video_id = YouTubeRecipeService.validate_and_extract_video_id(url)
        except YouTubeValidationError as e:
            return jsonify({"error": str(e)}), 400

        # Get optional parameters
        cookbook_id = data.get("cookbook_id")
        if cookbook_id is not None:
            cookbook_id = int(cookbook_id)
        translate_to_english = bool(data.get("translate_to_english", False))
        is_original_recipe = bool(data.get("is_original_recipe", False))

        # Handle cookbook creation if requested
        create_new_cookbook = bool(data.get("create_new_cookbook", False))
        if create_new_cookbook:
            new_cookbook_title = (data.get("new_cookbook_title") or "").strip()
            if not new_cookbook_title:
                return jsonify(
                    {"error": "Cookbook title required when creating new cookbook"}
                ), 400

            cookbook = Cookbook(
                title=new_cookbook_title,
                author=(data.get("new_cookbook_author") or "").strip() or None,
                description=(
                    (data.get("new_cookbook_description") or "").strip() or None
                ),
                publisher=((data.get("new_cookbook_publisher") or "").strip() or None),
                isbn=(data.get("new_cookbook_isbn") or "").strip() or None,
                user_id=current_user.id,
            )
            db.session.add(cookbook)
            db.session.flush()
            cookbook_id = cookbook.id

        # Create VideoProcessingJob with synthetic file values for YouTube
        video_job = VideoProcessingJob(
            user_id=current_user.id,
            video_filename=f"youtube_{video_id}",
            video_original_filename=f"youtube_{video_id}",
            video_path="youtube",
            video_size_bytes=0,
            video_content_type="video/youtube",
            status=VideoProcessingStatus.PENDING,
            progress_message="Queued for processing",
            progress_percentage=0,
            is_original_recipe=is_original_recipe,
            translate_to_english=translate_to_english,
            cookbook_id=cookbook_id,
            youtube_url=url,
            youtube_video_id=video_id,
        )

        db.session.add(video_job)
        db.session.commit()

        current_app.logger.info(
            f"Created YouTube VideoProcessingJob {video_job.id} "
            f"for video {video_id}, user {current_user.id}"
        )

        # Queue Celery task
        from app.tasks.recipe_tasks import process_youtube_recipe_task

        process_youtube_recipe_task.delay(video_job.id)

        return jsonify(
            {
                "message": "YouTube video queued for processing.",
                "video_job_id": video_job.id,
                "status": video_job.status.value,
            }
        ), 202

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"YouTube upload error: {str(e)}\nTraceback: {traceback.format_exc()}"
        )
        return jsonify({"error": f"YouTube import failed: {str(e)}"}), 500
