"""
Video recipe processor service.

Extracts recipes from cooking videos using:
1. FFmpeg for audio/frame extraction
2. OpenAI Whisper for audio transcription
3. Claude Vision for frame analysis
4. Claude for recipe structuring
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
from pathlib import Path
from typing import Dict, List, Optional

import anthropic
from flask import current_app
from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class VideoProcessingResult:
    """Result of video processing."""
    success: bool
    transcript: Optional[str] = None
    frame_analyses: Optional[List[Dict]] = None
    parsed_recipe: Optional[Dict] = None
    error_message: Optional[str] = None
    video_duration_seconds: Optional[float] = None


class VideoRecipeProcessor:
    """Process cooking videos to extract structured recipes."""

    # Supported video formats
    SUPPORTED_FORMATS = {'video/mp4', 'video/quicktime', 'video/webm', 'video/x-msvideo'}
    SUPPORTED_EXTENSIONS = {'.mp4', '.mov', '.webm', '.avi'}

    # Processing limits
    MAX_VIDEO_SIZE_MB = 100
    MAX_DURATION_SECONDS = 180  # 3 minutes
    FRAME_COUNT = 6  # Number of frames to extract for analysis

    def __init__(self):
        """Initialize the video processor with API clients."""
        self.anthropic_client = anthropic.Anthropic(
            api_key=current_app.config.get("ANTHROPIC_API_KEY")
        )

        # OpenAI client for Whisper
        openai_api_key = current_app.config.get("OPENAI_API_KEY")
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
        else:
            self.openai_client = None
            logger.warning("OPENAI_API_KEY not configured - video transcription will not work")

    def validate_video(self, video_path: str, content_type: str) -> tuple[bool, str]:
        """
        Validate a video file for processing.

        Returns:
            tuple: (is_valid, error_message)
        """
        path = Path(video_path)

        # Check file exists
        if not path.exists():
            return False, "Video file not found"

        # Check file extension
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return False, f"Unsupported video format. Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"

        # Check content type
        if content_type and content_type not in self.SUPPORTED_FORMATS:
            return False, f"Unsupported content type: {content_type}"

        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.MAX_VIDEO_SIZE_MB:
            return False, f"Video too large ({file_size_mb:.1f}MB). Maximum: {self.MAX_VIDEO_SIZE_MB}MB"

        # Check duration using FFprobe
        try:
            duration = self._get_video_duration(video_path)
            if duration and duration > self.MAX_DURATION_SECONDS:
                return False, f"Video too long ({duration:.0f}s). Maximum: {self.MAX_DURATION_SECONDS}s"
        except Exception as e:
            logger.warning(f"Could not determine video duration: {e}")
            # Continue anyway - will fail later if truly invalid

        return True, ""

    def _get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration in seconds using FFprobe."""
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'quiet',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
            logger.error(f"FFprobe error getting duration: {e}")
        return None

    def process_video(
        self,
        video_path: str,
        translate_to_english: bool = False
    ) -> VideoProcessingResult:
        """
        Process a video file to extract a recipe.

        Args:
            video_path: Path to the video file
            translate_to_english: Whether to translate non-English content

        Returns:
            VideoProcessingResult with extracted recipe data
        """
        temp_dir = None

        try:
            # Create temp directory for processing artifacts
            temp_dir = tempfile.mkdtemp(prefix='video_recipe_')
            logger.info(f"Processing video: {video_path} in temp dir: {temp_dir}")

            # Get video duration
            video_duration = self._get_video_duration(video_path)

            # Step 1: Extract audio
            logger.info("Step 1: Extracting audio from video...")
            audio_path = os.path.join(temp_dir, 'audio.mp3')
            audio_success = self._extract_audio(video_path, audio_path)

            if not audio_success:
                logger.warning("Audio extraction failed - video may have no audio track")

            # Step 2: Transcribe audio (if available)
            transcript = None
            if audio_success and os.path.exists(audio_path):
                logger.info("Step 2: Transcribing audio with Whisper...")
                transcript = self._transcribe_audio(audio_path)
                if transcript:
                    logger.info(f"Transcription complete: {len(transcript)} characters")
                else:
                    logger.warning("Transcription returned no text")
            else:
                logger.info("Step 2: Skipping transcription (no audio)")

            # Step 3: Extract frames
            logger.info("Step 3: Extracting frames from video...")
            frames_dir = os.path.join(temp_dir, 'frames')
            os.makedirs(frames_dir, exist_ok=True)
            frame_paths = self._extract_frames(video_path, frames_dir, self.FRAME_COUNT)
            logger.info(f"Extracted {len(frame_paths)} frames")

            # Step 4: Analyze frames with Claude Vision
            frame_analyses = []
            if frame_paths:
                logger.info("Step 4: Analyzing frames with Claude Vision...")
                frame_analyses = self._analyze_frames(frame_paths)
                logger.info(f"Frame analysis complete: {len(frame_analyses)} analyses")

            # Step 5: Parse recipe from transcript + visual context
            logger.info("Step 5: Parsing recipe from transcript and visual context...")
            parsed_recipe = self._parse_recipe(
                transcript=transcript,
                frame_analyses=frame_analyses,
                translate_to_english=translate_to_english
            )

            if not parsed_recipe:
                return VideoProcessingResult(
                    success=False,
                    error_message="Could not extract recipe from video content",
                    video_duration_seconds=video_duration
                )

            logger.info(f"Recipe parsing complete: {parsed_recipe.get('title', 'Untitled')}")

            return VideoProcessingResult(
                success=True,
                transcript=transcript,
                frame_analyses=frame_analyses,
                parsed_recipe=parsed_recipe,
                video_duration_seconds=video_duration
            )

        except Exception as e:
            error_msg = f"Video processing failed: {str(e)}"
            logger.error(f"{error_msg}\nTraceback: {traceback.format_exc()}")
            return VideoProcessingResult(
                success=False,
                error_message=error_msg
            )
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory: {e}")

    def _extract_audio(self, video_path: str, output_path: str) -> bool:
        """
        Extract audio track from video using FFmpeg.

        Args:
            video_path: Path to input video
            output_path: Path for output audio file (MP3)

        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                [
                    'ffmpeg',
                    '-i', video_path,
                    '-vn',  # No video
                    '-acodec', 'libmp3lame',
                    '-ar', '16000',  # 16kHz sample rate (good for speech)
                    '-ac', '1',  # Mono
                    '-b:a', '64k',  # 64kbps bitrate
                    '-y',  # Overwrite output
                    output_path
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg audio extraction failed: {result.stderr}")
                return False

            # Verify output file exists and has content
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True

            logger.warning("Audio extraction produced empty file")
            return False

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg audio extraction timed out")
            return False
        except FileNotFoundError:
            logger.error("FFmpeg not found - please install FFmpeg")
            return False
        except Exception as e:
            logger.error(f"Audio extraction error: {e}\nTraceback: {traceback.format_exc()}")
            return False

    def _extract_frames(
        self,
        video_path: str,
        output_dir: str,
        count: int = 6
    ) -> List[str]:
        """
        Extract evenly-spaced frames from video using FFmpeg.

        Args:
            video_path: Path to input video
            output_dir: Directory for output frames
            count: Number of frames to extract

        Returns:
            List of paths to extracted frame images
        """
        try:
            # Get video duration first
            duration = self._get_video_duration(video_path)
            if not duration or duration <= 0:
                logger.warning("Could not determine video duration, using fallback method")
                # Fallback: extract frames at fixed intervals
                duration = 60  # Assume 60 seconds if unknown

            # Calculate frame extraction points (evenly spaced, excluding very start/end)
            interval = duration / (count + 1)
            frame_paths = []

            for i in range(1, count + 1):
                timestamp = interval * i
                output_path = os.path.join(output_dir, f'frame_{i:02d}.jpg')

                result = subprocess.run(
                    [
                        'ffmpeg',
                        '-ss', str(timestamp),
                        '-i', video_path,
                        '-vframes', '1',
                        '-q:v', '2',  # High quality JPEG
                        '-y',
                        output_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0 and os.path.exists(output_path):
                    frame_paths.append(output_path)
                else:
                    logger.warning(f"Failed to extract frame at {timestamp}s")

            return frame_paths

        except Exception as e:
            logger.error(f"Frame extraction error: {e}\nTraceback: {traceback.format_exc()}")
            return []

    def _transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio using OpenAI Whisper API.

        Args:
            audio_path: Path to audio file (MP3)

        Returns:
            Transcribed text, or None if failed
        """
        if not self.openai_client:
            logger.error("OpenAI client not configured - cannot transcribe audio")
            return None

        try:
            with open(audio_path, 'rb') as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )

            # Response is the transcribed text directly
            transcript = response.strip() if isinstance(response, str) else str(response).strip()

            if not transcript:
                logger.warning("Whisper returned empty transcription")
                return None

            return transcript

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}\nTraceback: {traceback.format_exc()}")
            return None

    def _analyze_frames(self, frame_paths: List[str]) -> List[Dict]:
        """
        Analyze video frames using Claude Vision to identify recipe elements.

        Args:
            frame_paths: List of paths to frame images

        Returns:
            List of analysis results for each frame
        """
        analyses = []

        for i, frame_path in enumerate(frame_paths):
            try:
                # Read and encode image
                with open(frame_path, 'rb') as f:
                    image_data = base64.standard_b64encode(f.read()).decode('utf-8')

                # Analyze with Claude Vision
                response = self.anthropic_client.messages.create(
                    model=current_app.config.get("ANTHROPIC_VISION_MODEL", "claude-sonnet-4-5-20250929"),
                    max_tokens=500,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_data
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": """Analyze this cooking video frame. Identify and describe:
1. Any visible ingredients (names, approximate quantities if visible)
2. Cooking techniques being demonstrated
3. Kitchen equipment being used
4. Any visible text (recipe cards, measurements, titles)
5. Stage of cooking process (prep, cooking, plating, etc.)

Be concise but thorough. Focus on recipe-relevant details."""
                                }
                            ]
                        }
                    ]
                )

                analysis = {
                    "frame_number": i + 1,
                    "analysis": response.content[0].text
                }
                analyses.append(analysis)

            except Exception as e:
                logger.error(f"Frame {i+1} analysis error: {e}")
                analyses.append({
                    "frame_number": i + 1,
                    "analysis": f"Analysis failed: {str(e)}"
                })

        return analyses

    def _parse_recipe(
        self,
        transcript: Optional[str],
        frame_analyses: List[Dict],
        translate_to_english: bool = False
    ) -> Optional[Dict]:
        """
        Parse a structured recipe from transcript and visual analysis.

        Args:
            transcript: Audio transcription from video
            frame_analyses: Visual analysis of video frames
            translate_to_english: Whether to translate non-English content

        Returns:
            Parsed recipe dict, or None if parsing failed
        """
        # Build context from available sources
        context_parts = []

        if transcript:
            context_parts.append(f"AUDIO TRANSCRIPTION:\n{transcript}")

        if frame_analyses:
            frame_text = "\n".join([
                f"Frame {a['frame_number']}: {a['analysis']}"
                for a in frame_analyses
            ])
            context_parts.append(f"VISUAL ANALYSIS:\n{frame_text}")

        if not context_parts:
            logger.error("No content available for recipe parsing")
            return None

        combined_context = "\n\n---\n\n".join(context_parts)

        # Build translation instructions if needed
        translation_instruction = ""
        if translate_to_english:
            translation_instruction = """
TRANSLATION REQUIREMENT:
If the recipe content is not in English, translate ALL content to English.
Preserve original text in the "original_*" fields.
"""

        prompt = f"""You are extracting a recipe from a cooking video. Use the following information:

{combined_context}

{translation_instruction}

Based on this cooking video content, extract a structured recipe in JSON format.

IMPORTANT GUIDELINES:
1. Infer ingredients from both spoken content AND what's visible in frames
2. Piece together cooking instructions from the narration and visual demonstrations
3. Estimate quantities if mentioned verbally or visible in the video
4. If the recipe title isn't explicitly stated, create a descriptive title based on the dish
5. Be thorough - cooking videos often show more than is narrated

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
            response = self.anthropic_client.messages.create(
                model=current_app.config.get("ANTHROPIC_TEXT_MODEL", "claude-sonnet-4-20250514"),
                max_tokens=3000,
                temperature=0.1,
                system="You are an expert at extracting recipes from cooking video content. Be thorough and accurate.",
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                logger.error(f"No JSON found in response: {content[:500]}")
                return None

            parsed = json.loads(json_match.group())

            # Validate required fields
            if not parsed.get('title'):
                logger.warning("Parsed recipe missing title")
                parsed['title'] = "Untitled Recipe from Video"

            if not parsed.get('ingredients'):
                logger.warning("Parsed recipe missing ingredients")
                parsed['ingredients'] = []

            if not parsed.get('instructions'):
                logger.warning("Parsed recipe missing instructions")
                parsed['instructions'] = []

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return None
        except Exception as e:
            logger.error(f"Recipe parsing error: {e}\nTraceback: {traceback.format_exc()}")
            return None


def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and accessible."""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
