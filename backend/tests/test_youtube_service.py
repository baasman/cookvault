"""
Tests for YouTubeRecipeService.

All external calls (subprocess, requests, API clients, Redis) are mocked.
"""

import json
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from app.services.youtube_recipe_service import (
    YouTubeDownloadError,
    YouTubeRecipeService,
    YouTubeValidationError,
)


# ═══════════════════════════════════════════════════════════════════
# URL Validation Tests
# ═══════════════════════════════════════════════════════════════════


class TestYouTubeUrlValidation:
    """Test YouTube URL validation and video ID extraction."""

    def test_standard_url(self):
        vid = YouTubeRecipeService.validate_and_extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_short_url(self):
        vid = YouTubeRecipeService.validate_and_extract_video_id(
            "https://youtu.be/dQw4w9WgXcQ"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_embed_url(self):
        vid = YouTubeRecipeService.validate_and_extract_video_id(
            "https://www.youtube.com/embed/dQw4w9WgXcQ"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_url_with_extra_params(self):
        vid = YouTubeRecipeService.validate_and_extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PL1234"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_mobile_url(self):
        vid = YouTubeRecipeService.validate_and_extract_video_id(
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        vid = YouTubeRecipeService.validate_and_extract_video_id(
            "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        )
        assert vid == "dQw4w9WgXcQ"

    def test_invalid_non_youtube_url(self):
        with pytest.raises(YouTubeValidationError, match="Not a valid YouTube"):
            YouTubeRecipeService.validate_and_extract_video_id(
                "https://www.vimeo.com/12345"
            )

    def test_no_video_id(self):
        with pytest.raises(YouTubeValidationError, match="Not a valid YouTube"):
            YouTubeRecipeService.validate_and_extract_video_id(
                "https://www.youtube.com/"
            )

    def test_playlist_url_rejected(self):
        with pytest.raises(YouTubeValidationError, match="playlist"):
            YouTubeRecipeService.validate_and_extract_video_id(
                "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
            )

    def test_channel_url_rejected(self):
        with pytest.raises(YouTubeValidationError, match="Not a valid YouTube"):
            YouTubeRecipeService.validate_and_extract_video_id(
                "https://www.youtube.com/@BonAppetit"
            )

    def test_empty_url(self):
        with pytest.raises(YouTubeValidationError, match="required"):
            YouTubeRecipeService.validate_and_extract_video_id("")

    def test_none_url(self):
        with pytest.raises(YouTubeValidationError, match="required"):
            YouTubeRecipeService.validate_and_extract_video_id(None)


# ═══════════════════════════════════════════════════════════════════
# Metadata Tests
# ═══════════════════════════════════════════════════════════════════


class TestFetchVideoMetadata:
    """Test yt-dlp metadata fetching."""

    @patch("app.services.youtube_recipe_service.subprocess.run")
    def test_successful_fetch(self, mock_run, app):
        metadata = {
            "title": "Easy Pasta Recipe",
            "duration": 600,
            "thumbnail": "https://img.youtube.com/vi/abc/maxresdefault.jpg",
            "subtitles": {"en": [{"ext": "vtt"}]},
        }
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(metadata), stderr=""
        )

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            result = service._fetch_video_metadata("abc12345678")

        assert result["title"] == "Easy Pasta Recipe"
        assert result["duration"] == 600

    @patch("app.services.youtube_recipe_service.subprocess.run")
    def test_video_too_long(self, mock_run, app):
        metadata = {"title": "Long Video", "duration": 2400}
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(metadata), stderr=""
        )

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            with pytest.raises(YouTubeValidationError, match="too long"):
                service._fetch_video_metadata("abc12345678")

    @patch("app.services.youtube_recipe_service.subprocess.run")
    def test_live_stream_rejected(self, mock_run, app):
        metadata = {"title": "Live Stream", "duration": 0, "is_live": True}
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(metadata), stderr=""
        )

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            with pytest.raises(YouTubeValidationError, match="Live streams"):
                service._fetch_video_metadata("abc12345678")

    @patch("app.services.youtube_recipe_service.subprocess.run")
    def test_private_video_error(self, mock_run, app):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ERROR: Private video. Sign in if you've been granted access",
        )

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            with pytest.raises(YouTubeDownloadError, match="private"):
                service._fetch_video_metadata("abc12345678")

    @patch("app.services.youtube_recipe_service.subprocess.run")
    def test_age_restricted_video(self, mock_run, app):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ERROR: age restricted video",
        )

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            with pytest.raises(YouTubeDownloadError, match="age-restricted"):
                service._fetch_video_metadata("abc12345678")

    @patch("app.services.youtube_recipe_service.subprocess.run")
    def test_network_error(self, mock_run, app):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="yt-dlp", timeout=60)

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            with pytest.raises(YouTubeDownloadError, match="Timed out"):
                service._fetch_video_metadata("abc12345678")


# ═══════════════════════════════════════════════════════════════════
# Caption Extraction Tests
# ═══════════════════════════════════════════════════════════════════


class TestCaptionExtraction:
    """Test caption source determination and extraction."""

    def test_manual_captions_preferred_over_auto(self, app):
        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()

            metadata = {
                "subtitles": {"en": [{"ext": "vtt"}]},
                "automatic_captions": {"en": [{"ext": "vtt"}]},
            }
            result = service._determine_caption_source(metadata)
            assert result is not None
            is_manual, lang = result
            assert is_manual is True
            assert lang == "en"

    def test_auto_captions_fallback(self, app):
        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()

            metadata = {
                "subtitles": {},
                "automatic_captions": {"en": [{"ext": "vtt"}]},
            }
            result = service._determine_caption_source(metadata)
            assert result is not None
            is_manual, lang = result
            assert is_manual is False
            assert lang == "en"

    def test_no_captions_returns_none(self, app):
        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()

            metadata = {"subtitles": {}, "automatic_captions": {}}
            result = service._determine_caption_source(metadata)
            assert result is None

    def test_non_english_caption_language(self, app):
        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()

            metadata = {
                "subtitles": {"fr": [{"ext": "vtt"}]},
                "automatic_captions": {},
            }
            result = service._determine_caption_source(metadata)
            assert result is not None
            is_manual, lang = result
            assert is_manual is True
            assert lang == "fr"


# ═══════════════════════════════════════════════════════════════════
# Audio Fallback Tests
# ═══════════════════════════════════════════════════════════════════


class TestAudioFallback:
    """Test audio download and transcription fallback."""

    @patch("app.services.youtube_recipe_service.subprocess.run")
    def test_audio_download_success(self, mock_run, app, tmp_path):
        # Create a fake audio file
        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake mp3 data")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            result = service._download_audio("abc12345678", str(tmp_path))

        assert result is not None
        assert result.endswith(".mp3")

    @patch("app.services.youtube_recipe_service.subprocess.run")
    def test_audio_download_failure(self, mock_run, app, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="ERROR: download failed"
        )

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            with pytest.raises(YouTubeDownloadError, match="Failed to download"):
                service._download_audio("abc12345678", str(tmp_path))


# ═══════════════════════════════════════════════════════════════════
# Thumbnail Tests
# ═══════════════════════════════════════════════════════════════════


class TestThumbnailDownload:
    """Test thumbnail download (graceful failure)."""

    @patch("app.services.youtube_recipe_service.requests.get")
    def test_success(self, mock_get, app, tmp_path):
        mock_response = MagicMock()
        mock_response.content = b"\xff\xd8\xff\xe0fake jpeg data"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            result = service._download_thumbnail(
                "https://img.youtube.com/vi/abc/maxresdefault.jpg",
                str(tmp_path),
            )

        assert result is not None
        assert result.endswith("thumbnail.jpg")

    @patch("app.services.youtube_recipe_service.requests.get")
    def test_graceful_failure(self, mock_get, app, tmp_path):
        mock_get.side_effect = Exception("Network error")

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            result = service._download_thumbnail(
                "https://img.youtube.com/vi/abc/maxresdefault.jpg",
                str(tmp_path),
            )

        # Should return None, not raise
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# Recipe Parsing Tests
# ═══════════════════════════════════════════════════════════════════


class TestRecipeParsing:
    """Test Claude recipe parsing."""

    @patch("app.services.youtube_recipe_service.anthropic.Anthropic")
    def test_parse_from_captions_text(self, mock_anthropic_cls, app):
        recipe_json = {
            "title": "Spaghetti Carbonara",
            "ingredients": ["200g spaghetti", "100g guanciale"],
            "instructions": ["Cook pasta", "Fry guanciale"],
            "difficulty": "medium",
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(recipe_json))]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            service.anthropic_client = mock_client

            result = service._parse_youtube_recipe(
                transcript="Today we're making carbonara...",
                thumbnail_path=None,
                video_title="Spaghetti Carbonara Recipe",
            )

        assert result is not None
        assert result["title"] == "Spaghetti Carbonara"
        assert len(result["ingredients"]) == 2

    @patch("app.services.youtube_recipe_service.anthropic.Anthropic")
    def test_parse_with_translation_flag(self, mock_anthropic_cls, app):
        recipe_json = {
            "title": "Pasta alla Norma (translated)",
            "ingredients": ["eggplant"],
            "instructions": ["Cook"],
            "is_translated": True,
            "source_language": "it",
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(recipe_json))]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            service.anthropic_client = mock_client

            result = service._parse_youtube_recipe(
                transcript="Oggi facciamo la pasta...",
                thumbnail_path=None,
                video_title="Pasta alla Norma",
                translate_to_english=True,
            )

        assert result is not None
        assert result["is_translated"] is True


# ═══════════════════════════════════════════════════════════════════
# Caching Tests
# ═══════════════════════════════════════════════════════════════════


class TestCaching:
    """Test Redis caching behavior."""

    def test_cache_hit_returns_data(self, app):
        cached_data = {
            "extraction_method": "captions",
            "transcript": "hello world",
            "parsed_recipe": {"title": "Test"},
            "video_title": "Test Video",
        }

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()

            mock_redis = MagicMock()
            mock_redis.get.return_value = json.dumps(cached_data)
            service.redis_client = mock_redis

            result = service._get_from_cache("yt_recipe:abc123")

        assert result is not None
        assert result["parsed_recipe"]["title"] == "Test"

    def test_cache_miss_returns_none(self, app):
        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()

            mock_redis = MagicMock()
            mock_redis.get.return_value = None
            service.redis_client = mock_redis

            result = service._get_from_cache("yt_recipe:nonexistent")

        assert result is None

    def test_redis_unavailable_degrades_gracefully(self, app):
        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            service.redis_client = None

            # Should return None, not raise
            result = service._get_from_cache("yt_recipe:abc")
            assert result is None

            # Should not raise
            service._set_in_cache("yt_recipe:abc", {"test": True})


# ═══════════════════════════════════════════════════════════════════
# End-to-End Tests
# ═══════════════════════════════════════════════════════════════════


class TestEndToEnd:
    """Test full processing pipelines (Tier 1 and Tier 2)."""

    @patch("app.services.youtube_recipe_service.requests.get")
    @patch("app.services.youtube_recipe_service.subprocess.run")
    @patch("app.services.youtube_recipe_service.anthropic.Anthropic")
    def test_tier1_fast_path_captions(
        self, mock_anthropic_cls, mock_run, mock_requests_get, app, tmp_path
    ):
        """Tier 1: captions found, no audio download needed."""
        metadata = {
            "title": "Easy Pasta Recipe",
            "duration": 600,
            "thumbnail": "https://img.youtube.com/vi/abc/default.jpg",
            "subtitles": {"en": [{"ext": "vtt"}]},
            "automatic_captions": {},
        }

        recipe_json = {
            "title": "Easy Pasta",
            "ingredients": ["pasta", "sauce"],
            "instructions": ["Cook pasta", "Add sauce"],
        }

        # Mock yt-dlp calls
        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""

            if "--dump-json" in cmd:
                result.stdout = json.dumps(metadata)
            elif "--write-sub" in cmd or "--write-auto-sub" in cmd:
                result.stdout = ""
                # Create a fake subtitle file in the temp dir
                # Find the output path from -o argument
                for i, arg in enumerate(cmd):
                    if arg == "-o":
                        out_dir = os.path.dirname(cmd[i + 1])
                        vtt_path = os.path.join(out_dir, "subs.en.vtt")
                        with open(vtt_path, "w") as f:
                            f.write(
                                "WEBVTT\n\n"
                                "00:00:01.000 --> 00:00:05.000\n"
                                "Today we're making easy pasta\n\n"
                                "00:00:05.000 --> 00:00:10.000\n"
                                "First boil the water\n"
                            )
                        break
            else:
                result.stdout = ""

            return result

        mock_run.side_effect = mock_subprocess_run

        # Mock thumbnail download
        mock_thumb_response = MagicMock()
        mock_thumb_response.content = b"\xff\xd8fake jpeg"
        mock_thumb_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_thumb_response

        # Mock Claude API
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(recipe_json))]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            service.anthropic_client = mock_client
            service.redis_client = None  # Disable caching for test

            result = service.process_youtube_url(
                video_id="abc12345678",
                youtube_url="https://www.youtube.com/watch?v=abc12345678",
            )

        assert result.success is True
        assert result.extraction_method == "captions"
        assert result.parsed_recipe is not None
        assert result.parsed_recipe["title"] == "Easy Pasta"

    @patch("app.services.youtube_recipe_service.requests.get")
    @patch("app.services.youtube_recipe_service.subprocess.run")
    @patch("app.services.youtube_recipe_service.anthropic.Anthropic")
    def test_tier2_fallback_path_audio(
        self, mock_anthropic_cls, mock_run, mock_requests_get, app, tmp_path
    ):
        """Tier 2: no captions, falls back to audio download + Whisper."""
        metadata = {
            "title": "Cooking Video",
            "duration": 300,
            "thumbnail": "https://img.youtube.com/vi/abc/default.jpg",
            "subtitles": {},
            "automatic_captions": {},
        }

        recipe_json = {
            "title": "Grilled Chicken",
            "ingredients": ["chicken", "salt"],
            "instructions": ["Season chicken", "Grill"],
        }

        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""
            result.stdout = ""

            if "--dump-json" in cmd:
                result.stdout = json.dumps(metadata)
            elif "--write-sub" in cmd or "--write-auto-sub" in cmd:
                # No subtitle files created — simulates no captions
                pass
            elif "-x" in cmd:
                # Audio download — create a fake MP3
                for i, arg in enumerate(cmd):
                    if arg == "-o":
                        out_dir = os.path.dirname(cmd[i + 1])
                        audio_path = os.path.join(out_dir, "audio.mp3")
                        with open(audio_path, "wb") as f:
                            f.write(b"fake mp3 data")
                        break

            return result

        mock_run.side_effect = mock_subprocess_run

        # Mock thumbnail
        mock_thumb = MagicMock()
        mock_thumb.content = b"\xff\xd8fake"
        mock_thumb.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_thumb

        # Mock Claude
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(recipe_json))]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        # Mock Whisper
        mock_openai = MagicMock()
        mock_openai.audio.transcriptions.create.return_value = (
            "Season the chicken with salt and grill it"
        )

        with app.app_context():
            app.config["ANTHROPIC_API_KEY"] = "test-key"
            app.config["OPENAI_API_KEY"] = "test-key"
            service = YouTubeRecipeService()
            service.anthropic_client = mock_client
            service.openai_client = mock_openai
            service.redis_client = None

            result = service.process_youtube_url(
                video_id="abc12345678",
                youtube_url="https://www.youtube.com/watch?v=abc12345678",
            )

        assert result.success is True
        assert result.extraction_method == "audio_fallback"
        assert result.parsed_recipe["title"] == "Grilled Chicken"
        # Verify Whisper was called
        mock_openai.audio.transcriptions.create.assert_called_once()


# ═══════════════════════════════════════════════════════════════════
# Subtitle Parsing Tests
# ═══════════════════════════════════════════════════════════════════


class TestSubtitleParsing:
    """Test VTT/SRT subtitle file parsing."""

    def test_vtt_parsing(self, tmp_path):
        vtt_content = (
            "WEBVTT\n"
            "Kind: captions\n"
            "\n"
            "00:00:01.000 --> 00:00:05.000\n"
            "Today we're making pasta\n"
            "\n"
            "00:00:05.000 --> 00:00:10.000\n"
            "First, boil the water\n"
            "\n"
            "00:00:10.000 --> 00:00:15.000\n"
            "First, boil the water\n"  # duplicate line
        )
        filepath = tmp_path / "test.vtt"
        filepath.write_text(vtt_content)

        result = YouTubeRecipeService._parse_subtitle_file(str(filepath))
        assert result is not None
        assert "pasta" in result
        assert "boil the water" in result
        # Duplicate line should be deduplicated
        assert result.count("boil the water") == 1

    def test_empty_subtitle_file(self, tmp_path):
        filepath = tmp_path / "empty.vtt"
        filepath.write_text("WEBVTT\n\n")

        result = YouTubeRecipeService._parse_subtitle_file(str(filepath))
        assert result is None
