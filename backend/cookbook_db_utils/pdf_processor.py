#!/usr/bin/env python3
"""
PDF Processing Module - Extract text from cookbook PDFs

This module provides utilities for:
- Extracting text from PDF files with proper formatting preservation
- Cleaning and normalizing extracted text for recipe parsing
- Handling page-by-page processing with metadata
- OCR fallback for scanned documents if needed
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import tempfile
import hashlib
import json
import os

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    print("Warning: pdfplumber not installed. Install with: pip install pdfplumber")

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None
    print("Warning: pdf2image not installed. Install with: pip install pdf2image")

try:
    import anthropic
except ImportError:
    anthropic = None
    print("Warning: anthropic not installed. Install with: pip install anthropic")

try:
    import redis
except ImportError:
    redis = None
    print("Warning: redis not installed. Install with: pip install redis")


class PDFProcessor:
    """Extract and process text from PDF cookbooks"""

    def __init__(self, use_llm: bool = True, anthropic_api_key: Optional[str] = None):
        """Initialize PDF processor

        Args:
            use_llm: Whether to use LLM for text extraction
            anthropic_api_key: Anthropic API key for Claude Haiku
        """
        if not pdfplumber:
            raise ImportError(
                "pdfplumber is required. Install with: pip install pdfplumber"
            )

        self.logger = logging.getLogger(__name__)

        self.use_llm = (
            use_llm and convert_from_path is not None and anthropic is not None
        )

        # Initialize Anthropic client if available
        self.anthropic_client = None
        if self.use_llm and anthropic:
            try:
                api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                    self.logger.info(
                        "Anthropic Claude client initialized for enhanced text extraction"
                    )
                else:
                    self.logger.info(
                        "No Anthropic API key found, falling back to pdfplumber only"
                    )
                    self.use_llm = False
            except Exception as e:
                self.logger.warning(f"Failed to initialize Anthropic client: {e}")
                self.use_llm = False
        elif use_llm:
            self.logger.info(
                "LLM requested but dependencies missing, falling back to pdfplumber"
            )
            self.use_llm = False

        # Initialize Redis for caching if available
        self.redis_client = None
        if redis:
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()  # Test connection
                self.cache_ttl = 86400  # 24 hours
                self.logger.info("Redis caching enabled for PDF processing")
            except Exception as e:
                self.logger.info(f"Redis not available, caching disabled: {e}")
                self.redis_client = None

    def extract_text_from_pdf(self, pdf_path: Path, max_pages: Optional[int] = None, skip_pages: int = 0) -> Dict:
        """
        Extract text from PDF file with page-by-page processing.

        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process (None = all pages)
            skip_pages: Number of pages to skip at the beginning

        Returns:
            Dictionary containing extracted text and metadata
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        result = {
            "pages": [],
            "total_pages": 0,
            "full_text": "",
            "metadata": {},
            "processing_errors": [],
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                result["total_pages"] = len(pdf.pages)
                result["metadata"] = self._extract_metadata(pdf)

                # Calculate page range to process
                start_page = skip_pages
                if max_pages:
                    end_page = min(start_page + max_pages, result['total_pages'])
                else:
                    end_page = result['total_pages']
                
                pages_to_process = end_page - start_page
                
                self.logger.info(
                    f"Processing PDF: {pdf_path.name} - {result['total_pages']} total pages, processing pages {start_page + 1}-{end_page} ({pages_to_process} pages)"
                )

                for page_index, page in enumerate(pdf.pages[start_page:end_page], start_page + 1):
                    try:
                        page_data = self._extract_page_text(page, page_index, pdf_path)
                        result["pages"].append(page_data)
                        result["full_text"] += page_data["text"] + "\n\n"

                        if (page_index - start_page) % 10 == 0:
                            self.logger.info(
                                f"Processed {page_index - start_page}/{pages_to_process} pages (page {page_index})"
                            )

                    except Exception as e:
                        error_msg = f"Error processing page {page_index}: {str(e)}"
                        self.logger.error(error_msg)
                        result["processing_errors"].append(error_msg)

                        # Add empty page data to maintain page order
                        result["pages"].append(
                            {
                                "page_number": page_index,
                                "text": "",
                                "char_count": 0,
                                "line_count": 0,
                                "error": str(e),
                            }
                        )

        except Exception as e:
            error_msg = f"Failed to open PDF file: {str(e)}"
            self.logger.error(error_msg)
            result["processing_errors"].append(error_msg)
            raise

        # Clean and normalize the full text
        result["full_text"] = self._clean_text(result["full_text"])

        self.logger.info(
            f"Successfully extracted {len(result['full_text'])} characters from {result['total_pages']} pages"
        )

        return result

    def _extract_metadata(self, pdf) -> Dict:
        """Extract metadata from PDF"""
        metadata = {}

        try:
            info = pdf.metadata
            if info:
                metadata.update(
                    {
                        "title": info.get("Title", ""),
                        "author": info.get("Author", ""),
                        "subject": info.get("Subject", ""),
                        "creator": info.get("Creator", ""),
                        "producer": info.get("Producer", ""),
                        "creation_date": str(info.get("CreationDate", "")),
                        "modification_date": str(info.get("ModDate", "")),
                    }
                )
        except Exception as e:
            self.logger.warning(f"Could not extract PDF metadata: {e}")

        return metadata

    def extract_enhanced_metadata(self, pdf_path: Path) -> Dict:
        """Extract enhanced metadata using Google Books API"""
        try:
            from cookbook_db_utils.google_books_metadata import GoogleBooksMetadataExtractor

            # First extract basic PDF metadata
            basic_metadata = {}
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    basic_metadata = self._extract_metadata(pdf)
            except Exception as e:
                self.logger.warning(f"Could not extract basic PDF metadata: {e}")

            # Use Google Books to enhance metadata
            extractor = GoogleBooksMetadataExtractor()
            enhanced_metadata = extractor.extract_metadata_from_pdf_info(str(pdf_path), basic_metadata)

            return enhanced_metadata

        except ImportError:
            self.logger.warning("Google Books metadata extractor not available")
            return self._extract_fallback_metadata(pdf_path)
        except Exception as e:
            self.logger.warning(f"Google Books metadata extraction failed: {e}")
            return self._extract_fallback_metadata(pdf_path)

    def _extract_fallback_metadata(self, pdf_path: Path) -> Dict:
        """Extract basic metadata when Google Books is not available"""
        filename = pdf_path.stem.replace('_', ' ').replace('-', ' ')

        return {
            'title': filename.title(),
            'author': 'Unknown',
            'authors': [],
            'description': f'Cookbook imported from PDF file: {pdf_path.name}',
            'publisher': '',
            'publication_date': None,
            'isbn_10': None,
            'isbn_13': None,
            'source': 'filename_only'
        }

    def _extract_page_text(
        self, page, page_num: int, pdf_path: Optional[Path] = None
    ) -> Dict:
        """Extract text from a single page with metadata"""
        try:
            # Try LLM-based extraction first if available
            if self.use_llm and self.anthropic_client and pdf_path:
                try:
                    llm_text = self._extract_page_text_with_llm(pdf_path, page_num)
                    if llm_text and len(llm_text.strip()) > 10:  # Valid extraction
                        self.logger.debug(
                            f"Successfully extracted page {page_num} text using Claude Haiku"
                        )
                        return {
                            "page_number": page_num,
                            "text": llm_text,
                            "char_count": len(llm_text),
                            "line_count": len(llm_text.split("\n")) if llm_text else 0,
                            "extraction_method": "claude_haiku",
                            "bbox": page.bbox if hasattr(page, "bbox") else None,
                        }
                except Exception as e:
                    self.logger.warning(
                        f"LLM extraction failed for page {page_num}, falling back to pdfplumber: {e}"
                    )

            # Fallback to pdfplumber extraction
            text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=2)

            if not text:
                text = ""

            # Clean up common PDF artifacts
            text = self._clean_page_text(text)

            return {
                "page_number": page_num,
                "text": text,
                "char_count": len(text),
                "line_count": len(text.split("\n")) if text else 0,
                "extraction_method": "pdfplumber",
                "bbox": page.bbox if hasattr(page, "bbox") else None,
            }

        except Exception as e:
            self.logger.error(f"Error extracting text from page {page_num}: {e}")
            return {
                "page_number": page_num,
                "text": "",
                "char_count": 0,
                "line_count": 0,
                "extraction_method": "failed",
                "error": str(e),
            }

    def _clean_page_text(self, text: str) -> str:
        """Clean common PDF text extraction artifacts from a single page"""
        if not text:
            return ""

        # Remove excessive whitespace but preserve structure
        text = re.sub(
            r"\n\s*\n\s*\n+", "\n\n", text
        )  # Multiple blank lines -> double line break
        text = re.sub(r"[ \t]+", " ", text)  # Multiple spaces/tabs -> single space
        text = re.sub(r" +\n", "\n", text)  # Trailing spaces before newlines

        # Remove common PDF artifacts
        text = re.sub(r"\uf0b7|\uf0a7|\uf0fc", "•", text)  # Convert bullet characters
        text = re.sub(r"\uf8ff|\ufeff", "", text)  # Remove BOM and other special chars

        # Fix common OCR/PDF extraction issues (conservative approach)
        # Don't remove line breaks - preserve text structure for recipe segmentation!

        return text.strip()

    def _clean_text(self, text: str) -> str:
        """Clean and normalize the full extracted text"""
        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines but preserve paragraph structure
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        # Remove page numbers and headers/footers (common patterns)
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # Skip likely page numbers (just numbers on their own line)
            if re.match(r"^\s*\d+\s*$", line):
                continue

            # Skip likely headers/footers (very short lines with common patterns)
            if len(line) < 5 and re.match(r"^[\d\-\s]+$", line):
                continue

            cleaned_lines.append(line)

        # Rejoin and do final cleanup
        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # Final blank line cleanup

        return text.strip()

    def extract_recipe_candidates(self, pdf_text: str) -> List[Dict]:
        """
        Extract potential recipe segments from the full PDF text.
        This is a basic implementation that can be enhanced.

        Args:
            pdf_text: Full text extracted from PDF

        Returns:
            List of dictionaries containing potential recipe segments
        """
        recipe_candidates = []

        # Split text into potential recipe sections
        # Look for lines that are likely recipe titles (all caps, or title case at start of line)
        lines = pdf_text.split("\n")
        current_recipe = []
        recipe_title = None

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                if current_recipe:
                    current_recipe.append("")
                continue

            # Check if this looks like a recipe title
            # Cookbooks often have titles in all caps or prominent formatting
            is_potential_title = (
                # All caps line (but not too long to avoid headers)
                (line.isupper() and len(line) > 3 and len(line) < 80)
                or
                # Title case at start of line with food words
                (
                    self._looks_like_recipe_title(line)
                    and i > 0
                    and lines[i - 1].strip() == ""
                )
            )

            if is_potential_title and current_recipe:
                # Save previous recipe candidate
                if recipe_title:
                    recipe_candidates.append(
                        {
                            "title": recipe_title,
                            "content": "\n".join(current_recipe).strip(),
                            "line_start": len(recipe_candidates) * 20,  # Approximate
                            "char_count": len("\n".join(current_recipe)),
                        }
                    )

                # Start new recipe
                recipe_title = line
                current_recipe = []

            elif is_potential_title and not current_recipe:
                # First recipe or standalone title
                recipe_title = line
                current_recipe = []

            else:
                # Regular content line
                current_recipe.append(line)

        # Don't forget the last recipe
        if recipe_title and current_recipe:
            recipe_candidates.append(
                {
                    "title": recipe_title,
                    "content": "\n".join(current_recipe).strip(),
                    "line_start": len(recipe_candidates) * 20,
                    "char_count": len("\n".join(current_recipe)),
                }
            )

        self.logger.info(f"Found {len(recipe_candidates)} potential recipe segments")

        return recipe_candidates

    def _looks_like_recipe_title(self, line: str) -> bool:
        """Check if a line looks like a recipe title"""
        # Common food/cooking words that might appear in recipe titles
        food_words = [
            "cake",
            "bread",
            "soup",
            "stew",
            "pie",
            "pudding",
            "sauce",
            "salad",
            "chicken",
            "beef",
            "pork",
            "fish",
            "eggs",
            "beans",
            "rice",
            "potato",
            "cookies",
            "biscuits",
            "muffins",
            "pancakes",
            "waffles",
            "custard",
            "jelly",
            "preserves",
            "pickles",
            "roast",
            "baked",
            "fried",
            "boiled",
        ]

        line_lower = line.lower()

        # Check for food words
        has_food_word = any(word in line_lower for word in food_words)

        # Check for title-like formatting
        is_title_case = line.istitle() or (line[0].isupper() if line else False)

        # Not too long (avoid paragraphs)
        reasonable_length = 5 < len(line) < 80

        # Doesn't look like an instruction (avoid imperative verbs at start)
        instruction_starters = [
            "take",
            "add",
            "mix",
            "stir",
            "cook",
            "bake",
            "boil",
            "fry",
        ]
        not_instruction = not any(
            line_lower.startswith(word) for word in instruction_starters
        )

        return has_food_word and is_title_case and reasonable_length and not_instruction

    def _extract_page_text_with_llm(
        self, pdf_path: Path, page_num: int
    ) -> Optional[str]:
        """Extract text from a specific PDF page using Claude Haiku vision model"""

        # Generate cache key for this page
        cache_key = self._generate_page_cache_key(pdf_path, page_num)

        # Check cache first
        if self.redis_client:
            try:
                cached_text = self.redis_client.get(cache_key)
                if cached_text:
                    return json.loads(cached_text)
            except Exception:
                pass  # Cache failure shouldn't break processing

        try:
            # Convert PDF page to image
            page_image = self._pdf_page_to_image(pdf_path, page_num)
            if not page_image:
                return None

            # Convert image to base64 for Claude
            image_data = self._image_to_base64(page_image)

            # Call Claude Haiku for text extraction
            prompt = self._build_llm_extraction_prompt()

            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Cheap, fast model
                max_tokens=2000,
                temperature=0.1,
                system="You are an expert at extracting text from cookbook pages with high accuracy.",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_data["media_type"],
                                    "data": image_data["data"],
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            extracted_text = response.content[0].text.strip()

            # Cache the result
            if self.redis_client and extracted_text:
                try:
                    self.redis_client.setex(
                        cache_key, self.cache_ttl, json.dumps(extracted_text)
                    )
                except Exception:
                    pass  # Cache failure shouldn't break processing

            return extracted_text

        except Exception as e:
            self.logger.error(
                f"Failed to extract text from page {page_num} using LLM: {e}"
            )
            return None

    def _pdf_page_to_image(self, pdf_path: Path, page_num: int) -> Optional[Path]:
        """Convert a specific PDF page to an image file"""
        try:
            # Create temporary directory for image
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Convert specific page to image (page_num is 1-indexed)
                images = convert_from_path(
                    pdf_path,
                    dpi=200,  # Good balance of quality and file size
                    first_page=page_num,
                    last_page=page_num,
                    fmt="PNG",
                )

                if not images:
                    return None

                # Save image to temporary file
                image_path = temp_path / f"page_{page_num}.png"
                images[0].save(image_path, "PNG")

                # Copy to a more permanent temp location for processing
                import shutil

                final_temp_path = Path(tempfile.mktemp(suffix=".png"))
                shutil.copy2(image_path, final_temp_path)

                return final_temp_path

        except Exception as e:
            self.logger.error(f"Failed to convert PDF page {page_num} to image: {e}")
            return None

    def _image_to_base64(self, image_path: Path) -> Dict[str, str]:
        """Convert image to base64 for API transmission"""
        try:
            import base64
            from PIL import Image

            # Open and optimize image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")

                # Resize if too large (max 1568x1568 for Claude)
                max_size = 1568
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                # Save to bytes
                import io

                img_buffer = io.BytesIO()
                img.save(img_buffer, format="JPEG", quality=85)
                img_bytes = img_buffer.getvalue()

            # Clean up temporary file
            try:
                image_path.unlink()
            except:
                pass

            # Encode to base64
            base64_data = base64.b64encode(img_bytes).decode("utf-8")

            return {"data": base64_data, "media_type": "image/jpeg"}

        except Exception as e:
            self.logger.error(f"Failed to convert image to base64: {e}")
            raise

    def _build_llm_extraction_prompt(self) -> str:
        """Build the prompt for LLM-based text extraction"""
        return """Please extract ALL text from this cookbook page with high accuracy. Focus on:

1. **Recipe Titles** - Extract complete recipe names
2. **Ingredients** - Preserve exact measurements, units, and ingredient names
3. **Instructions** - Maintain step-by-step order and cooking details
4. **Additional Info** - Cooking times, serving sizes, temperatures, notes

EXTRACTION GUIDELINES:
- Preserve original spelling, capitalization, and terminology
- Include ALL visible text, even if partially obscured or faded
- Maintain the logical structure and layout
- Use clear line breaks between different sections
- If text is unclear, make your best interpretation
- Include any page numbers, headers, or marginalia

OUTPUT FORMAT:
Return the extracted text in a clean, readable format that preserves the page's structure. Do not add explanations or modify the content - just extract what you see exactly as it appears."""

    def _generate_page_cache_key(self, pdf_path: Path, page_num: int) -> str:
        """Generate a cache key for a specific PDF page"""
        try:
            # Create hash from file path and modification time for cache invalidation
            stat = pdf_path.stat()
            content_hash = hashlib.sha256(
                f"{pdf_path}_{stat.st_mtime}_{page_num}".encode("utf-8")
            ).hexdigest()
            return f"pdf_llm_page:{content_hash}"
        except Exception:
            # Fallback to simple hash
            content_hash = hashlib.sha256(
                f"{pdf_path}_{page_num}".encode("utf-8")
            ).hexdigest()
            return f"pdf_llm_page:{content_hash}"


# Convenience function for direct usage
def extract_pdf_cookbook_text(
    pdf_path: str, use_llm: bool = True, anthropic_api_key: str = None, 
    max_pages: Optional[int] = None, skip_pages: int = 0
) -> Dict:
    """
    Convenience function to extract text from a PDF cookbook.

    Args:
        pdf_path: Path to the PDF file (string)
        use_llm: Whether to use LLM for enhanced text extraction
        anthropic_api_key: Anthropic API key (if not provided, will try to get from env)
        max_pages: Maximum number of pages to process (None = all pages)
        skip_pages: Number of pages to skip at the beginning

    Returns:
        Dictionary with extracted text and recipe candidates
    """
    processor = PDFProcessor(use_llm=use_llm, anthropic_api_key=anthropic_api_key)
    pdf_path_obj = Path(pdf_path)

    # Extract text from PDF with page limits
    extraction_result = processor.extract_text_from_pdf(pdf_path_obj, max_pages=max_pages, skip_pages=skip_pages)

    # Extract recipe candidates
    recipe_candidates = processor.extract_recipe_candidates(
        extraction_result["full_text"]
    )

    return {
        "pdf_data": extraction_result,
        "recipe_candidates": recipe_candidates,
        "summary": {
            "total_pages": extraction_result["total_pages"],
            "total_chars": len(extraction_result["full_text"]),
            "potential_recipes": len(recipe_candidates),
            "processing_errors": len(extraction_result["processing_errors"]),
        },
    }


# Backward compatibility function
def extract_historical_cookbook_text(
    pdf_path: str, use_llm: bool = True, anthropic_api_key: str = None
) -> Dict:
    """
    Backward compatibility wrapper for historical cookbook text extraction.
    """
    return extract_pdf_cookbook_text(pdf_path, use_llm, anthropic_api_key, max_pages=None, skip_pages=0)


if __name__ == "__main__":
    # Test the PDF processor with a sample cookbook
    import logging

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Test with a sample cookbook
    pdf_path = "/Users/baasman/projects/cookbook-creator/backend/scripts/seed_data/175_choice_recipes_mainly_furnished_by_members_of_the_chicago_womens_club-1887.pdf"

    try:
        result = extract_pdf_cookbook_text(pdf_path, use_llm=True)
        print(f"📖 PDF Processing Results (with Claude Haiku enhancement):")
        print(f"   📄 Pages: {result['summary']['total_pages']}")
        print(f"   📝 Characters: {result['summary']['total_chars']:,}")
        print(f"   🍽️  Potential recipes: {result['summary']['potential_recipes']}")
        print(f"   ⚠️  Errors: {result['summary']['processing_errors']}")

        if result["recipe_candidates"]:
            print(f"\n🔍 First few recipe candidates:")
            for i, recipe in enumerate(result["recipe_candidates"][:5]):
                print(f"   {i+1}. {recipe['title'][:50]}...")

    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
