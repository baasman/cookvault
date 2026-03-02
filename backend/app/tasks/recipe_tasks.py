"""
Celery tasks for recipe image and video processing.

These tasks wrap the existing processing functions to enable
asynchronous, queued execution for better memory management.
"""
import json
import logging
import os
import traceback
from datetime import datetime

from app import db
from app.celery_app import celery
from app.models.recipe import (
    ProcessingJob,
    ProcessingStatus,
    MultiRecipeJob,
    Recipe,
    Ingredient,
    Instruction,
    Tag,
    recipe_ingredients,
)
from app.models.video_job import VideoProcessingJob, VideoProcessingStatus

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=2, default_retry_delay=30)
def process_single_recipe_task(self, job_id: int, user_id: int = None):
    """
    Celery task to process a single recipe image.

    Replaces the threading.Thread approach in upload_recipe().

    Args:
        self: Celery task instance (bound)
        job_id: ID of the ProcessingJob to process
        user_id: Optional user ID for auto-adding to collection

    Returns:
        Dict with status and job_id
    """
    logger.info(f"[Task {self.request.id}] Starting single recipe task for job {job_id}, user {user_id}")

    try:
        job = db.session.get(ProcessingJob, job_id)
        if not job:
            logger.error(f"[Task {self.request.id}] ProcessingJob {job_id} not found")
            return {"status": "error", "message": "Job not found"}

        # Import the existing processing function (inside task to avoid circular imports)
        from app.api.recipes import _process_recipe_image

        # Process the image (this function already handles all the logic)
        _process_recipe_image(job_id, user_id)

        logger.info(f"[Task {self.request.id}] Completed single recipe task for job {job_id}")
        return {"status": "success", "job_id": job_id}

    except Exception as e:
        logger.error(
            f"[Task {self.request.id}] Failed single recipe task for job {job_id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )

        # Update job status to failed
        try:
            job = db.session.get(ProcessingJob, job_id)
            if job:
                job.status = ProcessingStatus.FAILED
                job.error_message = f"Celery task failed: {str(e)[:450]}"
                db.session.commit()
        except Exception as db_error:
            logger.error(f"[Task {self.request.id}] Failed to update job status: {db_error}")

        # Retry the task if retries remain
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=1, default_retry_delay=60)
def process_multi_recipe_task(self, multi_job_id: int):
    """
    Celery task to process multiple images for a single recipe.

    Replaces the synchronous call to process_multi_image_job().

    Args:
        self: Celery task instance (bound)
        multi_job_id: ID of the MultiRecipeJob to process

    Returns:
        Dict with status and multi_job_id
    """
    logger.info(f"[Task {self.request.id}] Starting multi-image task for job {multi_job_id}")

    try:
        multi_job = db.session.get(MultiRecipeJob, multi_job_id)
        if not multi_job:
            logger.error(f"[Task {self.request.id}] MultiRecipeJob {multi_job_id} not found")
            return {"status": "error", "message": "Multi-job not found"}

        # Import the existing processing function (inside task to avoid circular imports)
        from app.api.recipes import process_multi_image_job

        # Process all images (this function already handles all the logic)
        process_multi_image_job(multi_job_id)

        logger.info(f"[Task {self.request.id}] Completed multi-image task for job {multi_job_id}")
        return {"status": "success", "multi_job_id": multi_job_id}

    except Exception as e:
        logger.error(
            f"[Task {self.request.id}] Failed multi-image task for job {multi_job_id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )

        # Update job status to failed
        try:
            multi_job = db.session.get(MultiRecipeJob, multi_job_id)
            if multi_job:
                multi_job.status = ProcessingStatus.FAILED
                multi_job.error_message = f"Celery task failed: {str(e)[:450]}"
                db.session.commit()
        except Exception as db_error:
            logger.error(f"[Task {self.request.id}] Failed to update multi-job status: {db_error}")

        # Retry the task if retries remain
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=2, default_retry_delay=60)
def process_video_recipe_task(self, video_job_id: int):
    """
    Celery task to process a video file and extract a recipe.

    This task:
    1. Extracts audio from the video using FFmpeg
    2. Transcribes audio using OpenAI Whisper
    3. Extracts key frames from the video
    4. Analyzes frames using Claude Vision
    5. Combines transcript + visual analysis into structured recipe
    6. Creates the Recipe in the database

    Args:
        self: Celery task instance (bound)
        video_job_id: ID of the VideoProcessingJob to process

    Returns:
        Dict with status and video_job_id
    """
    logger.info(f"[Task {self.request.id}] Starting video recipe task for job {video_job_id}")

    try:
        # Get the video job
        video_job = db.session.get(VideoProcessingJob, video_job_id)
        if not video_job:
            logger.error(f"[Task {self.request.id}] VideoProcessingJob {video_job_id} not found")
            return {"status": "error", "message": "Video job not found"}

        # Update status to processing
        video_job.update_progress(
            VideoProcessingStatus.EXTRACTING_AUDIO,
            "Extracting audio from video...",
            10
        )
        db.session.commit()

        # Import the video processor (inside task to avoid circular imports)
        from app.services.video_processor import VideoRecipeProcessor, check_ffmpeg_installed

        # Check FFmpeg is installed
        if not check_ffmpeg_installed():
            video_job.mark_failed("FFmpeg is not installed on the server")
            db.session.commit()
            return {"status": "error", "message": "FFmpeg not installed"}

        # Process the video
        processor = VideoRecipeProcessor()

        # Update progress through the stages
        video_job.update_progress(
            VideoProcessingStatus.EXTRACTING_AUDIO,
            "Extracting audio track...",
            15
        )
        db.session.commit()

        # Run the full processing pipeline
        result = processor.process_video(
            video_path=video_job.video_path,
            translate_to_english=video_job.translate_to_english
        )

        if not result.success:
            video_job.mark_failed(result.error_message or "Video processing failed")
            db.session.commit()
            logger.error(f"[Task {self.request.id}] Video processing failed: {result.error_message}")
            return {"status": "error", "message": result.error_message}

        # Store intermediate results
        video_job.transcript = result.transcript
        if result.frame_analyses:
            video_job.frame_analysis = json.dumps(result.frame_analyses)
        if result.video_duration_seconds:
            video_job.video_duration_seconds = result.video_duration_seconds

        video_job.update_progress(
            VideoProcessingStatus.PARSING_RECIPE,
            "Creating recipe from extracted content...",
            85
        )
        db.session.commit()

        # Create the Recipe from parsed data
        parsed_recipe = result.parsed_recipe
        if not parsed_recipe:
            video_job.mark_failed("Could not parse recipe from video content")
            db.session.commit()
            return {"status": "error", "message": "Recipe parsing failed"}

        # Create Recipe object
        recipe = Recipe(
            title=parsed_recipe.get("title", "Recipe from Video"),
            description=parsed_recipe.get("description"),
            cookbook_id=video_job.cookbook_id,
            user_id=video_job.user_id,
            uploaded_by_id=video_job.user_id,
            prep_time=parsed_recipe.get("prep_time"),
            cook_time=parsed_recipe.get("cook_time"),
            servings=parsed_recipe.get("servings"),
            difficulty=parsed_recipe.get("difficulty"),
            course_type=parsed_recipe.get("course_type"),
            source="Video Import",
            is_original_recipe=video_job.is_original_recipe,
            # Translation fields
            source_language=parsed_recipe.get("source_language"),
            source_language_name=parsed_recipe.get("source_language_name"),
            is_translated=parsed_recipe.get("is_translated", False),
            original_title=parsed_recipe.get("original_title"),
            original_description=parsed_recipe.get("original_description"),
        )

        db.session.add(recipe)
        db.session.flush()  # Get the recipe ID

        # Add ingredients
        ingredients_list = parsed_recipe.get("ingredients", [])
        for i, ing_text in enumerate(ingredients_list):
            if not ing_text or not isinstance(ing_text, str):
                continue

            # Parse ingredient text (simple extraction)
            ing_name = ing_text.strip()

            # Find or create ingredient
            ingredient = Ingredient.query.filter(
                Ingredient.name.ilike(ing_name[:200])
            ).first()

            if not ingredient:
                ingredient = Ingredient(name=ing_name[:200])
                db.session.add(ingredient)
                db.session.flush()

            # Link to recipe
            db.session.execute(
                recipe_ingredients.insert().values(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    order=i
                )
            )

        # Add instructions
        instructions_list = parsed_recipe.get("instructions", [])
        for i, inst_text in enumerate(instructions_list):
            if not inst_text or not isinstance(inst_text, str):
                continue

            instruction = Instruction(
                recipe_id=recipe.id,
                step_number=i + 1,
                text=inst_text.strip()
            )
            db.session.add(instruction)

        # Add tags
        tags_list = parsed_recipe.get("tags", [])
        for tag_name in tags_list:
            if not tag_name or not isinstance(tag_name, str):
                continue

            tag = Tag(
                recipe_id=recipe.id,
                name=tag_name.strip()[:100]
            )
            db.session.add(tag)

        # Update video job with completion
        video_job.recipe_id = recipe.id
        video_job.update_progress(
            VideoProcessingStatus.COMPLETED,
            "Recipe extracted successfully!",
            100
        )
        db.session.commit()

        # Clean up video file
        try:
            if os.path.exists(video_job.video_path):
                os.remove(video_job.video_path)
                logger.info(f"Cleaned up video file: {video_job.video_path}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up video file: {cleanup_error}")

        logger.info(
            f"[Task {self.request.id}] Completed video recipe task for job {video_job_id}, "
            f"created recipe {recipe.id}: {recipe.title}"
        )

        return {
            "status": "success",
            "video_job_id": video_job_id,
            "recipe_id": recipe.id
        }

    except Exception as e:
        logger.error(
            f"[Task {self.request.id}] Failed video recipe task for job {video_job_id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )

        # Update job status to failed
        try:
            video_job = db.session.get(VideoProcessingJob, video_job_id)
            if video_job:
                video_job.mark_failed(f"Processing error: {str(e)[:450]}")
                db.session.commit()
        except Exception as db_error:
            logger.error(f"[Task {self.request.id}] Failed to update video job status: {db_error}")

        # Retry the task if retries remain
        raise self.retry(exc=e)
