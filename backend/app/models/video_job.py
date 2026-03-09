"""
Video processing job model for tracking video-to-recipe extraction jobs.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class VideoProcessingStatus(Enum):
    """Status states for video processing jobs."""

    PENDING = "pending"
    UPLOADING = "uploading"
    FETCHING_METADATA = "fetching_metadata"
    EXTRACTING_CAPTIONS = "extracting_captions"
    DOWNLOADING_AUDIO = "downloading_audio"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    EXTRACTING_FRAMES = "extracting_frames"
    ANALYZING_FRAMES = "analyzing_frames"
    PARSING_RECIPE = "parsing_recipe"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoProcessingJob(db.Model):
    """
    Tracks video-to-recipe processing jobs.

    Video processing involves multiple steps:
    1. Upload and store video temporarily
    2. Extract audio using FFmpeg
    3. Transcribe audio using OpenAI Whisper
    4. Extract key frames using FFmpeg
    5. Analyze frames using Claude Vision
    6. Parse transcript + visual context into structured recipe using Claude
    """

    __tablename__ = "video_processing_job"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"), nullable=False, index=True
    )

    # Video file information
    video_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    video_original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    video_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # Local path (may be None)
    video_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    video_duration_seconds: Mapped[Optional[float]] = mapped_column(db.Float)
    video_content_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # YouTube-specific fields (nullable — only set for YouTube imports)
    youtube_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    youtube_video_id: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )
    extraction_method: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # "captions", "audio_fallback", "file_upload"

    # Processing status
    status: Mapped[VideoProcessingStatus] = mapped_column(
        default=VideoProcessingStatus.PENDING
    )
    progress_message: Mapped[Optional[str]] = mapped_column(String(255))
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Processing results
    transcript: Mapped[Optional[str]] = mapped_column(Text)
    frame_analysis: Mapped[Optional[str]] = mapped_column(
        Text
    )  # JSON string of frame analyses

    # Result
    recipe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recipe.id"))
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Recipe source tracking
    is_original_recipe: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    translate_to_english: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Cookbook association (optional)
    cookbook_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cookbook.id"))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="video_jobs")
    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")
    cookbook: Mapped[Optional["Cookbook"]] = relationship("Cookbook")

    def update_progress(
        self, status: VideoProcessingStatus, message: str, percentage: int
    ) -> None:
        """Update the job's progress status."""
        self.status = status
        self.progress_message = message
        self.progress_percentage = percentage

        if status == VideoProcessingStatus.COMPLETED:
            self.completed_at = datetime.utcnow()
        elif self.started_at is None and status != VideoProcessingStatus.PENDING:
            self.started_at = datetime.utcnow()

    def mark_failed(self, error_message: str) -> None:
        """Mark the job as failed with an error message."""
        self.status = VideoProcessingStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "video_filename": self.video_filename,
            "video_original_filename": self.video_original_filename,
            "video_size_bytes": self.video_size_bytes,
            "video_duration_seconds": self.video_duration_seconds,
            "youtube_url": self.youtube_url,
            "youtube_video_id": self.youtube_video_id,
            "extraction_method": self.extraction_method,
            "status": self.status.value,
            "progress_message": self.progress_message,
            "progress_percentage": self.progress_percentage,
            "recipe_id": self.recipe_id,
            "error_message": self.error_message,
            "cookbook_id": self.cookbook_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }
