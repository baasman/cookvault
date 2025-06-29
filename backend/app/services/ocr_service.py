from pathlib import Path
import tempfile

import pytesseract
from PIL import Image
import numpy as np
from skimage import filters, morphology, transform, exposure, io
from skimage.color import rgb2gray
from skimage.util import img_as_ubyte

from app.exceptions import OCRExtractionError


class OCRService:
    def __init__(self):
        pass

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
