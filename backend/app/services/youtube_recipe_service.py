"""
YouTube recipe import service.

Extracts recipes from YouTube cooking videos using a two-tier approach:
1. Tier 1 (fast): Extract captions/subtitles when available
2. Tier 2 (fallback): Download audio + Whisper transcription

Uses yt-dlp for YouTube interaction, Claude for recipe parsing.
"""

import base64
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import anthropic
import redis
import requests
from flask import current_app

logger = logging.getLogger(__name__)


class YouTubeValidationError(Exception):
    """Raised when YouTube URL validation fails."""

    pass


class YouTubeDownloadError(Exception):
    """Raised when downloading from YouTube fails."""

    pass


class YouTubeCaptionError(Exception):
    """Raised when caption extraction fails."""

    pass


@dataclass
class YouTubeProcessingResult:
    """Result of YouTube video processing."""

    success: bool
    extraction_method: Optional[str] = None  # "captions" or "audio_fallback"
    transcript: Optional[str] = None
    parsed_recipe: Optional[Dict] = None
    error_message: Optional[str] = None
    video_title: Optional[str] = None
    video_duration_seconds: Optional[float] = None


# Regex patterns for YouTube URL parsing
YOUTUBE_URL_PATTERNS = [
    # Standard: youtube.com/watch?v=VIDEO_ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})"),
    # Short: youtu.be/VIDEO_ID
    re.compile(r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})"),
    # Embed: youtube.com/embed/VIDEO_ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    # Shorts: youtube.com/shorts/VIDEO_ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})"),
    # Mobile: m.youtube.com/watch?v=VIDEO_ID
    re.compile(r"(?:https?://)?m\.youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})"),
]

# Patterns that indicate a non-video URL (playlists, channels, etc.)
YOUTUBE_REJECT_PATTERNS = [
    re.compile(r"youtube\.com/playlist\?"),
    re.compile(r"youtube\.com/channel/"),
    re.compile(r"youtube\.com/c/"),
    re.compile(r"youtube\.com/@"),
    re.compile(r"youtube\.com/user/"),
]

# Max video duration: 20 minutes
MAX_DURATION_SECONDS = 1200

# Cache TTL: 24 hours
CACHE_TTL = 86400


class YouTubeRecipeService:
    """Service for extracting recipes from YouTube cooking videos."""

    def __init__(self):
        """Initialize with API clients."""
        self.anthropic_client = anthropic.Anthropic(
            api_key=current_app.config.get("ANTHROPIC_API_KEY")
        )

        openai_api_key = current_app.config.get("OPENAI_API_KEY")
        if openai_api_key:
            from openai import OpenAI

            self.openai_client = OpenAI(api_key=openai_api_key)
        else:
            self.openai_client = None
            logger.warning(
                "OPENAI_API_KEY not configured — audio fallback will not work"
            )

        # Log yt-dlp version for debugging
        self._log_ytdlp_version()

        self.redis_client = self._init_redis()

    def _init_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis connection for caching."""
        try:
            redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception as e:
            logger.warning(f"Redis connection failed, caching disabled: {e}")
            return None

    def _log_ytdlp_version(self):
        """Log yt-dlp version for debugging."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info(f"yt-dlp version: {result.stdout.strip()}")
            else:
                logger.warning(f"Could not get yt-dlp version: {result.stderr}")
        except Exception as e:
            logger.warning(f"Error checking yt-dlp version: {e}")

    # ── URL Validation ──────────────────────────────────────────────

    @staticmethod
    def validate_and_extract_video_id(url: str) -> str:
        """
        Validate a YouTube URL and extract the video ID.

        Args:
            url: The URL to validate

        Returns:
            The 11-character YouTube video ID

        Raises:
            YouTubeValidationError: If URL is invalid or not a YouTube video
        """
        if not url or not isinstance(url, str):
            raise YouTubeValidationError("URL is required")

        url = url.strip()

        # Reject playlist/channel/user URLs
        for pattern in YOUTUBE_REJECT_PATTERNS:
            if pattern.search(url):
                if "playlist" in url.lower():
                    raise YouTubeValidationError(
                        "Please provide a single video URL, not a playlist"
                    )
                raise YouTubeValidationError("Not a valid YouTube video URL")

        # Try to extract video ID
        for pattern in YOUTUBE_URL_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1)

        raise YouTubeValidationError(
            "Not a valid YouTube video URL. Please provide a URL like "
            "https://www.youtube.com/watch?v=... or https://youtu.be/..."
        )

    # ── Metadata ────────────────────────────────────────────────────

    def _fetch_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """
        Fetch video metadata using yt-dlp --dump-json.

        Returns:
            Dict with title, duration, thumbnails, subtitles info, etc.

        Raises:
            YouTubeDownloadError: If metadata fetch fails
        """
        url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--dump-json",
                    "--no-download",
                    "--no-playlist",
                    # Enable Node.js runtime and download challenge solver from GitHub
                    "--js-runtimes", "node",
                    "--remote-components", "ejs:github",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                logger.warning(f"yt-dlp metadata fetch failed for {video_id}: {stderr[:500]}")

                # Check for specific error types
                stderr_lower = stderr.lower()
                if "private video" in stderr_lower:
                    raise YouTubeDownloadError("This video is private")
                if "sign in" in stderr_lower and "confirm your age" in stderr_lower:
                    raise YouTubeDownloadError("This video is age-restricted and requires sign-in")
                if "sign in" in stderr_lower:
                    raise YouTubeDownloadError("This video requires sign-in (may be members-only or region-restricted)")
                if "video unavailable" in stderr_lower or "is unavailable" in stderr_lower:
                    raise YouTubeDownloadError("This video is unavailable (may be deleted or region-restricted)")
                if "age" in stderr_lower and "restrict" in stderr_lower:
                    raise YouTubeDownloadError("This video is age-restricted")

                # Generic error with details
                raise YouTubeDownloadError(
                    f"Failed to fetch video: {stderr[:200]}"
                )

            metadata = json.loads(result.stdout)

            # Validate: not a live stream
            if metadata.get("is_live"):
                raise YouTubeValidationError("Live streams are not supported")

            # Validate: duration
            duration = metadata.get("duration", 0)
            if duration and duration > MAX_DURATION_SECONDS:
                raise YouTubeValidationError(
                    f"Video is too long ({duration // 60}m {duration % 60}s). "
                    f"Maximum is {MAX_DURATION_SECONDS // 60} minutes."
                )

            return metadata

        except (YouTubeDownloadError, YouTubeValidationError):
            raise
        except subprocess.TimeoutExpired:
            raise YouTubeDownloadError(
                "Timed out fetching video metadata. Please try again later."
            )
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse yt-dlp JSON output: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            raise YouTubeDownloadError("Failed to parse video metadata")
        except FileNotFoundError:
            logger.error("yt-dlp not found on system PATH")
            raise YouTubeDownloadError("yt-dlp is not installed on the server")
        except Exception as e:
            logger.error(
                f"Unexpected error fetching metadata for {video_id}: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            raise YouTubeDownloadError(f"Failed to fetch video info: {str(e)}")

    # ── Caption Extraction ──────────────────────────────────────────

    def _determine_caption_source(
        self, metadata: Dict[str, Any]
    ) -> Optional[Tuple[bool, str]]:
        """
        Determine the best caption source from video metadata.

        Args:
            metadata: yt-dlp metadata dict

        Returns:
            Tuple of (is_manual, language_code) or None if no captions
        """
        # Prefer manual (human-written) captions
        subtitles = metadata.get("subtitles", {})
        if subtitles:
            # Prefer English
            for lang in ["en", "en-US", "en-GB"]:
                if lang in subtitles:
                    return (True, lang)
            # Fall back to first available manual subtitle
            first_lang = next(iter(subtitles))
            return (True, first_lang)

        # Fall back to auto-generated captions
        auto_captions = metadata.get("automatic_captions", {})
        if auto_captions:
            for lang in ["en", "en-US", "en-GB"]:
                if lang in auto_captions:
                    return (False, lang)
            # Fall back to first available auto caption
            first_lang = next(iter(auto_captions))
            return (False, first_lang)

        return None

    def _extract_captions(
        self,
        video_id: str,
        temp_dir: str,
        use_auto: bool = False,
        lang_code: Optional[str] = None,
    ) -> Optional[str]:
        """
        Extract captions/subtitles using yt-dlp.

        Args:
            video_id: YouTube video ID
            temp_dir: Temp directory for subtitle files
            use_auto: Whether to use auto-generated captions
            lang_code: Specific language code from metadata (e.g. 'en-US-cvfXDfbeED0')

        Returns:
            Plain text transcript, or None if extraction fails
        """
        url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            sub_args = ["--write-auto-sub"] if use_auto else ["--write-sub"]

            # Build language list: include the exact key from metadata + common English variants
            lang_list = "en.*,en,en-US,en-GB"
            if lang_code and lang_code not in ("en", "en-US", "en-GB"):
                lang_list = f"{lang_code},{lang_list}"

            result = subprocess.run(
                [
                    "yt-dlp",
                    *sub_args,
                    "--sub-lang",
                    lang_list,
                    "--sub-format",
                    "vtt/srt/best",
                    "--skip-download",
                    "--no-playlist",
                    # Enable Node.js runtime and download challenge solver from GitHub
                    "--js-runtimes", "node",
                    "--remote-components", "ejs:github",
                    "-o",
                    os.path.join(temp_dir, "subs"),
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.warning(
                    f"yt-dlp caption extraction failed: {result.stderr[:300]}"
                )
                return None

            # Find the downloaded subtitle file
            sub_files = [
                f
                for f in os.listdir(temp_dir)
                if f.startswith("subs") and (f.endswith(".vtt") or f.endswith(".srt"))
            ]

            if not sub_files:
                logger.info("No subtitle files were downloaded")
                return None

            # Parse the first subtitle file into plain text
            sub_path = os.path.join(temp_dir, sub_files[0])
            return self._parse_subtitle_file(sub_path)

        except subprocess.TimeoutExpired:
            logger.warning("Caption extraction timed out")
            return None
        except Exception as e:
            logger.error(
                f"Caption extraction error: {e}\nTraceback: {traceback.format_exc()}"
            )
            return None

    @staticmethod
    def _parse_subtitle_file(filepath: str) -> Optional[str]:
        """
        Parse a VTT/SRT subtitle file into clean plain text.

        Removes timestamps, duplicate lines (common in auto-captions),
        and VTT headers.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Remove VTT header (WEBVTT + optional metadata lines + blank line)
            content = re.sub(
                r"^WEBVTT[^\n]*\n(?:.*?\n)*?\n", "", content, flags=re.DOTALL
            )

            # Remove SRT sequence numbers
            content = re.sub(r"^\d+\s*$", "", content, flags=re.MULTILINE)

            # Remove timestamps (VTT and SRT formats)
            content = re.sub(
                r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}.*",
                "",
                content,
            )

            # Remove VTT position/alignment tags
            content = re.sub(r"<[^>]+>", "", content)

            # Split into lines and deduplicate consecutive lines
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            deduped = []
            for line in lines:
                if not deduped or line != deduped[-1]:
                    deduped.append(line)

            text = " ".join(deduped)

            if not text.strip():
                return None

            return text.strip()

        except Exception as e:
            logger.error(
                f"Subtitle parsing error: {e}\nTraceback: {traceback.format_exc()}"
            )
            return None

    # ── Audio Fallback ──────────────────────────────────────────────

    def _download_audio(self, video_id: str, temp_dir: str) -> Optional[str]:
        """
        Download audio from YouTube using yt-dlp.

        Args:
            video_id: YouTube video ID
            temp_dir: Temp directory to save audio

        Returns:
            Path to downloaded MP3, or None if failed
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        output_template = os.path.join(temp_dir, "audio.%(ext)s")

        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-x",
                    "--audio-format",
                    "mp3",
                    "--audio-quality",
                    "5",
                    "--no-playlist",
                    # Enable Node.js runtime and download challenge solver from GitHub
                    "--js-runtimes", "node",
                    "--remote-components", "ejs:github",
                    "-o",
                    output_template,
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes for longer videos
            )

            if result.returncode != 0:
                logger.error(f"yt-dlp audio download failed: {result.stderr[:300]}")
                raise YouTubeDownloadError(
                    f"Failed to download audio: {result.stderr[:200]}"
                )

            # Find the output file
            audio_path = os.path.join(temp_dir, "audio.mp3")
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                return audio_path

            # yt-dlp might have used a different extension before conversion
            for f in os.listdir(temp_dir):
                if f.startswith("audio") and f.endswith(".mp3"):
                    return os.path.join(temp_dir, f)

            logger.error("Audio file not found after download")
            raise YouTubeDownloadError("Audio download produced no output file")

        except YouTubeDownloadError:
            raise
        except subprocess.TimeoutExpired:
            raise YouTubeDownloadError(
                "Audio download timed out. The video may be too long."
            )
        except FileNotFoundError:
            raise YouTubeDownloadError("yt-dlp is not installed on the server")
        except Exception as e:
            logger.error(
                f"Audio download error: {e}\nTraceback: {traceback.format_exc()}"
            )
            raise YouTubeDownloadError(f"Audio download failed: {str(e)}")

    def _transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio using OpenAI Whisper API.

        Args:
            audio_path: Path to audio file (MP3)

        Returns:
            Transcribed text, or None if failed
        """
        if not self.openai_client:
            logger.error("OpenAI client not configured — cannot transcribe")
            return None

        try:
            with open(audio_path, "rb") as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                )

            transcript = (
                response.strip() if isinstance(response, str) else str(response).strip()
            )

            if not transcript:
                logger.warning("Whisper returned empty transcription")
                return None

            return transcript

        except Exception as e:
            logger.error(
                f"Whisper transcription error: {e}\nTraceback: {traceback.format_exc()}"
            )
            return None

    # ── Thumbnail ───────────────────────────────────────────────────

    def _download_thumbnail(self, thumbnail_url: str, temp_dir: str) -> Optional[str]:
        """
        Download video thumbnail for visual context.

        Args:
            thumbnail_url: URL of the thumbnail image
            temp_dir: Temp directory to save the image

        Returns:
            Path to downloaded image, or None on failure (graceful)
        """
        if not thumbnail_url:
            return None

        try:
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()

            thumb_path = os.path.join(temp_dir, "thumbnail.jpg")
            with open(thumb_path, "wb") as f:
                f.write(response.content)

            if os.path.getsize(thumb_path) > 0:
                return thumb_path

            return None

        except Exception as e:
            logger.warning(f"Thumbnail download failed (non-fatal): {e}")
            return None

    # ── Recipe Parsing ──────────────────────────────────────────────

    def _parse_youtube_recipe(
        self,
        transcript: str,
        thumbnail_path: Optional[str],
        video_title: str,
        translate_to_english: bool = False,
    ) -> Optional[Dict]:
        """
        Parse a structured recipe from transcript + optional thumbnail.

        Args:
            transcript: Video transcript text
            thumbnail_path: Path to thumbnail image (optional)
            video_title: Title of the YouTube video
            translate_to_english: Whether to translate non-English content

        Returns:
            Parsed recipe dict, or None if parsing failed
        """
        translation_instruction = ""
        if translate_to_english:
            translation_instruction = """
TRANSLATION REQUIREMENT:
If the recipe content is not in English, translate ALL content to English.
Preserve original text in the "original_*" fields.
"""

        prompt = f"""You are extracting a recipe from a YouTube cooking video.

VIDEO TITLE: {video_title}

TRANSCRIPT:
{transcript}

{translation_instruction}

Based on this cooking video content, extract a structured recipe in JSON format.

IMPORTANT GUIDELINES:
1. The video title often contains the recipe name
2. Infer ingredients from spoken content
3. Piece together cooking instructions from the narration
4. Estimate quantities if mentioned verbally
5. Be thorough — cooking videos often mention more than written recipes

Return a JSON object with these fields:
- title: recipe name (required)
- description: brief description of the dish
- ingredients: array of ingredient strings (e.g., "2 cups flour", "1 lb chicken breast")
- instructions: array of step-by-step cooking instructions
- prep_time: preparation time in minutes (if mentioned or can be estimated)
- cook_time: cooking time in minutes (if mentioned or can be estimated)
- servings: number of servings (if mentioned)
- difficulty: easy/medium/hard (infer from complexity)
- course_type: one of "Appetizer", "Soup", "Salad", "Main Course", "Side Dish", "Bread", "Dessert", "Beverage", "Sauce/Condiment", "Snack"
- tags: array of relevant tags (cuisine type, dietary info, etc.)
- source_language: ISO 639-1 code if not English (e.g., 'es', 'fr')
- source_language_name: language name if not English
- is_translated: true if translated from another language
- original_title: original language title if translated
- original_description: original description if translated
- parsing_confidence: high/medium/low (your confidence in the extraction)
- parsing_notes: any issues or assumptions made during extraction

If information is truly unavailable, use null. But try to infer reasonable values from context.

Return ONLY valid JSON, no markdown code blocks or extra text."""

        try:
            # Build message content
            content: List[Dict[str, Any]] = []

            # Add thumbnail if available
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    with open(thumbnail_path, "rb") as f:
                        raw = f.read()
                    image_data = base64.standard_b64encode(raw).decode("utf-8")

                    # Detect actual image format from magic bytes
                    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
                        media_type = "image/webp"
                    elif raw[:3] == b"\xff\xd8\xff":
                        media_type = "image/jpeg"
                    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
                        media_type = "image/png"
                    elif raw[:4] in (b"GIF8",):
                        media_type = "image/gif"
                    else:
                        media_type = "image/jpeg"

                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to encode thumbnail: {e}")

            content.append({"type": "text", "text": prompt})

            model = current_app.config.get(
                "ANTHROPIC_TEXT_MODEL", "claude-sonnet-4-20250514"
            )

            # Use vision model if we have a thumbnail
            if any(c.get("type") == "image" for c in content):
                model = current_app.config.get(
                    "ANTHROPIC_VISION_MODEL", "claude-sonnet-4-5-20250929"
                )

            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=3000,
                temperature=0.1,
                system="You are an expert at extracting recipes from cooking video content. Be thorough and accurate.",
                messages=[{"role": "user", "content": content}],
            )

            response_text = response.content[0].text

            # Extract JSON from response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if not json_match:
                logger.error(f"No JSON found in Claude response: {response_text[:500]}")
                return None

            parsed = json.loads(json_match.group())

            # Validate required fields
            if not parsed.get("title"):
                parsed["title"] = video_title or "Recipe from YouTube Video"

            if not parsed.get("ingredients"):
                parsed["ingredients"] = []

            if not parsed.get("instructions"):
                parsed["instructions"] = []

            return parsed

        except json.JSONDecodeError as e:
            logger.error(
                f"JSON parsing error in recipe extraction: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            raise YouTubeCaptionError(f"Failed to parse Claude response as JSON: {e}")
        except Exception as e:
            logger.error(
                f"Recipe parsing error: {e}\nTraceback: {traceback.format_exc()}"
            )
            raise YouTubeCaptionError(f"Recipe extraction failed: {e}")

    # ── Caching ─────────────────────────────────────────────────────

    @staticmethod
    def _generate_cache_key(video_id: str, translate: bool = False) -> str:
        """Generate Redis cache key for a YouTube video."""
        suffix = "_translated" if translate else ""
        return f"yt_recipe:{video_id}{suffix}"

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get cached recipe data."""
        if not self.redis_client:
            return None
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    def _set_in_cache(self, cache_key: str, data: Dict) -> None:
        """Cache recipe data with 24h TTL."""
        if not self.redis_client:
            return
        try:
            self.redis_client.setex(cache_key, CACHE_TTL, json.dumps(data))
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    # ── Main Orchestrator ───────────────────────────────────────────

    def process_youtube_url(
        self,
        video_id: str,
        youtube_url: str,
        translate_to_english: bool = False,
        progress_callback: Optional[Callable[[str, str, int], None]] = None,
    ) -> YouTubeProcessingResult:
        """
        Main orchestrator: process a YouTube URL into a recipe.

        Args:
            video_id: YouTube video ID
            youtube_url: Original YouTube URL
            translate_to_english: Whether to translate non-English content
            progress_callback: Callback(status, message, percentage) for progress updates

        Returns:
            YouTubeProcessingResult
        """
        temp_dir = None

        def update_progress(status: str, message: str, pct: int) -> None:
            if progress_callback:
                progress_callback(status, message, pct)

        try:
            temp_dir = tempfile.mkdtemp(prefix="youtube_recipe_")
            logger.info(f"Processing YouTube video {video_id} in {temp_dir}")

            # ── Check cache ──
            cache_key = self._generate_cache_key(video_id, translate_to_english)
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.info(f"Cache hit for YouTube video {video_id}")
                return YouTubeProcessingResult(
                    success=True,
                    extraction_method=cached.get("extraction_method", "captions"),
                    transcript=cached.get("transcript"),
                    parsed_recipe=cached.get("parsed_recipe"),
                    video_title=cached.get("video_title"),
                    video_duration_seconds=cached.get("video_duration_seconds"),
                )

            # ── Fetch metadata ──
            update_progress("fetching_metadata", "Fetching video info...", 10)
            metadata = self._fetch_video_metadata(video_id)

            video_title = metadata.get("title", "")
            video_duration = metadata.get("duration")

            # ── Try captions (Tier 1) ──
            update_progress("extracting_captions", "Looking for captions...", 30)
            caption_source = self._determine_caption_source(metadata)
            transcript = None
            extraction_method = None

            if caption_source:
                is_manual, lang_code = caption_source
                logger.info(
                    f"Found {'manual' if is_manual else 'auto'} captions in {lang_code}"
                )
                transcript = self._extract_captions(
                    video_id,
                    temp_dir,
                    use_auto=not is_manual,
                    lang_code=lang_code,
                )

            if transcript:
                extraction_method = "captions"
                logger.info(
                    f"Tier 1 (captions): Got {len(transcript)} chars of transcript"
                )
            else:
                # ── Tier 2: Audio fallback ──
                logger.info("No captions available, falling back to audio download")

                if not self.openai_client:
                    return YouTubeProcessingResult(
                        success=False,
                        error_message=(
                            "No captions available and audio transcription "
                            "not configured"
                        ),
                        video_title=video_title,
                        video_duration_seconds=video_duration,
                    )

                update_progress("downloading_audio", "Downloading audio...", 40)
                audio_path = self._download_audio(video_id, temp_dir)

                update_progress("transcribing", "Transcribing audio...", 60)
                transcript = self._transcribe_audio(audio_path)

                if not transcript:
                    return YouTubeProcessingResult(
                        success=False,
                        error_message="Failed to transcribe video audio",
                        video_title=video_title,
                        video_duration_seconds=video_duration,
                    )

                extraction_method = "audio_fallback"
                logger.info(
                    f"Tier 2 (audio): Got {len(transcript)} chars of transcript"
                )

            # ── Download thumbnail ──
            thumbnail_url = metadata.get("thumbnail")
            thumbnail_path = self._download_thumbnail(thumbnail_url, temp_dir)

            # ── Parse recipe ──
            update_progress(
                "parsing_recipe", "Extracting recipe from transcript...", 70
            )
            try:
                parsed_recipe = self._parse_youtube_recipe(
                    transcript=transcript,
                    thumbnail_path=thumbnail_path,
                    video_title=video_title,
                    translate_to_english=translate_to_english,
                )
            except YouTubeCaptionError as e:
                return YouTubeProcessingResult(
                    success=False,
                    error_message=f"Recipe parsing failed: {e}",
                    extraction_method=extraction_method,
                    transcript=transcript,
                    video_title=video_title,
                    video_duration_seconds=video_duration,
                )

            if not parsed_recipe:
                return YouTubeProcessingResult(
                    success=False,
                    error_message="Could not extract a recipe from the video transcript",
                    extraction_method=extraction_method,
                    transcript=transcript,
                    video_title=video_title,
                    video_duration_seconds=video_duration,
                )

            # ── Cache the result ──
            cache_data = {
                "extraction_method": extraction_method,
                "transcript": transcript,
                "parsed_recipe": parsed_recipe,
                "video_title": video_title,
                "video_duration_seconds": video_duration,
            }
            self._set_in_cache(cache_key, cache_data)

            return YouTubeProcessingResult(
                success=True,
                extraction_method=extraction_method,
                transcript=transcript,
                parsed_recipe=parsed_recipe,
                video_title=video_title,
                video_duration_seconds=video_duration,
            )

        except (YouTubeValidationError, YouTubeDownloadError) as e:
            logger.warning(f"YouTube processing error for {video_id}: {e}")
            return YouTubeProcessingResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(
                f"Unexpected error processing YouTube video {video_id}: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            return YouTubeProcessingResult(
                success=False,
                error_message=f"Processing failed: {str(e)}",
            )
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp dir: {e}")
