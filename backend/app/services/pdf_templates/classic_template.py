"""Classic PDF Template for Cookbooks

A traditional, professional cookbook template with clean typography.
"""

from typing import Dict, Any
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import inch

from .base_template import BasePDFTemplate, TemplateColors, TemplateFonts


class ClassicPDFTemplate(BasePDFTemplate):
    """Classic cookbook template with traditional styling"""
    
    def get_colors(self) -> TemplateColors:
        """Classic color scheme - professional and readable"""
        return TemplateColors(
            primary='#2C3E50',      # Dark blue-gray for titles
            secondary='#34495E',     # Slightly lighter for headers
            accent='#E74C3C',        # Warm red for accents
            text='#2C3E50',         # Main text color
            text_light='#7F8C8D',   # Light gray for metadata
            background='#FFFFFF'     # White background
        )
    
    def get_fonts(self) -> TemplateFonts:
        """Classic font selection"""
        return TemplateFonts(
            title='Helvetica-Bold',
            heading='Helvetica-Bold',
            body='Helvetica',
            body_italic='Helvetica-Oblique',
            monospace='Courier'
        )
    
    def get_title_style(self) -> ParagraphStyle:
        """Recipe title style"""
        return ParagraphStyle(
            name='RecipeTitle',
            fontName=self.fonts.title,
            fontSize=24,
            textColor=colors.HexColor(self.colors.primary),
            alignment=TA_CENTER,
            spaceAfter=12,
            spaceBefore=0
        )
    
    def get_subtitle_style(self) -> ParagraphStyle:
        """Recipe subtitle/description style"""
        return ParagraphStyle(
            name='RecipeSubtitle',
            fontName=self.fonts.body_italic,
            fontSize=14,
            textColor=colors.HexColor(self.colors.text_light),
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=12
        )
    
    def get_section_header_style(self) -> ParagraphStyle:
        """Section header style (Ingredients, Instructions)"""
        return ParagraphStyle(
            name='SectionHeader',
            fontName=self.fonts.heading,
            fontSize=16,
            textColor=colors.HexColor(self.colors.secondary),
            alignment=TA_LEFT,
            spaceBefore=12,
            spaceAfter=6
        )
    
    def get_ingredient_style(self) -> ParagraphStyle:
        """Ingredient list item style"""
        return ParagraphStyle(
            name='Ingredient',
            fontName=self.fonts.body,
            fontSize=11,
            textColor=colors.HexColor(self.colors.text),
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=2,
            spaceAfter=2
        )
    
    def get_instruction_style(self) -> ParagraphStyle:
        """Instruction step style"""
        return ParagraphStyle(
            name='Instruction',
            fontName=self.fonts.body,
            fontSize=11,
            textColor=colors.HexColor(self.colors.text),
            alignment=TA_JUSTIFY,
            spaceBefore=4,
            spaceAfter=4
        )
    
    def get_metadata_style(self) -> ParagraphStyle:
        """Metadata style (prep time, servings, etc.)"""
        return ParagraphStyle(
            name='Metadata',
            fontName=self.fonts.body,
            fontSize=10,
            textColor=colors.HexColor(self.colors.text_light),
            alignment=TA_CENTER,
            spaceBefore=3,
            spaceAfter=3
        )
    
    def get_cover_title_style(self) -> ParagraphStyle:
        """Cookbook cover title style"""
        return ParagraphStyle(
            name='CoverTitle',
            fontName=self.fonts.title,
            fontSize=36,
            textColor=colors.HexColor(self.colors.primary),
            alignment=TA_CENTER,
            spaceAfter=24
        )
    
    def get_cover_author_style(self) -> ParagraphStyle:
        """Cookbook cover author style"""
        return ParagraphStyle(
            name='CoverAuthor',
            fontName=self.fonts.body,
            fontSize=18,
            textColor=colors.HexColor(self.colors.secondary),
            alignment=TA_CENTER,
            spaceBefore=12,
            spaceAfter=24
        )
    
    def get_toc_title_style(self) -> ParagraphStyle:
        """Table of contents title style"""
        return ParagraphStyle(
            name='TOCTitle',
            fontName=self.fonts.title,
            fontSize=24,
            textColor=colors.HexColor(self.colors.primary),
            alignment=TA_CENTER,
            spaceAfter=24
        )
    
    def get_toc_entry_style(self) -> ParagraphStyle:
        """Table of contents entry style"""
        return ParagraphStyle(
            name='TOCEntry',
            fontName=self.fonts.body,
            fontSize=11,
            textColor=colors.HexColor(self.colors.text),
            leftIndent=0.5 * inch,
            spaceBefore=4,
            spaceAfter=4
        )
    
    def get_index_title_style(self) -> ParagraphStyle:
        """Index title style"""
        return ParagraphStyle(
            name='IndexTitle',
            fontName=self.fonts.title,
            fontSize=24,
            textColor=colors.HexColor(self.colors.primary),
            alignment=TA_CENTER,
            spaceAfter=24
        )
    
    def get_index_entry_style(self) -> ParagraphStyle:
        """Index entry style"""
        return ParagraphStyle(
            name='IndexEntry',
            fontName=self.fonts.body,
            fontSize=10,
            textColor=colors.HexColor(self.colors.text),
            leftIndent=0.5 * inch,
            spaceBefore=2,
            spaceAfter=2
        )
    
    def get_page_number_style(self) -> Dict[str, Any]:
        """Page number styling"""
        return {
            'font': 'Helvetica',
            'size': 9,
            'color': colors.HexColor(self.colors.text_light)
        }
    
    def get_notes_style(self) -> ParagraphStyle:
        """Notes section style"""
        return ParagraphStyle(
            name='Notes',
            fontName=self.fonts.body,
            fontSize=10,
            textColor=colors.HexColor(self.colors.text),
            alignment=TA_LEFT,
            spaceBefore=3,
            spaceAfter=3,
            leftIndent=10
        )