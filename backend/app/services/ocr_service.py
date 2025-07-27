from pathlib import Path
import tempfile
import re
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
    
    def extract_text_from_multiple_images(self, image_paths: list[Path], maintain_order: bool = True) -> Dict[str, any]:
        """
        Extract text from multiple images with quality assessment and optimization.
        
        Args:
            image_paths: List of paths to image files in order
            maintain_order: Whether to process images in sequential order
            
        Returns:
            Dictionary containing:
            - results: List of extraction results per image
            - overall_quality: Overall quality assessment
            - completeness_score: Recipe completeness assessment
            - processing_summary: Summary of processing results
        """
        if not image_paths:
            raise ValueError("At least one image path is required")
        
        results = []
        successful_extractions = 0
        total_quality_score = 0
        processing_errors = []
        
        current_app.logger.info(f"Starting multi-image OCR processing for {len(image_paths)} images")
        
        for i, image_path in enumerate(image_paths):
            current_app.logger.info(f"Processing image {i+1}/{len(image_paths)}: {image_path}")
            
            try:
                # Extract text with quality assessment
                extraction_result = self.extract_text_with_quality_check(image_path)
                extraction_result['image_index'] = i
                extraction_result['image_path'] = str(image_path)
                
                results.append(extraction_result)
                
                if extraction_result['text'].strip():
                    successful_extractions += 1
                    if extraction_result['quality_score']:
                        total_quality_score += extraction_result['quality_score']
                        
                current_app.logger.info(f"Image {i+1} processed: {len(extraction_result['text'])} chars, quality: {extraction_result.get('quality_score', 'N/A')}")
                
            except Exception as e:
                error_msg = f"Failed to process image {i+1} ({image_path}): {str(e)}"
                current_app.logger.error(error_msg)
                processing_errors.append(error_msg)
                
                # Add failed result to maintain order
                results.append({
                    'image_index': i,
                    'image_path': str(image_path),
                    'text': '',
                    'method': 'failed',
                    'quality_score': 0,
                    'quality_reasoning': f'Processing failed: {str(e)}',
                    'fallback_used': False,
                    'error': str(e)
                })
        
        # Calculate overall quality metrics
        avg_quality = (total_quality_score / successful_extractions) if successful_extractions > 0 else 0
        success_rate = (successful_extractions / len(image_paths)) * 100
        
        # Assess overall completeness
        all_texts = [r['text'] for r in results if r['text'].strip()]
        completeness_score = self._assess_multi_image_completeness(all_texts)
        
        processing_summary = {
            'total_images': len(image_paths),
            'successful_extractions': successful_extractions,
            'failed_extractions': len(image_paths) - successful_extractions,
            'success_rate': success_rate,
            'average_quality': avg_quality,
            'processing_errors': processing_errors
        }
        
        current_app.logger.info(f"Multi-image OCR completed: {successful_extractions}/{len(image_paths)} successful, avg quality: {avg_quality:.1f}")
        
        return {
            'results': results,
            'overall_quality': avg_quality,
            'completeness_score': completeness_score,
            'processing_summary': processing_summary
        }
    
    def _assess_multi_image_completeness(self, texts: list[str]) -> Dict[str, any]:
        """
        Assess the completeness of a multi-image recipe extraction.
        
        Args:
            texts: List of extracted text from all images
            
        Returns:
            Dictionary with completeness assessment
        """
        if not texts:
            return {
                'score': 0,
                'has_title': False,
                'has_ingredients': False,
                'has_instructions': False,
                'estimated_completeness': 0,
                'missing_elements': ['title', 'ingredients', 'instructions'],
                'reasoning': 'No text extracted from any image'
            }
        
        combined_text = '\n'.join(texts).lower()
        
        # Check for key recipe elements
        has_title = bool(self._detect_title_indicators(combined_text))
        has_ingredients = bool(self._detect_ingredient_indicators(combined_text))
        has_instructions = bool(self._detect_instruction_indicators(combined_text))
        
        # Calculate completeness score
        elements_found = sum([has_title, has_ingredients, has_instructions])
        completeness_percentage = (elements_found / 3) * 100
        
        # Determine overall score (1-10)
        if completeness_percentage >= 90:
            score = 10
        elif completeness_percentage >= 75:
            score = 8
        elif completeness_percentage >= 50:
            score = 6
        elif completeness_percentage >= 25:
            score = 4
        else:
            score = 2
        
        missing_elements = []
        if not has_title:
            missing_elements.append('title')
        if not has_ingredients:
            missing_elements.append('ingredients')
        if not has_instructions:
            missing_elements.append('instructions')
        
        reasoning = f"Found {elements_found}/3 key elements. "
        if missing_elements:
            reasoning += f"Missing: {', '.join(missing_elements)}."
        else:
            reasoning += "All key elements detected."
        
        return {
            'score': score,
            'has_title': has_title,
            'has_ingredients': has_ingredients,
            'has_instructions': has_instructions,
            'estimated_completeness': completeness_percentage,
            'missing_elements': missing_elements,
            'reasoning': reasoning
        }
    
    def _detect_title_indicators(self, text: str) -> bool:
        """Detect if text contains recipe title indicators."""
        title_patterns = [
            r'\b\w+\s+(cake|cookies?|bread|soup|stew|salad|pasta)\b',
            r'\b(recipe|dish|meal)\b.*\b(for|with|and)\b',
            r'^\s*[A-Z][a-z\s]+\s*$',  # Capitalized standalone lines
        ]
        
        for pattern in title_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _detect_ingredient_indicators(self, text: str) -> bool:
        """Detect if text contains ingredient list indicators."""
        ingredient_patterns = [
            r'\bingredients?\b',
            r'\b\d+\s*(cups?|tbsp|tsp|pounds?|oz|grams?|ml|liters?)\b',
            r'\b\d+\s*\w+\s+(flour|sugar|butter|oil|salt|pepper)\b',
            r'[\•\-\*]\s*\d',  # Bullet points with measurements
        ]
        
        for pattern in ingredient_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _detect_instruction_indicators(self, text: str) -> bool:
        """Detect if text contains instruction/method indicators."""
        instruction_patterns = [
            r'\b(instructions?|method|directions?|steps?)\b',
            r'\b\d+\.\s+\w+',  # Numbered steps
            r'\b(mix|stir|bake|cook|heat|add|combine|blend)\b',
            r'\b(preheat|oven|pan|bowl)\b',
        ]
        
        for pattern in instruction_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
