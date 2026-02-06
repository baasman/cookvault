"""
Celery tasks for recipe image processing.

These tasks wrap the existing processing functions to enable
asynchronous, queued execution for better memory management.
"""
import logging
import traceback

from app import db
from app.celery_app import celery
from app.models.recipe import ProcessingJob, ProcessingStatus, MultiRecipeJob

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
