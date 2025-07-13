from pathlib import Path
import tempfile
from typing import Dict, Tuple

import pytesseract
from PIL import Image
import numpy as np
from skimage import filters, morphology, transform, exposure, io
from skimage.color import rgb2gray
from skimage.util import img_as_ubyte
from flask import current_app

from app.exceptions import OCRExtractionError
from app.services.ocr_quality_service import OCRQualityService
from app.services.llm_ocr_service import LLMOCRService


class OCRService:
    def __init__(self):
        self.quality_service = OCRQualityService()
        self.llm_ocr_service = LLMOCRService()

    def extract_text_from_image(self, image_path: Path) -> str:
        try:
            # Preprocess the image for better OCR results
            preprocessed_path = self.preprocess_image(image_path)

            # Load preprocessed image
            image = Image.open(preprocessed_path)

            # Use custom OCR configuration for better results
            custom_config = r"--oem 3 --psm 6 -c tessedit_char_blacklist=|"
            text = pytesseract.image_to_string(image, config=custom_config)

            # Clean up temporary file if created
            if preprocessed_path != image_path:
                preprocessed_path.unlink()

            return text.strip()
        except Exception as e:
            raise OCRExtractionError(f"OCR extraction failed: {str(e)}", e) from e

    def extract_text_with_quality_check(self, image_path: Path) -> Dict[str, any]:
        """
        Extract text with quality assessment and intelligent fallback to LLM.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary containing:
            - text: The extracted text
            - method: 'traditional' or 'llm'
            - quality_score: 1-10 quality assessment (only for traditional OCR)
            - quality_reasoning: Explanation of quality score
            - fallback_used: Whether LLM fallback was triggered
        """
        result = {
            "text": "",
            "method": "traditional",
            "quality_score": None,
            "quality_reasoning": "",
            "fallback_used": False
        }

        # Get quality threshold from config
        quality_threshold = current_app.config.get("OCR_QUALITY_THRESHOLD", 6)
        llm_fallback_enabled = current_app.config.get("OCR_ENABLE_LLM_FALLBACK", True)

        try:
            # Step 1: Try traditional OCR first
            current_app.logger.info(f"Starting traditional OCR extraction for {image_path}")
            traditional_text = self.extract_text_from_image(image_path)

            # Step 2: Assess quality of traditional OCR
            current_app.logger.info("Assessing OCR quality...")
            quality_score, quality_reasoning = self.quality_service.assess_quality(traditional_text)

            result.update({
                "text": traditional_text,
                "quality_score": quality_score,
                "quality_reasoning": quality_reasoning
            })

            current_app.logger.info(f"OCR quality score: {quality_score}/10 - {quality_reasoning}")

            # Step 3: Decide whether to use LLM fallback
            if quality_score < quality_threshold and llm_fallback_enabled:
                current_app.logger.info(f"Quality score {quality_score} below threshold {quality_threshold}, using LLM fallback")

                try:
                    llm_text = self.llm_ocr_service.extract_text_from_image(image_path)
                    result.update({
                        "text": llm_text,
                        "method": "llm",
                        "fallback_used": True
                    })
                    current_app.logger.info("LLM OCR extraction completed successfully")

                except Exception as llm_error:
                    current_app.logger.error(f"LLM OCR fallback failed: {str(llm_error)}")
                    # Keep traditional OCR result despite poor quality
                    result["quality_reasoning"] += f" (LLM fallback failed: {str(llm_error)})"
            else:
                current_app.logger.info(f"Using traditional OCR result (quality: {quality_score}/10)")

            return result

        except Exception as e:
            current_app.logger.error(f"OCR extraction with quality check failed: {str(e)}")
            raise OCRExtractionError(f"OCR extraction with quality check failed: {str(e)}", e) from e

    def preprocess_image(self, image_path: Path) -> Path:
        try:
            # Load image with scikit-image
            img = io.imread(str(image_path))
            if img is None:
                return image_path

            # Convert to grayscale if needed
            if len(img.shape) == 3:
                gray = rgb2gray(img)
            else:
                gray = img

            # Apply Gaussian filter to reduce noise
            blurred = filters.gaussian(gray, sigma=1.0)

            # Enhance contrast using adaptive histogram equalization
            enhanced = exposure.equalize_adapthist(blurred, clip_limit=0.03)

            # Apply threshold for better text contrast
            threshold_val = filters.threshold_otsu(enhanced)
            binary = enhanced > threshold_val

            # Remove noise with morphological operations
            disk_elem = morphology.disk(1)
            processed = morphology.closing(binary, disk_elem)
            processed = morphology.opening(processed, disk_elem)

            # Resize image if too small (OCR works better on larger images)
            height, width = processed.shape
            if height < 600 or width < 600:
                scale_factor = max(600 / height, 600 / width)
                new_height = int(height * scale_factor)
                new_width = int(width * scale_factor)
                processed = transform.resize(
                    processed, (new_height, new_width),
                    order=3, preserve_range=True, anti_aliasing=True
                )

            # Convert to uint8 for saving
            processed_uint8 = img_as_ubyte(processed)

            # Save processed image to temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                temp_path = Path(tmp_file.name)
                io.imsave(str(temp_path), processed_uint8)
                return temp_path

        except Exception:
            # If preprocessing fails, return original image
            return image_path
