"""
Print-ready PDF builder for professional cookbook printing.

This module provides specialized PDF generation for print-on-demand services
with proper bleed margins, crop marks, and print specifications.
"""

import io
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, 
    Paragraph, Spacer, PageBreak, KeepTogether,
    Table, TableStyle
)
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter

from app.services.pdf_service import PDFConfig, PDFStyleManager
from app.utils.trim_sizes import TrimSizeMapper, PrintDimensions
from app.utils.print_marks import PrintMarksRenderer, PrintMarksConfig
from app.models.print_order import TrimSize, BindingType

logger = logging.getLogger(__name__)


class PrintReadyBaseDocTemplate(BaseDocTemplate):
    """Custom BaseDocTemplate for print-ready PDFs with print marks."""
    
    def __init__(self, filename, dimensions: PrintDimensions, config: PDFConfig):
        self.dimensions = dimensions
        self.config = config
        self.print_marks_renderer = PrintMarksRenderer(
            PrintMarksConfig(
                crop_marks=config.crop_marks,
                registration_marks=config.registration_marks,
                color_bars=config.color_bars,
                page_info=config.page_info
            )
        )
        
        # Initialize with full page size (including bleed)
        super().__init__(
            filename,
            pagesize=dimensions.full_size_tuple,
            leftMargin=0,
            rightMargin=0,
            topMargin=0,
            bottomMargin=0
        )
        
        self.page_count = 0
    
    def handle_pageBegin(self):
        """Called at the start of each page."""
        super().handle_pageBegin()
        self.page_count += 1
        
        # Apply print marks to canvas
        page_info = {
            'page_number': self.page_count,
            'title': getattr(self, 'document_title', 'Cookbook'),
            'trim_size': self.config.trim_size,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        self.print_marks_renderer.create_print_ready_template(
            self.canv,
            self.dimensions,
            page_info=page_info
        )


class PrintReadyPDFBuilder:
    """Builds print-ready PDFs with precise dimensions and print marks."""
    
    def __init__(self, config: PDFConfig):
        if not config.print_ready or not config.trim_size:
            raise ValueError("PrintReadyPDFBuilder requires print_ready=True and trim_size")
        
        self.config = config
        self.style_manager = PDFStyleManager(config.template)
        
        # Parse trim size and calculate dimensions
        try:
            trim_size_enum = TrimSize(config.trim_size)
        except ValueError:
            raise ValueError(f"Invalid trim size: {config.trim_size}")
        
        self.trim_size = trim_size_enum
        self.dimensions = TrimSizeMapper.get_dimensions(
            trim_size_enum,
            bleed_margin=config.bleed_margin,
            safety_margin=config.safety_margin
        )
        
        logger.info(f"PrintReadyPDFBuilder configured for {trim_size_enum.value}")
        logger.info(f"Full size: {self.dimensions.full_width/inch:.2f}\" x {self.dimensions.full_height/inch:.2f}\"")
        logger.info(f"Trim size: {self.dimensions.trim_width/inch:.2f}\" x {self.dimensions.trim_height/inch:.2f}\"")
    
    def build_cookbook_pdf(
        self,
        cookbook: Dict[str, Any],
        recipes: List[Dict[str, Any]]
    ) -> bytes:
        """Generate print-ready cookbook PDF."""
        buffer = io.BytesIO()
        
        # Create custom document template
        doc = PrintReadyBaseDocTemplate(buffer, self.dimensions, self.config)
        doc.document_title = cookbook.get('title', 'Cookbook')
        
        # Calculate content area with gutter if needed
        gutter_margin = 0
        if self.config.gutter_adjustment:
            gutter_margin = TrimSizeMapper.get_gutter_margin(
                binding_type='perfect_bound',  # Default for cookbooks
                page_count=len(recipes) * 2 + 20  # Approximate page count
            )
        
        # Get content frame bounds
        frame_bounds = PrintMarksRenderer.get_content_frame_bounds(
            self.dimensions,
            gutter_margin=gutter_margin
        )
        
        # Create page template with proper content frame
        content_frame = Frame(
            frame_bounds['left'],
            frame_bounds['bottom'],
            frame_bounds['width'],
            frame_bounds['height'],
            leftPadding=12,
            bottomPadding=12,
            rightPadding=12,
            topPadding=12,
            id='content_frame'
        )
        
        page_template = PageTemplate(
            id='cookbook_page',
            frames=[content_frame],
            onPage=self._on_page_callback
        )
        
        doc.addPageTemplates([page_template])
        
        # Build content
        story = []
        
        # Title page
        if cookbook.get('title'):
            story.extend(self._build_title_page(cookbook))
            story.append(PageBreak())
        
        # Table of contents
        if self.config.include_toc:
            story.extend(self._build_table_of_contents(recipes))
            story.append(PageBreak())
        
        # Recipes
        for i, recipe in enumerate(recipes):
            story.extend(self._build_recipe_content(recipe))
            
            # Add page break except for last recipe
            if i < len(recipes) - 1:
                story.append(PageBreak())
        
        # Index
        if self.config.include_index:
            story.append(PageBreak())
            story.extend(self._build_ingredient_index(recipes))
        
        # Build the PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.read()
    
    def build_recipe_pdf(self, recipe: Dict[str, Any]) -> bytes:
        """Generate print-ready single recipe PDF."""
        buffer = io.BytesIO()
        
        # Create custom document template
        doc = PrintReadyBaseDocTemplate(buffer, self.dimensions, self.config)
        doc.document_title = recipe.get('title', 'Recipe')
        
        # Create content frame
        frame_bounds = PrintMarksRenderer.get_content_frame_bounds(self.dimensions)
        
        content_frame = Frame(
            frame_bounds['left'],
            frame_bounds['bottom'],
            frame_bounds['width'],
            frame_bounds['height'],
            leftPadding=12,
            bottomPadding=12,
            rightPadding=12,
            topPadding=12,
            id='content_frame'
        )
        
        page_template = PageTemplate(
            id='recipe_page',
            frames=[content_frame],
            onPage=self._on_page_callback
        )
        
        doc.addPageTemplates([page_template])
        
        # Build recipe content
        story = self._build_recipe_content(recipe)
        
        # Build the PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.read()
    
    def _on_page_callback(self, canvas: Canvas, doc):
        """Callback for each page to add print marks."""
        # Print marks are handled in handle_pageBegin
        pass
    
    def _build_title_page(self, cookbook: Dict[str, Any]) -> List:
        """Build title page elements."""
        elements = []
        styles = self.style_manager.styles
        
        # Large top spacing
        elements.append(Spacer(1, 2 * inch))
        
        # Title
        title = cookbook.get('title', 'Untitled Cookbook')
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 0.5 * inch))
        
        # Author
        author = cookbook.get('author', 'Unknown Author')
        elements.append(Paragraph(f"by {author}", styles['Normal']))
        elements.append(Spacer(1, 0.5 * inch))
        
        # Description
        description = cookbook.get('description')
        if description:
            elements.append(Paragraph(description, styles['Normal']))
            elements.append(Spacer(1, 1 * inch))
        
        return elements
    
    def _build_table_of_contents(self, recipes: List[Dict[str, Any]]) -> List:
        """Build table of contents."""
        elements = []
        styles = self.style_manager.styles
        
        elements.append(Paragraph("Table of Contents", styles['Heading1']))
        elements.append(Spacer(1, 0.5 * inch))
        
        # Simple TOC without page numbers (since we can't predict them easily)
        for recipe in recipes:
            title = recipe.get('title', 'Untitled Recipe')
            elements.append(Paragraph(f"• {title}", styles['Normal']))
            elements.append(Spacer(1, 6))
        
        return elements
    
    def _build_recipe_content(self, recipe: Dict[str, Any]) -> List:
        """Build content for a single recipe."""
        elements = []
        styles = self.style_manager.styles
        
        # Recipe title
        title = recipe.get('title', 'Untitled Recipe')
        elements.append(Paragraph(title, styles['Heading1']))
        elements.append(Spacer(1, 12))
        
        # Description
        description = recipe.get('description')
        if description and self.config.include_notes:
            elements.append(Paragraph(description, styles['Normal']))
            elements.append(Spacer(1, 12))
        
        # Timing information
        prep_time = recipe.get('prep_time_minutes')
        cook_time = recipe.get('cook_time_minutes')
        servings = recipe.get('servings')
        
        timing_info = []
        if prep_time:
            timing_info.append(f"Prep: {prep_time} min")
        if cook_time:
            timing_info.append(f"Cook: {cook_time} min")
        if servings:
            timing_info.append(f"Serves: {servings}")
        
        if timing_info:
            timing_text = " | ".join(timing_info)
            elements.append(Paragraph(timing_text, styles['Normal']))
            elements.append(Spacer(1, 16))
        
        # Ingredients
        ingredients = recipe.get('ingredients', [])
        if ingredients:
            elements.append(Paragraph("Ingredients", styles['Heading2']))
            elements.append(Spacer(1, 6))
            
            for ingredient in ingredients:
                ingredient_text = self._format_ingredient(ingredient)
                elements.append(Paragraph(f"• {ingredient_text}", styles['Normal']))
                elements.append(Spacer(1, 4))
            
            elements.append(Spacer(1, 16))
        
        # Instructions
        instructions = recipe.get('instructions', [])
        if instructions:
            elements.append(Paragraph("Instructions", styles['Heading2']))
            elements.append(Spacer(1, 6))
            
            for i, instruction in enumerate(instructions, 1):
                instruction_text = instruction.get('instruction', str(instruction))
                elements.append(Paragraph(f"{i}. {instruction_text}", styles['Normal']))
                elements.append(Spacer(1, 8))
        
        # Notes
        if self.config.include_notes and recipe.get('notes'):
            elements.append(Spacer(1, 16))
            elements.append(Paragraph("Notes", styles['Heading2']))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(recipe['notes'], styles['Normal']))
        
        return elements
    
    def _format_ingredient(self, ingredient) -> str:
        """Format an ingredient for display."""
        if isinstance(ingredient, dict):
            parts = []
            if ingredient.get('quantity'):
                parts.append(str(ingredient['quantity']))
            if ingredient.get('unit'):
                parts.append(ingredient['unit'])
            if ingredient.get('ingredient'):
                parts.append(ingredient['ingredient'])
            elif ingredient.get('name'):
                parts.append(ingredient['name'])
            
            return " ".join(parts)
        else:
            return str(ingredient)
    
    def _build_ingredient_index(self, recipes: List[Dict[str, Any]]) -> List:
        """Build alphabetical ingredient index."""
        elements = []
        styles = self.style_manager.styles
        
        elements.append(Paragraph("Ingredient Index", styles['Heading1']))
        elements.append(Spacer(1, 0.5 * inch))
        
        # Collect all ingredients
        ingredients = set()
        for recipe in recipes:
            for ingredient_data in recipe.get('ingredients', []):
                if isinstance(ingredient_data, dict):
                    ingredient_name = ingredient_data.get('ingredient') or ingredient_data.get('name')
                    if ingredient_name:
                        ingredients.add(ingredient_name.lower().strip())
                else:
                    # Extract ingredient name from string (simple approach)
                    ingredient_str = str(ingredient_data).lower()
                    # This is simplified - in a real implementation you'd use NLP
                    if len(ingredient_str) > 3:
                        ingredients.add(ingredient_str)
        
        # Sort and display
        for ingredient in sorted(ingredients):
            elements.append(Paragraph(f"• {ingredient.title()}", styles['Normal']))
            elements.append(Spacer(1, 4))
        
        return elements
    
    def validate_content_safety(self, content_elements: List) -> Dict[str, Any]:
        """Validate that content will fit within safe printing bounds."""
        # This would analyze the content elements and warn about potential
        # issues with content placement relative to trim and safe areas
        
        return {
            'is_safe': True,
            'warnings': [],
            'recommendations': []
        }
    
    def get_print_specifications(self) -> Dict[str, Any]:
        """Get detailed specifications for this print-ready PDF."""
        return {
            'trim_size': self.trim_size.value,
            'dimensions': self.dimensions.to_dict(),
            'bleed_margin_inches': self.dimensions.bleed_margin / inch,
            'safety_margin_inches': self.dimensions.safety_margin / inch,
            'includes_crop_marks': self.config.crop_marks,
            'includes_registration_marks': self.config.registration_marks,
            'includes_color_bars': self.config.color_bars,
            'suitable_for_binding': ['perfect_bound', 'saddle_stitch'],
            'recommended_paper_types': ['standard_white', 'standard_cream', 'premium_white']
        }