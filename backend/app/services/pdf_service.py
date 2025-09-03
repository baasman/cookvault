"""
PDF Generation Service for Recipes and Cookbooks

This service provides professional PDF generation capabilities for:
- Individual recipes
- Complete cookbooks
- Recipe collections

Supports multiple templates and print-ready output.
"""

import io
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    KeepTogether,
    Image as RLImage,
    ListFlowable,
    ListItem,
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from flask import current_app

logger = logging.getLogger(__name__)


def sanitize_html_for_reportlab(html_text: str) -> str:
    """
    Sanitize HTML text to be compatible with ReportLab's limited HTML parser.
    
    ReportLab only supports a subset of HTML tags and has strict parsing rules.
    This function cleans up common issues:
    - Removes nested tags of the same type (e.g., <b><b>text</b></b>)
    - Fixes malformed br tags
    - Removes unsupported tags
    - Ensures proper tag closure
    """
    if not html_text:
        return ""
    
    # Remove multiple consecutive identical opening tags
    html_text = re.sub(r'(<([bi]|em|strong)>)\1+', r'\1', html_text)
    html_text = re.sub(r'(<(/[bi]|/em|/strong)>)\1+', r'\1', html_text)
    
    # Fix self-closing br tags - ReportLab expects <br/> or just <br>
    html_text = re.sub(r'<br\s*>', '<br/>', html_text)
    html_text = re.sub(r'<br\s*/?\s*>', '<br/>', html_text)
    
    # Remove content inside br tags (ReportLab error: "No content allowed in br tag")
    html_text = re.sub(r'<br[^>]*>[^<]*</br[^>]*>', '<br/>', html_text)
    
    # Convert some tags to ReportLab-supported equivalents
    html_text = re.sub(r'<strong>', '<b>', html_text)
    html_text = re.sub(r'</strong>', '</b>', html_text)
    html_text = re.sub(r'<em>', '<i>', html_text)
    html_text = re.sub(r'</em>', '</i>', html_text)
    
    # Remove unsupported HTML tags but keep their content
    # Keep only: b, i, br, u, sup, sub
    supported_tags = r'(?:/?(?:b|i|br|u|sup|sub)\b[^>]*)'
    html_text = re.sub(r'<(?!' + supported_tags + r')[^>]+>', '', html_text)
    
    # Fix broken tag nesting by removing orphaned closing tags
    # This is a simplified approach - for complex HTML, a proper parser would be better
    open_tags = []
    cleaned_parts = []
    
    # Simple state machine to track tag balance
    tag_pattern = r'<(/?)([a-zA-Z]+)[^>]*>'
    last_pos = 0
    
    for match in re.finditer(tag_pattern, html_text):
        # Add text before this tag
        cleaned_parts.append(html_text[last_pos:match.start()])
        
        is_closing = bool(match.group(1))
        tag_name = match.group(2).lower()
        full_tag = match.group(0)
        
        if tag_name in ['br']:
            # Self-closing tags
            cleaned_parts.append('<br/>')
        elif is_closing:
            if open_tags and open_tags[-1] == tag_name:
                open_tags.pop()
                cleaned_parts.append(full_tag)
            # Skip orphaned closing tags
        else:
            open_tags.append(tag_name)
            cleaned_parts.append(full_tag)
        
        last_pos = match.end()
    
    # Add remaining text
    cleaned_parts.append(html_text[last_pos:])
    
    # Close any remaining open tags
    while open_tags:
        tag = open_tags.pop()
        cleaned_parts.append(f'</{tag}>')
    
    result = ''.join(cleaned_parts)
    
    # Final cleanup - remove any double spaces or extra whitespace
    result = re.sub(r'\s+', ' ', result.strip())
    
    return result


class PageSize(Enum):
    """Supported page sizes for PDF generation"""
    LETTER = "letter"
    A4 = "a4"


class PDFTemplate(Enum):
    """Available PDF templates"""
    CLASSIC = "classic"
    MODERN = "modern"
    MINIMALIST = "minimalist"


@dataclass
class PDFConfig:
    """Configuration for PDF generation"""
    page_size: PageSize = PageSize.LETTER
    template: PDFTemplate = PDFTemplate.CLASSIC
    include_images: bool = True
    include_nutrition: bool = False
    include_notes: bool = True
    include_toc: bool = True  # Table of contents for cookbooks
    include_index: bool = False  # Ingredient index for cookbooks
    margins: Dict[str, float] = None
    
    def __post_init__(self):
        if self.margins is None:
            self.margins = {
                'top': 1 * inch,
                'bottom': 1 * inch,
                'left': 1 * inch,
                'right': 1 * inch
            }


class PDFStyleManager:
    """Manages styles for PDF generation"""
    
    def __init__(self, template: PDFTemplate = PDFTemplate.CLASSIC):
        self.template = template
        self.styles = getSampleStyleSheet()
        self._customize_styles()
    
    def _customize_styles(self):
        """Customize styles based on template"""
        if self.template == PDFTemplate.CLASSIC:
            self._apply_classic_styles()
        elif self.template == PDFTemplate.MODERN:
            self._apply_modern_styles()
        else:
            self._apply_minimalist_styles()
    
    def _apply_classic_styles(self):
        """Apply classic cookbook styling"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='RecipeTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='RecipeSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#7F8C8D'),
            spaceBefore=6,
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495E'),
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        # Ingredient style
        self.styles.add(ParagraphStyle(
            name='Ingredient',
            parent=self.styles['Normal'],
            fontSize=11,
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=2,
            spaceAfter=2
        ))
        
        # Instruction style
        self.styles.add(ParagraphStyle(
            name='Instruction',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=4,
            spaceAfter=4,
            alignment=TA_JUSTIFY
        ))
        
        # Metadata style
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#95A5A6'),
            alignment=TA_CENTER
        ))
    
    def _apply_modern_styles(self):
        """Apply modern, clean styling"""
        # To be implemented with artist input
        pass
    
    def _apply_minimalist_styles(self):
        """Apply minimalist styling"""
        # To be implemented with artist input
        pass


class PDFImageHandler:
    """Handles image processing for PDF generation"""
    
    @staticmethod
    def process_image(image_path: str, max_width: float = 4 * inch, 
                      max_height: float = 3 * inch) -> Optional[RLImage]:
        """Process and resize image for PDF inclusion"""
        try:
            if not image_path or not Path(image_path).exists():
                return None
            
            img = RLImage(image_path)
            
            # Calculate scaling to fit within max dimensions
            img_width = img.drawWidth
            img_height = img.drawHeight
            
            width_scale = max_width / img_width if img_width > max_width else 1
            height_scale = max_height / img_height if img_height > max_height else 1
            scale = min(width_scale, height_scale)
            
            if scale < 1:
                img.drawWidth *= scale
                img.drawHeight *= scale
            
            return img
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None
    
    @staticmethod
    def get_image_from_url(url: str, max_width: float = 4 * inch,
                          max_height: float = 3 * inch) -> Optional[RLImage]:
        """Download and process image from URL"""
        try:
            import requests
            from PIL import Image as PILImage
            import tempfile
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Save to temporary file (don't delete yet - ReportLab needs the file to exist)
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            
            # Process the image
            img = PDFImageHandler.process_image(tmp_path, max_width, max_height)
            
            # Store cleanup path in image object for later cleanup
            if img:
                img._temp_file_path = tmp_path
            else:
                # If image processing failed, clean up immediately
                Path(tmp_path).unlink(missing_ok=True)
            
            return img
            
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return None


class RecipePDFBuilder:
    """Builds PDF for individual recipes"""
    
    def __init__(self, config: PDFConfig = None):
        self.config = config or PDFConfig()
        self.style_manager = PDFStyleManager(self.config.template)
        self.image_handler = PDFImageHandler()
    
    def build_recipe_pdf(self, recipe: Dict[str, Any]) -> bytes:
        """Generate PDF for a single recipe"""
        buffer = io.BytesIO()
        
        # Determine page size
        page_size = letter if self.config.page_size == PageSize.LETTER else A4
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            topMargin=self.config.margins['top'],
            bottomMargin=self.config.margins['bottom'],
            leftMargin=self.config.margins['left'],
            rightMargin=self.config.margins['right']
        )
        
        # Build content
        story = []
        
        # Add recipe title
        story.append(Paragraph(
            recipe.get('title', 'Untitled Recipe'),
            self.style_manager.styles['RecipeTitle']
        ))
        
        # Add description if present
        if recipe.get('description'):
            story.append(Paragraph(
                sanitize_html_for_reportlab(recipe['description']),
                self.style_manager.styles['RecipeSubtitle']
            ))
        
        # Add metadata
        metadata_parts = []
        if recipe.get('prep_time'):
            metadata_parts.append(f"Prep: {recipe['prep_time']} min")
        if recipe.get('cook_time'):
            metadata_parts.append(f"Cook: {recipe['cook_time']} min")
        if recipe.get('servings'):
            metadata_parts.append(f"Servings: {recipe['servings']}")
        
        if metadata_parts:
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph(
                " • ".join(metadata_parts),
                self.style_manager.styles['Metadata']
            ))
        
        story.append(Spacer(1, 0.3 * inch))
        
        # Add main image if available and configured
        if self.config.include_images and recipe.get('images'):
            main_image = recipe['images'][0]
            img = None
            
            if main_image.get('cloudinary_url'):
                img = self.image_handler.get_image_from_url(main_image['cloudinary_url'])
            elif main_image.get('image_url'):
                img = self.image_handler.get_image_from_url(main_image['image_url'])
            
            if img:
                story.append(img)
                story.append(Spacer(1, 0.2 * inch))
        
        # Add ingredients section
        story.append(Paragraph('Ingredients', self.style_manager.styles['SectionHeader']))
        story.append(Spacer(1, 0.1 * inch))
        
        ingredients_list = []
        for ingredient in recipe.get('ingredients', []):
            if isinstance(ingredient, dict):
                ing_text = self._format_ingredient(ingredient)
            else:
                ing_text = str(ingredient)
            
            ingredients_list.append(
                ListItem(
                    Paragraph(ing_text, self.style_manager.styles['Ingredient']),
                    bulletType='bullet',
                    bulletColor=colors.HexColor('#34495E')
                )
            )
        
        if ingredients_list:
            story.append(ListFlowable(ingredients_list, bulletType='bullet'))
        
        story.append(Spacer(1, 0.3 * inch))
        
        # Add instructions section
        story.append(Paragraph('Instructions', self.style_manager.styles['SectionHeader']))
        story.append(Spacer(1, 0.1 * inch))
        
        instructions = recipe.get('instructions', [])
        for i, instruction in enumerate(instructions, 1):
            if isinstance(instruction, dict):
                inst_text = instruction.get('text', '')
            else:
                inst_text = str(instruction)
            
            story.append(Paragraph(
                f"{i}. {inst_text}",
                self.style_manager.styles['Instruction']
            ))
            story.append(Spacer(1, 0.1 * inch))
        
        # Add notes if configured and present
        if self.config.include_notes and recipe.get('notes'):
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph('Notes', self.style_manager.styles['SectionHeader']))
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(
                recipe['notes'],
                self.style_manager.styles['Normal']
            ))
        
        # Build PDF
        doc.build(story)
        
        # Clean up temporary image files
        self._cleanup_temp_images(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _cleanup_temp_images(self, story):
        """Clean up temporary image files created during PDF generation"""
        def cleanup_element(element):
            if hasattr(element, '_temp_file_path'):
                try:
                    Path(element._temp_file_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {element._temp_file_path}: {e}")
            
            # Handle nested elements (like tables, frames, etc.)
            if hasattr(element, '_contents') and element._contents:
                for content in element._contents:
                    cleanup_element(content)
            elif hasattr(element, 'contents') and element.contents:
                for content in element.contents:
                    cleanup_element(content)
        
        for element in story:
            cleanup_element(element)
    
    def _format_ingredient(self, ingredient: Dict[str, Any]) -> str:
        """Format ingredient dictionary into readable string"""
        parts = []
        
        if ingredient.get('quantity'):
            parts.append(str(ingredient['quantity']))
        
        if ingredient.get('unit'):
            parts.append(ingredient['unit'])
        
        parts.append(ingredient.get('name', ''))
        
        if ingredient.get('preparation'):
            parts.append(f", {ingredient['preparation']}")
        
        if ingredient.get('optional'):
            parts.append(" (optional)")
        
        return " ".join(parts)


class CookbookPDFBuilder:
    """Builds PDF for complete cookbooks"""
    
    def __init__(self, config: PDFConfig = None):
        self.config = config or PDFConfig()
        self.style_manager = PDFStyleManager(self.config.template)
        self.image_handler = PDFImageHandler()
        self.recipe_builder = RecipePDFBuilder(config)
    
    def build_cookbook_pdf(self, cookbook: Dict[str, Any], recipes: List[Dict[str, Any]]) -> bytes:
        """Generate PDF for a complete cookbook"""
        buffer = io.BytesIO()
        
        # Determine page size
        page_size = letter if self.config.page_size == PageSize.LETTER else A4
        
        # Create document with page numbering
        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            topMargin=self.config.margins['top'],
            bottomMargin=self.config.margins['bottom'],
            leftMargin=self.config.margins['left'],
            rightMargin=self.config.margins['right']
        )
        
        # Build content
        story = []
        
        # Add cover page
        story.extend(self._build_cover_page(cookbook))
        story.append(PageBreak())
        
        # Add table of contents if configured
        if self.config.include_toc and recipes:
            story.extend(self._build_table_of_contents(recipes))
            story.append(PageBreak())
        
        # Add recipes
        for i, recipe in enumerate(recipes):
            if i > 0:
                story.append(PageBreak())
            story.extend(self._build_recipe_section(recipe))
        
        # Add index if configured
        if self.config.include_index and recipes:
            story.append(PageBreak())
            story.extend(self._build_ingredient_index(recipes))
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        # Clean up temporary image files
        self._cleanup_temp_images(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _cleanup_temp_images(self, story):
        """Clean up temporary image files created during PDF generation"""
        def cleanup_element(element):
            if hasattr(element, '_temp_file_path'):
                try:
                    Path(element._temp_file_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {element._temp_file_path}: {e}")
            
            # Handle nested elements (like tables, frames, etc.)
            if hasattr(element, '_contents') and element._contents:
                for content in element._contents:
                    cleanup_element(content)
            elif hasattr(element, 'contents') and element.contents:
                for content in element.contents:
                    cleanup_element(content)
        
        for element in story:
            cleanup_element(element)
    
    def _build_cover_page(self, cookbook: Dict[str, Any]) -> List:
        """Build cookbook cover page"""
        elements = []
        
        # Add some spacing
        elements.append(Spacer(1, 2 * inch))
        
        # Title
        title_style = ParagraphStyle(
            'CoverTitle',
            parent=self.style_manager.styles['Title'],
            fontSize=36,
            textColor=colors.HexColor('#2C3E50'),
            alignment=TA_CENTER,
            spaceAfter=24
        )
        elements.append(Paragraph(
            cookbook.get('title', 'Cookbook'),
            title_style
        ))
        
        # Author
        if cookbook.get('author'):
            author_style = ParagraphStyle(
                'CoverAuthor',
                parent=self.style_manager.styles['Normal'],
                fontSize=18,
                textColor=colors.HexColor('#34495E'),
                alignment=TA_CENTER,
                spaceBefore=12,
                spaceAfter=24
            )
            elements.append(Paragraph(
                f"by {cookbook['author']}",
                author_style
            ))
        
        # Description
        if cookbook.get('description'):
            elements.append(Spacer(1, 0.5 * inch))
            desc_style = ParagraphStyle(
                'CoverDescription',
                parent=self.style_manager.styles['Normal'],
                fontSize=12,
                alignment=TA_CENTER,
                leftIndent=1 * inch,
                rightIndent=1 * inch
            )
            elements.append(Paragraph(
                sanitize_html_for_reportlab(cookbook['description']),
                desc_style
            ))
        
        # Publication info
        elements.append(Spacer(1, 2 * inch))
        
        pub_info = []
        if cookbook.get('publisher'):
            pub_info.append(cookbook['publisher'])
        if cookbook.get('publication_date'):
            pub_date = cookbook['publication_date']
            if isinstance(pub_date, str):
                pub_info.append(pub_date[:4])  # Just year
            else:
                pub_info.append(str(pub_date.year))
        
        if pub_info:
            pub_style = ParagraphStyle(
                'PublicationInfo',
                parent=self.style_manager.styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#7F8C8D'),
                alignment=TA_CENTER
            )
            elements.append(Paragraph(
                " • ".join(pub_info),
                pub_style
            ))
        
        return elements
    
    def _build_table_of_contents(self, recipes: List[Dict[str, Any]]) -> List:
        """Build table of contents"""
        elements = []
        
        # TOC Title
        toc_title_style = ParagraphStyle(
            'TOCTitle',
            parent=self.style_manager.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=24
        )
        elements.append(Paragraph('Table of Contents', toc_title_style))
        
        # Recipe entries
        toc_entry_style = ParagraphStyle(
            'TOCEntry',
            parent=self.style_manager.styles['Normal'],
            fontSize=11,
            leftIndent=0.5 * inch,
            spaceBefore=4,
            spaceAfter=4
        )
        
        for i, recipe in enumerate(recipes, 1):
            # Simple numbering for now - would need real page numbers in production
            entry = f"{i}. {recipe.get('title', 'Untitled Recipe')}"
            elements.append(Paragraph(entry, toc_entry_style))
        
        return elements
    
    def _build_recipe_section(self, recipe: Dict[str, Any]) -> List:
        """Build a recipe section for the cookbook"""
        elements = []
        
        # Use the same formatting as individual recipes
        # but return as elements list instead of full PDF
        
        # Recipe title
        elements.append(Paragraph(
            recipe.get('title', 'Untitled Recipe'),
            self.style_manager.styles['RecipeTitle']
        ))
        
        # Description
        if recipe.get('description'):
            elements.append(Paragraph(
                sanitize_html_for_reportlab(recipe['description']),
                self.style_manager.styles['RecipeSubtitle']
            ))
        
        # Metadata
        metadata_parts = []
        if recipe.get('prep_time'):
            metadata_parts.append(f"Prep: {recipe['prep_time']} min")
        if recipe.get('cook_time'):
            metadata_parts.append(f"Cook: {recipe['cook_time']} min")
        if recipe.get('servings'):
            metadata_parts.append(f"Servings: {recipe['servings']}")
        
        if metadata_parts:
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph(
                " • ".join(metadata_parts),
                self.style_manager.styles['Metadata']
            ))
        
        elements.append(Spacer(1, 0.3 * inch))
        
        # Ingredients
        elements.append(Paragraph('Ingredients', self.style_manager.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1 * inch))
        
        ingredients_list = []
        for ingredient in recipe.get('ingredients', []):
            if isinstance(ingredient, dict):
                ing_text = self.recipe_builder._format_ingredient(ingredient)
            else:
                ing_text = str(ingredient)
            
            ingredients_list.append(
                ListItem(
                    Paragraph(ing_text, self.style_manager.styles['Ingredient']),
                    bulletType='bullet'
                )
            )
        
        if ingredients_list:
            elements.append(ListFlowable(ingredients_list, bulletType='bullet'))
        
        elements.append(Spacer(1, 0.3 * inch))
        
        # Instructions
        elements.append(Paragraph('Instructions', self.style_manager.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1 * inch))
        
        for i, instruction in enumerate(recipe.get('instructions', []), 1):
            if isinstance(instruction, dict):
                inst_text = instruction.get('text', '')
            else:
                inst_text = str(instruction)
            
            elements.append(Paragraph(
                f"{i}. {inst_text}",
                self.style_manager.styles['Instruction']
            ))
            elements.append(Spacer(1, 0.1 * inch))
        
        return elements
    
    def _build_ingredient_index(self, recipes: List[Dict[str, Any]]) -> List:
        """Build ingredient index"""
        elements = []
        
        # Index title
        index_title_style = ParagraphStyle(
            'IndexTitle',
            parent=self.style_manager.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=24
        )
        elements.append(Paragraph('Ingredient Index', index_title_style))
        
        # Collect all ingredients
        ingredient_map = {}
        for i, recipe in enumerate(recipes):
            for ingredient in recipe.get('ingredients', []):
                if isinstance(ingredient, dict):
                    ing_name = ingredient.get('name', '').lower()
                else:
                    ing_name = str(ingredient).lower()
                
                if ing_name:
                    if ing_name not in ingredient_map:
                        ingredient_map[ing_name] = []
                    ingredient_map[ing_name].append(recipe.get('title', f'Recipe {i+1}'))
        
        # Sort and display
        index_entry_style = ParagraphStyle(
            'IndexEntry',
            parent=self.style_manager.styles['Normal'],
            fontSize=10,
            leftIndent=0.5 * inch
        )
        
        for ingredient in sorted(ingredient_map.keys()):
            recipes_list = ", ".join(ingredient_map[ingredient])
            entry = f"<b>{ingredient.title()}</b>: {recipes_list}"
            elements.append(Paragraph(entry, index_entry_style))
            elements.append(Spacer(1, 0.05 * inch))
        
        return elements
    
    def _add_page_number(self, canvas_obj, doc):
        """Add page numbers to the document"""
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.setFillColor(colors.HexColor('#7F8C8D'))
        
        # Get page size
        page_width = letter[0] if self.config.page_size == PageSize.LETTER else A4[0]
        
        # Add page number at bottom center
        page_num = canvas_obj.getPageNumber()
        text = f"Page {page_num}"
        canvas_obj.drawCentredString(page_width / 2, 0.5 * inch, text)
        
        canvas_obj.restoreState()


class PDFService:
    """Main service for PDF generation"""
    
    def __init__(self, config: PDFConfig = None):
        self.config = config or PDFConfig()
        self.recipe_builder = RecipePDFBuilder(self.config)
        self.cookbook_builder = CookbookPDFBuilder(self.config)
    
    def generate_recipe_pdf(self, recipe: Dict[str, Any], config: PDFConfig = None) -> bytes:
        """Generate PDF for a single recipe"""
        if config:
            self.recipe_builder.config = config
        
        return self.recipe_builder.build_recipe_pdf(recipe)
    
    def generate_cookbook_pdf(self, cookbook: Dict[str, Any], 
                            recipes: List[Dict[str, Any]], 
                            config: PDFConfig = None) -> bytes:
        """Generate PDF for a complete cookbook"""
        if config:
            self.cookbook_builder.config = config
        
        return self.cookbook_builder.build_cookbook_pdf(cookbook, recipes)
    
    def generate_recipe_collection_pdf(self, recipes: List[Dict[str, Any]], 
                                      title: str = "My Recipe Collection",
                                      config: PDFConfig = None) -> bytes:
        """Generate PDF for a collection of recipes"""
        # Create a virtual cookbook
        cookbook = {
            'title': title,
            'description': f"A collection of {len(recipes)} recipes",
            'author': 'Generated Collection'
        }
        
        return self.generate_cookbook_pdf(cookbook, recipes, config)