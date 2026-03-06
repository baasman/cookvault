"""
Celery tasks for recipe image and video processing.

These tasks wrap the existing processing functions to enable
asynchronous, queued execution for better memory management.
"""

import json
import logging
import os
import tempfile
import traceback
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
    logger.info(
        f"[Task {self.request.id}] Starting single recipe task for job {job_id}, user {user_id}"
    )

    try:
        job = db.session.get(ProcessingJob, job_id)
        if not job:
            logger.error(f"[Task {self.request.id}] ProcessingJob {job_id} not found")
            return {"status": "error", "message": "Job not found"}

        # Import the existing processing function (inside task to avoid circular imports)
        from app.api.recipes import _process_recipe_image

        # Process the image (this function already handles all the logic)
        _process_recipe_image(job_id, user_id)

        logger.info(
            f"[Task {self.request.id}] Completed single recipe task for job {job_id}"
        )
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
            logger.error(
                f"[Task {self.request.id}] Failed to update job status: {db_error}"
            )

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
    logger.info(
        f"[Task {self.request.id}] Starting multi-image task for job {multi_job_id}"
    )

    try:
        multi_job = db.session.get(MultiRecipeJob, multi_job_id)
        if not multi_job:
            logger.error(
                f"[Task {self.request.id}] MultiRecipeJob {multi_job_id} not found"
            )
            return {"status": "error", "message": "Multi-job not found"}

        # Import the existing processing function (inside task to avoid circular imports)
        from app.api.recipes import process_multi_image_job

        # Process all images (this function already handles all the logic)
        process_multi_image_job(multi_job_id)

        logger.info(
            f"[Task {self.request.id}] Completed multi-image task for job {multi_job_id}"
        )
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
            logger.error(
                f"[Task {self.request.id}] Failed to update multi-job status: {db_error}"
            )

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
    logger.info(
        f"[Task {self.request.id}] Starting video recipe task for job {video_job_id}"
    )

    try:
        # Get the video job
        video_job = db.session.get(VideoProcessingJob, video_job_id)
        if not video_job:
            logger.error(
                f"[Task {self.request.id}] VideoProcessingJob {video_job_id} not found"
            )
            return {"status": "error", "message": "Video job not found"}

        # Update status to processing
        video_job.update_progress(
            VideoProcessingStatus.EXTRACTING_AUDIO, "Extracting audio from video...", 10
        )
        db.session.commit()

        # Import the video processor (inside task to avoid circular imports)
        from app.services.video_processor import (
            VideoRecipeProcessor,
            check_ffmpeg_installed,
        )

        # Check FFmpeg is installed
        if not check_ffmpeg_installed():
            video_job.mark_failed("FFmpeg is not installed on the server")
            db.session.commit()
            return {"status": "error", "message": "FFmpeg not installed"}

        # Process the video
        processor = VideoRecipeProcessor()

        # Determine video source - download from Cloudinary if needed
        video_path = video_job.video_path
        temp_video_file = None

        if video_job.cloudinary_url and (
            not video_path or not os.path.exists(video_path)
        ):
            # Download video from Cloudinary to a temp file
            video_job.update_progress(
                VideoProcessingStatus.UPLOADING,
                "Downloading video for processing...",
                12,
            )
            db.session.commit()

            try:
                # Create temp file with correct extension
                original_ext = (
                    os.path.splitext(video_job.video_original_filename)[1] or ".mp4"
                )
                temp_video_file = tempfile.NamedTemporaryFile(
                    suffix=original_ext, delete=False, prefix="cookle_video_"
                )
                temp_video_file.close()
                video_path = temp_video_file.name

                # Download from Cloudinary
                logger.info(
                    f"Downloading video from Cloudinary: {video_job.cloudinary_url}"
                )
                response = requests.get(
                    video_job.cloudinary_url, stream=True, timeout=120
                )
                response.raise_for_status()

                with open(video_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(
                    f"Downloaded video to: {video_path} ({os.path.getsize(video_path)} bytes)"
                )

            except Exception as download_error:
                error_msg = (
                    f"Failed to download video from Cloudinary: {download_error}"
                )
                logger.error(f"{error_msg}\nTraceback: {traceback.format_exc()}")
                video_job.mark_failed(error_msg)
                db.session.commit()
                return {"status": "error", "message": error_msg}

        # Update progress through the stages
        video_job.update_progress(
            VideoProcessingStatus.EXTRACTING_AUDIO, "Extracting audio track...", 15
        )
        db.session.commit()

        # Run the full processing pipeline
        result = processor.process_video(
            video_path=video_path, translate_to_english=video_job.translate_to_english
        )

        if not result.success:
            video_job.mark_failed(result.error_message or "Video processing failed")
            db.session.commit()
            logger.error(
                f"[Task {self.request.id}] Video processing failed: {result.error_message}"
            )
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
            85,
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
                    recipe_id=recipe.id, ingredient_id=ingredient.id, order=i
                )
            )

        # Add instructions
        instructions_list = parsed_recipe.get("instructions", [])
        for i, inst_text in enumerate(instructions_list):
            if not inst_text or not isinstance(inst_text, str):
                continue

            instruction = Instruction(
                recipe_id=recipe.id, step_number=i + 1, text=inst_text.strip()
            )
            db.session.add(instruction)

        # Add tags
        tags_list = parsed_recipe.get("tags", [])
        for tag_name in tags_list:
            if not tag_name or not isinstance(tag_name, str):
                continue

            tag = Tag(recipe_id=recipe.id, name=tag_name.strip()[:100])
            db.session.add(tag)

        # Update video job with completion
        video_job.recipe_id = recipe.id
        video_job.update_progress(
            VideoProcessingStatus.COMPLETED, "Recipe extracted successfully!", 100
        )
        db.session.commit()

        # Clean up video files
        try:
            # Clean up temp downloaded file
            if temp_video_file and os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"Cleaned up temp video file: {video_path}")

            # Clean up original video path if it exists
            if video_job.video_path and os.path.exists(video_job.video_path):
                os.remove(video_job.video_path)
                logger.info(f"Cleaned up original video file: {video_job.video_path}")

            # Delete video from Cloudinary (we only needed it for processing)
            if video_job.cloudinary_public_id:
                try:
                    cloudinary.uploader.destroy(
                        video_job.cloudinary_public_id, resource_type="video"
                    )
                    logger.info(
                        f"Deleted video from Cloudinary: {video_job.cloudinary_public_id}"
                    )
                except Exception as cloudinary_error:
                    logger.warning(
                        f"Failed to delete video from Cloudinary: {cloudinary_error}"
                    )

        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up video file: {cleanup_error}")

        logger.info(
            f"[Task {self.request.id}] Completed video recipe task for job {video_job_id}, "
            f"created recipe {recipe.id}: {recipe.title}"
        )

        return {
            "status": "success",
            "video_job_id": video_job_id,
            "recipe_id": recipe.id,
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
            logger.error(
                f"[Task {self.request.id}] Failed to update video job status: {db_error}"
            )

        # Retry the task if retries remain
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=2, default_retry_delay=60)
def process_youtube_recipe_task(self, video_job_id: int):
    """
    Celery task to process a YouTube URL and extract a recipe.

    This task:
    1. Fetches video metadata via yt-dlp
    2. Extracts captions (Tier 1) or downloads audio + Whisper (Tier 2)
    3. Optionally downloads thumbnail for visual context
    4. Parses transcript into structured recipe via Claude
    5. Creates the Recipe in the database

    Args:
        self: Celery task instance (bound)
        video_job_id: ID of the VideoProcessingJob to process

    Returns:
        Dict with status and video_job_id
    """
    logger.info(
        f"[Task {self.request.id}] Starting YouTube recipe task for job {video_job_id}"
    )

    try:
        video_job = db.session.get(VideoProcessingJob, video_job_id)
        if not video_job:
            logger.error(
                f"[Task {self.request.id}] VideoProcessingJob {video_job_id} not found"
            )
            return {"status": "error", "message": "Video job not found"}

        if not video_job.youtube_video_id:
            video_job.mark_failed("No YouTube video ID set on job")
            db.session.commit()
            return {"status": "error", "message": "Missing YouTube video ID"}

        # Import inside task to avoid circular imports
        from app.services.youtube_recipe_service import YouTubeRecipeService

        service = YouTubeRecipeService()

        # Progress callback that updates the job in the DB
        def progress_callback(status: str, message: str, percentage: int):
            try:
                status_enum = VideoProcessingStatus(status)
                video_job.update_progress(status_enum, message, percentage)
                db.session.commit()
            except Exception as e:
                logger.warning(
                    f"[Task {self.request.id}] Failed to update progress: {e}"
                )

        # Run the processing pipeline
        result = service.process_youtube_url(
            video_id=video_job.youtube_video_id,
            youtube_url=video_job.youtube_url or "",
            translate_to_english=video_job.translate_to_english,
            progress_callback=progress_callback,
        )

        if not result.success:
            # Save transcript/method even on failure for debugging
            if result.transcript:
                video_job.transcript = result.transcript
            if result.extraction_method:
                video_job.extraction_method = result.extraction_method
            video_job.mark_failed(result.error_message or "YouTube processing failed")
            db.session.commit()
            logger.error(
                f"[Task {self.request.id}] YouTube processing failed: "
                f"{result.error_message}"
            )
            return {"status": "error", "message": result.error_message}

        # Store intermediate results
        video_job.transcript = result.transcript
        video_job.extraction_method = result.extraction_method
        if result.video_duration_seconds:
            video_job.video_duration_seconds = result.video_duration_seconds

        video_job.update_progress(
            VideoProcessingStatus.PARSING_RECIPE,
            "Creating recipe from extracted content...",
            85,
        )
        db.session.commit()

        # Create the Recipe from parsed data
        parsed_recipe = result.parsed_recipe
        if not parsed_recipe:
            video_job.mark_failed("Could not parse recipe from video content")
            db.session.commit()
            return {"status": "error", "message": "Recipe parsing failed"}

        # Build source string
        youtube_source = video_job.youtube_url or (
            f"https://www.youtube.com/watch?v={video_job.youtube_video_id}"
        )

        recipe = Recipe(
            title=parsed_recipe.get("title", "Recipe from YouTube"),
            description=parsed_recipe.get("description"),
            cookbook_id=video_job.cookbook_id,
            user_id=video_job.user_id,
            uploaded_by_id=video_job.user_id,
            prep_time=parsed_recipe.get("prep_time"),
            cook_time=parsed_recipe.get("cook_time"),
            servings=parsed_recipe.get("servings"),
            difficulty=parsed_recipe.get("difficulty"),
            course_type=parsed_recipe.get("course_type"),
            source=youtube_source,
            is_original_recipe=video_job.is_original_recipe,
            source_language=parsed_recipe.get("source_language"),
            source_language_name=parsed_recipe.get("source_language_name"),
            is_translated=parsed_recipe.get("is_translated", False),
            original_title=parsed_recipe.get("original_title"),
            original_description=parsed_recipe.get("original_description"),
        )

        db.session.add(recipe)
        db.session.flush()

        # Add ingredients
        for i, ing_text in enumerate(parsed_recipe.get("ingredients", [])):
            if not ing_text or not isinstance(ing_text, str):
                continue

            ing_name = ing_text.strip()
            ingredient = Ingredient.query.filter(
                Ingredient.name.ilike(ing_name[:200])
            ).first()

            if not ingredient:
                ingredient = Ingredient(name=ing_name[:200])
                db.session.add(ingredient)
                db.session.flush()

            db.session.execute(
                recipe_ingredients.insert().values(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    order=i,
                )
            )

        # Add instructions
        for i, inst_text in enumerate(parsed_recipe.get("instructions", [])):
            if not inst_text or not isinstance(inst_text, str):
                continue

            instruction = Instruction(
                recipe_id=recipe.id,
                step_number=i + 1,
                text=inst_text.strip(),
            )
            db.session.add(instruction)

        # Add tags
        for tag_name in parsed_recipe.get("tags", []):
            if not tag_name or not isinstance(tag_name, str):
                continue

            tag = Tag(
                recipe_id=recipe.id,
                name=tag_name.strip()[:100],
            )
            db.session.add(tag)

        # Complete the job
        video_job.recipe_id = recipe.id
        video_job.update_progress(
            VideoProcessingStatus.COMPLETED,
            "Recipe extracted successfully!",
            100,
        )
        db.session.commit()

        logger.info(
            f"[Task {self.request.id}] Completed YouTube recipe task for "
            f"job {video_job_id}, created recipe {recipe.id}: {recipe.title}"
        )

        return {
            "status": "success",
            "video_job_id": video_job_id,
            "recipe_id": recipe.id,
        }

    except Exception as e:
        logger.error(
            f"[Task {self.request.id}] Failed YouTube recipe task for "
            f"job {video_job_id}: {str(e)}\n"
            f"Traceback: {traceback.format_exc()}"
        )

        try:
            video_job = db.session.get(VideoProcessingJob, video_job_id)
            if video_job:
                video_job.mark_failed(f"Processing error: {str(e)[:450]}")
                db.session.commit()
        except Exception as db_error:
            logger.error(
                f"[Task {self.request.id}] Failed to update YouTube job status: "
                f"{db_error}"
            )

        raise self.retry(exc=e)
