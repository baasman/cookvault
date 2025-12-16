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
    Frame,
    PageTemplate,
    BaseDocTemplate,
    FrameBreak,
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY, TA_LEFT
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
    BOOK = "book"


class OutputProfile(Enum):
    """Output profiles for different use cases"""
    DIGITAL = "digital"  # Optimized for screen viewing
    HOME_PRINT = "home_print"  # Optimized for home printers
    PROFESSIONAL_PRINT = "professional_print"  # Print-ready with CMYK


@dataclass
class PDFConfig:
    """Configuration for PDF generation"""
    page_size: PageSize = PageSize.LETTER
    template: PDFTemplate = PDFTemplate.CLASSIC
    profile: OutputProfile = OutputProfile.DIGITAL  # Output profile for different use cases
    include_images: bool = True
    include_nutrition: bool = False
    include_notes: bool = True
    include_toc: bool = True  # Table of contents for cookbooks
    include_index: bool = False  # Ingredient index for cookbooks
    margins: Dict[str, float] = None

    # Image quality settings (profile-specific defaults)
    image_quality: int = 85  # JPEG quality (0-100)
    color_mode: str = 'RGB'  # 'RGB' or 'CMYK'

    # Print-ready options
    print_ready: bool = False  # Enable print-ready features
    trim_size: Optional[str] = None  # TrimSize enum value for print orders
    bleed_margin: float = 0.125 * inch  # Standard 1/8 inch bleed
    safety_margin: float = 0.25 * inch  # Safety margin inside trim
    crop_marks: bool = False  # Add corner crop marks
    registration_marks: bool = False  # Add registration marks for color alignment
    color_bars: bool = False  # Add color bars for print quality control
    page_info: bool = False  # Add page information text
    include_spine_calculation: bool = False  # Calculate spine width for binding
    gutter_adjustment: bool = False  # Add extra margin for binding gutter
    
    def __post_init__(self):
        # Apply profile-specific settings
        self._apply_profile_settings()

        if self.margins is None:
            if self.print_ready:
                # For print-ready PDFs, use minimal base margins
                # Actual safe margins will be calculated by PrintReadyPDFBuilder
                self.margins = {
                    'top': 0.5 * inch,
                    'bottom': 0.5 * inch,
                    'left': 0.5 * inch,
                    'right': 0.5 * inch
                }
            elif self.profile == OutputProfile.HOME_PRINT:
                # Home print profile: smaller margins for standard printers
                self.margins = {
                    'top': 0.5 * inch,
                    'bottom': 0.5 * inch,
                    'left': 0.5 * inch,
                    'right': 0.5 * inch
                }
            else:
                # Standard margins for digital viewing
                self.margins = {
                    'top': 1 * inch,
                    'bottom': 1 * inch,
                    'left': 1 * inch,
                    'right': 1 * inch
                }

    def _apply_profile_settings(self):
        """Apply settings based on output profile"""
        if self.profile == OutputProfile.DIGITAL:
            # Digital viewing: smaller file size, RGB, lower quality
            self.image_quality = 85
            self.color_mode = 'RGB'
            self.print_ready = False

        elif self.profile == OutputProfile.HOME_PRINT:
            # Home printing: higher quality, RGB, no bleed
            self.image_quality = 90
            self.color_mode = 'RGB'
            self.print_ready = False

        elif self.profile == OutputProfile.PROFESSIONAL_PRINT:
            # Professional printing: highest quality, CMYK, print marks
            self.image_quality = 95
            self.color_mode = 'CMYK'
            self.print_ready = True
            self.crop_marks = True
            self.bleed_margin = 0.125 * inch  # Standard 1/8" bleed
    
    def enable_print_ready_mode(
        self,
        trim_size: str,
        include_marks: bool = True,
        bleed_margin: float = None,
        safety_margin: float = None
    ) -> 'PDFConfig':
        """
        Configure for print-ready output with specified trim size.
        
        Args:
            trim_size: TrimSize enum value (e.g., 'US_TRADE')
            include_marks: Whether to include crop marks and registration marks
            bleed_margin: Custom bleed margin (defaults to 1/8 inch)
            safety_margin: Custom safety margin (defaults to 1/4 inch)
            
        Returns:
            Self for method chaining
        """
        self.print_ready = True
        self.trim_size = trim_size
        
        if bleed_margin is not None:
            self.bleed_margin = bleed_margin
        if safety_margin is not None:
            self.safety_margin = safety_margin
            
        if include_marks:
            self.crop_marks = True
            self.registration_marks = True
            self.page_info = True
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'page_size': self.page_size.value,
            'template': self.template.value,
            'include_images': self.include_images,
            'include_nutrition': self.include_nutrition,
            'include_notes': self.include_notes,
            'include_toc': self.include_toc,
            'include_index': self.include_index,
            'margins': self.margins.copy(),
            'print_ready': self.print_ready,
            'trim_size': self.trim_size,
            'bleed_margin': self.bleed_margin,
            'safety_margin': self.safety_margin,
            'crop_marks': self.crop_marks,
            'registration_marks': self.registration_marks,
            'color_bars': self.color_bars,
            'page_info': self.page_info,
            'include_spine_calculation': self.include_spine_calculation,
            'gutter_adjustment': self.gutter_adjustment
        }


class PDFStyleManager:
    """Manages styles for PDF generation"""
    
    def __init__(self, template: PDFTemplate = PDFTemplate.CLASSIC):
        self.template = template
        self.styles = getSampleStyleSheet()
        self._register_fonts()
        self._customize_styles()
    
    def _register_fonts(self):
        """Register custom fonts for PDF generation"""
        try:
            fonts_dir = Path(__file__).parent / 'fonts'

            # Register Inter (sans-serif) - primary font for modern design
            if (fonts_dir / 'Inter-Regular.ttf').exists():
                pdfmetrics.registerFont(TTFont('Inter', str(fonts_dir / 'Inter-Regular.ttf')))
                pdfmetrics.registerFont(TTFont('Inter-Medium', str(fonts_dir / 'Inter-Medium.ttf')))
                pdfmetrics.registerFont(TTFont('Inter-SemiBold', str(fonts_dir / 'Inter-SemiBold.ttf')))
                pdfmetrics.registerFont(TTFont('Inter-Bold', str(fonts_dir / 'Inter-Bold.ttf')))

                # Register font family with proper weight mappings
                pdfmetrics.registerFontFamily(
                    'Inter',
                    normal='Inter',
                    bold='Inter-Bold',
                    italic='Inter',  # Using regular as italic fallback
                    boldItalic='Inter-Bold'
                )
                logger.info("✓ Registered Inter font family (sans-serif)")

            # Register Lora (serif) - accent font for titles
            if (fonts_dir / 'Lora-Regular.ttf').exists():
                pdfmetrics.registerFont(TTFont('Lora', str(fonts_dir / 'Lora-Regular.ttf')))
                pdfmetrics.registerFont(TTFont('Lora-Bold', str(fonts_dir / 'Lora-Bold.ttf')))

                pdfmetrics.registerFontFamily(
                    'Lora',
                    normal='Lora',
                    bold='Lora-Bold',
                    italic='Lora',
                    boldItalic='Lora-Bold'
                )
                logger.info("✓ Registered Lora font family (serif)")

            # Register JetBrains Mono (monospace) - for measurements/times
            if (fonts_dir / 'JetBrainsMono-Regular.ttf').exists():
                pdfmetrics.registerFont(TTFont('JetBrainsMono', str(fonts_dir / 'JetBrainsMono-Regular.ttf')))
                pdfmetrics.registerFont(TTFont('JetBrainsMono-Medium', str(fonts_dir / 'JetBrainsMono-Medium.ttf')))

                pdfmetrics.registerFontFamily(
                    'JetBrainsMono',
                    normal='JetBrainsMono',
                    bold='JetBrainsMono-Medium',
                    italic='JetBrainsMono',
                    boldItalic='JetBrainsMono-Medium'
                )
                logger.info("✓ Registered JetBrains Mono font family (monospace)")

            # Store font availability for fallback logic
            self.fonts_available = {
                'inter': (fonts_dir / 'Inter-Regular.ttf').exists(),
                'lora': (fonts_dir / 'Lora-Regular.ttf').exists(),
                'jetbrains': (fonts_dir / 'JetBrainsMono-Regular.ttf').exists()
            }

        except Exception as e:
            logger.warning(f"Failed to register custom fonts: {e}. Using system fonts.")
            self.fonts_available = {'inter': False, 'lora': False, 'jetbrains': False}
    
    def _customize_styles(self):
        """Customize styles based on template"""
        if self.template == PDFTemplate.CLASSIC:
            self._apply_classic_styles()
        elif self.template == PDFTemplate.MODERN:
            self._apply_modern_styles()
        elif self.template == PDFTemplate.BOOK:
            self._apply_book_styles()
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
        """Apply modern minimalist styling with professional typography"""
        # Modern Minimalist Color Palette
        primary_text = colors.HexColor('#2B2D42')      # Charcoal - main text
        secondary_text = colors.HexColor('#8D99AE')    # Warm gray - metadata
        accent_color = colors.HexColor('#EF8354')      # Muted coral - accents
        bg_color = colors.HexColor('#FAF9F6')          # Off-white - backgrounds
        divider_color = colors.HexColor('#EDF2F4')     # Light gray - dividers

        # Font fallbacks: Use custom fonts if available, else Helvetica
        serif_font = 'Lora' if self.fonts_available.get('lora') else 'Helvetica'
        serif_bold = 'Lora-Bold' if self.fonts_available.get('lora') else 'Helvetica-Bold'
        sans_font = 'Inter' if self.fonts_available.get('inter') else 'Helvetica'
        sans_medium = 'Inter-Medium' if self.fonts_available.get('inter') else 'Helvetica-Bold'
        sans_semibold = 'Inter-SemiBold' if self.fonts_available.get('inter') else 'Helvetica-Bold'
        sans_bold = 'Inter-Bold' if self.fonts_available.get('inter') else 'Helvetica-Bold'
        mono_font = 'JetBrainsMono' if self.fonts_available.get('jetbrains') else 'Courier'

        # Level 1: Cookbook Title (48pt serif, bold)
        self.styles.add(ParagraphStyle(
            name='CookbookTitle',
            parent=self.styles['Title'],
            fontSize=48,
            textColor=primary_text,
            spaceAfter=24,
            spaceBefore=0,
            alignment=TA_CENTER,
            fontName=serif_bold,
            leading=54  # 1.125x line height
        ))

        # Level 2: Recipe Title (32pt serif, semibold)
        self.styles.add(ParagraphStyle(
            name='RecipeTitle',
            parent=self.styles['Heading1'],
            fontSize=32,
            textColor=primary_text,
            spaceAfter=12,
            spaceBefore=0,
            alignment=TA_LEFT,
            fontName=serif_bold,
            leading=38  # 1.19x line height
        ))

        # Subtitle for recipes (used for description)
        self.styles.add(ParagraphStyle(
            name='RecipeSubtitle',
            parent=self.styles['Normal'],
            fontSize=13,
            textColor=secondary_text,
            spaceBefore=6,
            spaceAfter=18,
            alignment=TA_LEFT,
            fontName=sans_font,
            leading=18  # 1.4x line height
        ))

        # Level 3: Section Headers (18pt sans-serif bold)
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=primary_text,
            spaceBefore=24,
            spaceAfter=12,
            fontName=sans_bold,
            leading=22  # 1.2x line height
        ))

        # Level 4: Body Text (11pt sans-serif regular)
        self.styles.add(ParagraphStyle(
            name='ModernBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=primary_text,
            spaceBefore=0,
            spaceAfter=6,
            fontName=sans_font,
            leading=15  # 1.4x line height
        ))

        # Ingredients (11pt sans-serif, with custom bullet)
        self.styles.add(ParagraphStyle(
            name='Ingredient',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=primary_text,
            leftIndent=0,
            bulletIndent=0,
            spaceBefore=3,
            spaceAfter=3,
            fontName=sans_font,
            leading=15
        ))

        # Instructions (11pt sans-serif, justified)
        self.styles.add(ParagraphStyle(
            name='Instruction',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=primary_text,
            spaceBefore=6,
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName=sans_font,
            leading=16  # Slightly more generous for readability
        ))

        # Instruction number style (accent color)
        self.styles.add(ParagraphStyle(
            name='InstructionNumber',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=accent_color,
            fontName=sans_bold,
            leading=16
        ))

        # Level 5: Metadata (9pt sans-serif light)
        # Use 'Metadata' name for consistency with other templates
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=secondary_text,
            alignment=TA_LEFT,
            fontName=sans_font,
            spaceBefore=2,
            spaceAfter=2
        ))

        # Metadata with monospace for measurements/times
        self.styles.add(ParagraphStyle(
            name='MetadataMono',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=secondary_text,
            fontName=mono_font
        ))

        # Notes/Tips box style
        self.styles.add(ParagraphStyle(
            name='NoteText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=primary_text,
            fontName=sans_font,
            leading=14,
            spaceBefore=6,
            spaceAfter=6
        ))

        # Caption style for images
        self.styles.add(ParagraphStyle(
            name='ImageCaption',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=secondary_text,
            alignment=TA_CENTER,
            fontName=sans_font,
            spaceBefore=4,
            spaceAfter=12
        ))

        # Store colors for use in builders
        self.modern_colors = {
            'primary': primary_text,
            'secondary': secondary_text,
            'accent': accent_color,
            'background': bg_color,
            'divider': divider_color
        }

        # Define spacing constants for consistent white space management
        self.spacing = {
            'SMALL': 6,      # 6pt - Tight spacing for list items
            'MEDIUM': 12,    # 12pt - Standard paragraph spacing
            'LARGE': 24,     # 24pt - Section spacing
            'XLARGE': 36,    # 36pt - Major section breaks
            'XXLARGE': 48    # 48pt - Chapter/category breaks
        }

    @staticmethod
    def rgb_to_cmyk(r: int, g: int, b: int) -> tuple[float, float, float, float]:
        """
        Convert RGB (0-255) to CMYK (0-1) for professional print output.

        Args:
            r, g, b: RGB values in range 0-255

        Returns:
            tuple of (c, m, y, k) in range 0-1

        Note: This is a basic conversion. For production printing, consider using
        ICC color profiles for more accurate color matching.
        """
        # Normalize RGB to 0-1 range
        r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0

        # Calculate key (black)
        k = 1 - max(r_norm, g_norm, b_norm)

        # Handle pure black case
        if k == 1:
            return 0.0, 0.0, 0.0, 1.0

        # Calculate CMY
        c = (1 - r_norm - k) / (1 - k)
        m = (1 - g_norm - k) / (1 - k)
        y = (1 - b_norm - k) / (1 - k)

        return c, m, y, k

    @staticmethod
    def apply_opacity(color: colors.Color, opacity: float) -> colors.Color:
        """
        Create a semi-transparent version of a color.

        Args:
            color: ReportLab Color object
            opacity: Alpha value (0.0 = fully transparent, 1.0 = fully opaque)

        Returns:
            New Color object with alpha channel

        Note: Requires PDF transparency support. For cover overlays, 0.3-0.4 opacity works well.
        """
        if opacity < 0.0 or opacity > 1.0:
            raise ValueError(f"Opacity must be between 0.0 and 1.0, got {opacity}")

        # Extract RGB components
        if hasattr(color, 'red') and hasattr(color, 'green') and hasattr(color, 'blue'):
            return colors.Color(color.red, color.green, color.blue, alpha=opacity)
        else:
            # Fallback for color formats without RGB attributes
            return color

    def get_color_for_profile(
        self,
        color_rgb: tuple[int, int, int],
        profile: str = 'digital'
    ) -> colors.Color:
        """
        Return appropriate color format based on output profile.

        Args:
            color_rgb: RGB color as tuple (r, g, b) in range 0-255
            profile: Output profile ('digital', 'home_print', 'professional_print')

        Returns:
            Color object in appropriate format (RGB or CMYK)
        """
        r, g, b = color_rgb

        if profile == 'professional_print':
            # Convert to CMYK for professional printing
            c, m, y, k = self.rgb_to_cmyk(r, g, b)
            return colors.CMYKColor(c, m, y, k)
        else:
            # Use RGB for digital and home print
            return colors.Color(r / 255.0, g / 255.0, b / 255.0)

    def create_divider_line(
        self,
        width: str = "30%",
        thickness: float = 0.5,
        color: colors.Color = None,
        space_before: int = 12,
        space_after: int = 12
    ):
        """
        Create an elegant horizontal divider line.

        Args:
            width: Line width (can be percentage like "30%" or absolute like "4*inch")
            thickness: Line thickness in points (default 0.5pt for subtle effect)
            color: Line color (defaults to divider color from modern palette)
            space_before: Spacing before the line in points
            space_after: Spacing after the line in points

        Returns:
            HRFlowable object for use in story
        """
        from reportlab.platypus import HRFlowable

        if color is None:
            color = self.modern_colors.get('divider', colors.HexColor('#EDF2F4'))

        return HRFlowable(
            width=width,
            thickness=thickness,
            color=color,
            spaceBefore=space_before,
            spaceAfter=space_after,
            hAlign='CENTER'
        )

    def create_framed_box(
        self,
        content_elements: list,
        padding: int = 12,
        border_color: colors.Color = None,
        border_width: float = 0.5,
        background_color: colors.Color = None
    ):
        """
        Create a framed box for notes, tips, or variations.

        Args:
            content_elements: List of Flowable elements to include in the box
            padding: Internal padding in points
            border_color: Border color (defaults to divider color)
            border_width: Border thickness in points
            background_color: Optional background color (None for transparent)

        Returns:
            KeepTogether flowable containing a Table with the framed content
        """
        from reportlab.platypus import Table, TableStyle, KeepTogether, Spacer

        if border_color is None:
            border_color = self.modern_colors.get('divider', colors.HexColor('#EDF2F4'))

        # Create table style for the frame
        table_style = [
            ('BOX', (0, 0), (-1, -1), border_width, border_color),
            ('LEFTPADDING', (0, 0), (-1, -1), padding),
            ('RIGHTPADDING', (0, 0), (-1, -1), padding),
            ('TOPPADDING', (0, 0), (-1, -1), padding),
            ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]

        if background_color:
            table_style.insert(0, ('BACKGROUND', (0, 0), (-1, -1), background_color))

        # Wrap content in table for framing
        table = Table([[content_elements]], colWidths=[None])
        table.setStyle(TableStyle(table_style))

        # Keep together to avoid page breaks within the box
        return KeepTogether([table])

    def create_pull_quote(
        self,
        quote_text: str,
        author: str = None,
        style_name: str = None
    ):
        """
        Create a pull quote for chef's notes or special highlights.

        Args:
            quote_text: The quote text
            author: Optional author attribution
            style_name: Style to use (defaults to appropriate modern style)

        Returns:
            List of Flowable elements (quote + optional attribution)
        """
        from reportlab.platypus import Paragraph, Spacer

        if style_name is None:
            # Use NoteText style if available, otherwise create inline
            if 'NoteText' in self.styles:
                quote_style = self.styles['NoteText']
            else:
                # Fallback inline style
                quote_style = ParagraphStyle(
                    'PullQuote',
                    parent=self.styles['Normal'],
                    fontSize=11,
                    textColor=self.modern_colors.get('secondary', colors.HexColor('#8D99AE')),
                    leftIndent=24,
                    rightIndent=24,
                    spaceBefore=12,
                    spaceAfter=6,
                    leading=16
                )
        else:
            quote_style = self.styles.get(style_name, self.styles['Normal'])

        elements = []

        # Add the quote with subtle italic emphasis
        quote_para = Paragraph(f'<i>"{quote_text}"</i>', quote_style)
        elements.append(quote_para)

        # Add author attribution if provided
        if author:
            author_style = ParagraphStyle(
                'QuoteAuthor',
                parent=self.styles['Normal'],
                fontSize=9,
                textColor=self.modern_colors.get('secondary', colors.HexColor('#8D99AE')),
                leftIndent=24,
                rightIndent=24,
                alignment=TA_RIGHT,
                spaceAfter=12
            )
            author_para = Paragraph(f'— {author}', author_style)
            elements.append(author_para)

        return elements

    def _apply_minimalist_styles(self):
        """Apply minimalist styling"""
        # Basic minimalist styles until full implementation with artist input
        self.styles.add(ParagraphStyle(
            name='RecipeTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            textColor=colors.black,
            spaceAfter=8,
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='RecipeSubtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#808080'),
            spaceBefore=4,
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.black,
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='Ingredient',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=0,
            bulletIndent=0,
            spaceBefore=2,
            spaceAfter=2
        ))
        
        self.styles.add(ParagraphStyle(
            name='Instruction',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=4,
            spaceAfter=4,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#A0A0A0'),
            alignment=TA_LEFT
        ))
    
    def _apply_book_styles(self):
        """Apply elegant book-style formatting inspired by professional cookbooks"""
        # Determine if custom fonts are available by checking registered fonts
        registered_fonts = list(pdfmetrics._fonts.keys())
        
        serif_font = 'CormorantGaramond' if 'CormorantGaramond' in registered_fonts else 'Times-Roman'
        serif_bold = 'CormorantGaramond-Bold' if 'CormorantGaramond-Bold' in registered_fonts else 'Times-Bold'
        serif_italic = 'CormorantGaramond-Italic' if 'CormorantGaramond-Italic' in registered_fonts else 'Times-Italic'
        sans_font = 'Inter' if 'Inter' in registered_fonts else 'Helvetica'
        sans_bold = 'Inter-Medium' if 'Inter-Medium' in registered_fonts else 'Helvetica-Bold'
        
        # Recipe title - Large, centered, elegant serif
        self.styles.add(ParagraphStyle(
            name='RecipeTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12,
            alignment=TA_CENTER,
            fontName=serif_bold,
            leading=34
        ))
        
        # Recipe description/headnote - Italic, centered, elegant
        self.styles.add(ParagraphStyle(
            name='RecipeDescription',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceBefore=4,
            spaceAfter=16,
            alignment=TA_CENTER,
            fontName=serif_italic,
            leading=14
        ))
        
        # Recipe subtitle style (alias for RecipeDescription for consistency)
        self.styles.add(ParagraphStyle(
            name='RecipeSubtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceBefore=4,
            spaceAfter=16,
            alignment=TA_CENTER,
            fontName=serif_italic,
            leading=14
        ))
        
        # Metadata bar - Small, centered, clean sans-serif
        self.styles.add(ParagraphStyle(
            name='MetadataBar',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            spaceBefore=8,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName=sans_font,
            leading=11
        ))
        
        # Metadata style (alias for MetadataBar for consistency)
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            spaceBefore=8,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName=sans_font,
            leading=11
        ))
        
        # Section headers - Small caps style, sans-serif
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            spaceBefore=16,
            spaceAfter=8,
            fontName=sans_bold,
            leading=13
        ))
        
        # Ingredients - Clean, serif body text with proper spacing
        self.styles.add(ParagraphStyle(
            name='Ingredient',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceBefore=3,
            spaceAfter=1,
            leftIndent=0,
            bulletIndent=0,
            fontName=serif_font,
            leading=14
        ))
        
        # Instructions - Serif, justified text for professional appearance
        self.styles.add(ParagraphStyle(
            name='Instruction',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceBefore=6,
            spaceAfter=2,
            alignment=TA_JUSTIFY,
            fontName=serif_font,
            leading=14
        ))
        
        # Notes - Smaller italic text
        self.styles.add(ParagraphStyle(
            name='Notes',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#555555'),
            spaceBefore=16,
            spaceAfter=8,
            fontName=serif_italic,
            leading=12
        ))


class PDFImageHandler:
    """Handles image processing for PDF generation with caching"""

    def __init__(self, config: 'PDFConfig'):
        """
        Initialize image handler with cache and profile configuration.

        Args:
            config: PDFConfig with profile-specific settings (image_quality, color_mode)
        """
        self.config = config
        self._image_cache: dict[str, tuple[str, RLImage]] = {}  # url -> (temp_path, image)
        self._temp_files: list[str] = []  # Track all temp files for cleanup

    def _optimize_image(self, source_path: str) -> str:
        """
        Optimize image based on output profile (quality and color mode).

        Args:
            source_path: Path to source image file

        Returns:
            Path to optimized image (may be same as source if no optimization needed)
        """
        try:
            from PIL import Image as PILImage
            import tempfile

            # Open image with PIL
            with PILImage.open(source_path) as img:
                # Convert to RGB if needed (handles RGBA, grayscale, etc.)
                if img.mode not in ('RGB', 'CMYK'):
                    img = img.convert('RGB')

                # Apply profile-specific optimizations
                if self.config.color_mode == 'CMYK' and img.mode != 'CMYK':
                    # Convert to CMYK for professional print
                    img = img.convert('CMYK')
                    logger.debug(f"Converted image to CMYK for {self.config.profile.value} profile")
                elif self.config.color_mode == 'RGB' and img.mode != 'RGB':
                    # Ensure RGB for digital/home print
                    img = img.convert('RGB')

                # Save with profile-specific quality
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    img.save(tmp.name, 'JPEG', quality=self.config.image_quality, optimize=True)
                    optimized_path = tmp.name

                self._temp_files.append(optimized_path)
                logger.debug(f"Optimized image: quality={self.config.image_quality}, mode={self.config.color_mode}")
                return optimized_path

        except Exception as e:
            logger.warning(f"Image optimization failed, using original: {e}")
            return source_path

    def process_image(self, image_path: str, max_width: float = 4 * inch,
                      max_height: float = 3 * inch, maintain_aspect: bool = True,
                      apply_profile_optimization: bool = True) -> Optional[RLImage]:
        """
        Process and resize image for PDF inclusion.

        Args:
            image_path: Path to image file
            max_width: Maximum width in points
            max_height: Maximum height in points
            maintain_aspect: Whether to maintain aspect ratio (default True)
            apply_profile_optimization: Apply profile-specific quality/color (default True)

        Returns:
            RLImage object or None if processing fails
        """
        try:
            if not image_path or not Path(image_path).exists():
                return None

            # Apply profile-specific optimization if requested
            if apply_profile_optimization:
                image_path = self._optimize_image(image_path)

            img = RLImage(image_path)

            # Calculate scaling to fit within max dimensions
            img_width = img.drawWidth
            img_height = img.drawHeight

            if maintain_aspect:
                # Scale proportionally to fit
                width_scale = max_width / img_width if img_width > max_width else 1
                height_scale = max_height / img_height if img_height > max_height else 1
                scale = min(width_scale, height_scale)

                if scale < 1:
                    img.drawWidth *= scale
                    img.drawHeight *= scale
            else:
                # Fill to exact dimensions (may distort)
                img.drawWidth = max_width
                img.drawHeight = max_height

            return img

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None

    def get_cover_image(self, url: str, page_width: float, page_height: float,
                       cover_fit: str = 'cover') -> Optional[RLImage]:
        """
        Download and process full-page cover image.

        Args:
            url: Image URL
            page_width: Full page width in points
            page_height: Full page height in points
            cover_fit: 'cover' (fill page, crop excess) or 'contain' (fit within page)

        Returns:
            RLImage sized for full-page cover or None if fails
        """
        try:
            import requests
            from PIL import Image as PILImage
            import tempfile

            # Check cache first
            if url in self._image_cache:
                cached_path, _ = self._image_cache[url]
                logger.debug(f"Using cached cover image for {url}")
                # Re-process from cache with cover dimensions
                return self._process_cover_from_path(cached_path, page_width, page_height, cover_fit)

            # Download image
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            self._temp_files.append(tmp_path)

            # Process as cover image
            img = self._process_cover_from_path(tmp_path, page_width, page_height, cover_fit)

            if img:
                img._temp_file_path = tmp_path
                # Cache the downloaded file path
                self._image_cache[url] = (tmp_path, img)
                logger.info(f"Downloaded and cached cover image from {url}")
            else:
                Path(tmp_path).unlink(missing_ok=True)
                self._temp_files.remove(tmp_path)

            return img

        except Exception as e:
            logger.error(f"Error downloading cover image from {url}: {e}")
            return None

    def _process_cover_from_path(self, image_path: str, page_width: float,
                                page_height: float, cover_fit: str) -> Optional[RLImage]:
        """Process image for full-page cover with profile optimization"""
        try:
            from PIL import Image as PILImage

            # Apply profile-specific optimization
            optimized_path = self._optimize_image(image_path)

            # Open with PIL to get actual dimensions
            with PILImage.open(optimized_path) as pil_img:
                img_width, img_height = pil_img.size

            # Create ReportLab image
            img = RLImage(optimized_path)

            if cover_fit == 'cover':
                # Fill entire page (crop if needed)
                width_ratio = page_width / img_width
                height_ratio = page_height / img_height
                scale = max(width_ratio, height_ratio)  # Use max to cover entire page
            else:  # 'contain'
                # Fit within page (may have borders)
                width_ratio = page_width / img_width
                height_ratio = page_height / img_height
                scale = min(width_ratio, height_ratio)

            img.drawWidth = img_width * scale
            img.drawHeight = img_height * scale

            return img

        except Exception as e:
            logger.error(f"Error processing cover image {image_path}: {e}")
            return None

    def get_image_from_url(self, url: str, max_width: float = 4 * inch,
                          max_height: float = 3 * inch) -> Optional[RLImage]:
        """
        Download and process image from URL with caching.

        Args:
            url: Image URL
            max_width: Maximum width in points (default 4 inches)
            max_height: Maximum height in points (default 3 inches)

        Returns:
            RLImage object or None if download/processing fails
        """
        try:
            import requests
            import tempfile

            # Check cache first
            if url in self._image_cache:
                cached_path, _ = self._image_cache[url]
                logger.debug(f"Using cached image for {url}")
                return self.process_image(cached_path, max_width, max_height)

            # Download image
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Save to temporary file (don't delete yet - ReportLab needs the file to exist)
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            self._temp_files.append(tmp_path)

            # Process the image
            img = self.process_image(tmp_path, max_width, max_height)

            # Store cleanup path in image object for later cleanup
            if img:
                img._temp_file_path = tmp_path
                # Cache for reuse
                self._image_cache[url] = (tmp_path, img)
                logger.info(f"Downloaded and cached image from {url}")
            else:
                # If image processing failed, clean up immediately
                Path(tmp_path).unlink(missing_ok=True)
                self._temp_files.remove(tmp_path)

            return img

        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return None

    def cleanup_temp_files(self):
        """Clean up all temporary image files"""
        for tmp_path in self._temp_files:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {tmp_path}: {e}")

        self._temp_files.clear()
        self._image_cache.clear()


class RecipePDFBuilder:
    """Builds PDF for individual recipes"""

    def __init__(self, config: PDFConfig = None):
        self.config = config or PDFConfig()
        self.style_manager = PDFStyleManager(self.config.template)
        self.image_handler = PDFImageHandler(self.config)
    
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

            # Modern template uses larger hero images (5" × 4")
            if self.config.template == PDFTemplate.MODERN:
                max_width = 5 * inch
                max_height = 4 * inch
            else:
                max_width = 4 * inch
                max_height = 3 * inch

            if main_image.get('cloudinary_url'):
                img = self.image_handler.get_image_from_url(
                    main_image['cloudinary_url'],
                    max_width,
                    max_height
                )
            elif main_image.get('image_url'):
                img = self.image_handler.get_image_from_url(
                    main_image['image_url'],
                    max_width,
                    max_height
                )

            if img:
                # Modern template: center image and add border
                if self.config.template == PDFTemplate.MODERN:
                    # Create framed image with border
                    from reportlab.platypus import Table, TableStyle

                    # Wrap image in table for centering and border
                    image_table = Table(
                        [[img]],
                        colWidths=[img.drawWidth],
                        rowHeights=[img.drawHeight]
                    )
                    image_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('BOX', (0, 0), (-1, -1), 0.5, self.style_manager.modern_colors.get('divider', colors.HexColor('#EDF2F4'))),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ]))

                    story.append(image_table)

                    # Add caption if available
                    caption = main_image.get('caption') or main_image.get('alt_text')
                    if caption:
                        story.append(Spacer(1, 0.1 * inch))
                        story.append(Paragraph(
                            caption,
                            self.style_manager.styles.get('ImageCaption', self.style_manager.styles['Normal'])
                        ))

                    story.append(Spacer(1, 0.3 * inch))
                else:
                    # Classic template: simple image
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
                inst_image_url = instruction.get('cloudinary_url') or instruction.get('image_url')
            else:
                inst_text = str(instruction)
                inst_image_url = None

            # Modern template: inline images with instructions
            if self.config.template == PDFTemplate.MODERN and self.config.include_images and inst_image_url:
                from reportlab.platypus import Table, TableStyle

                # Get small inline image (2" × 1.5")
                inst_img = self.image_handler.get_image_from_url(
                    inst_image_url,
                    max_width=2 * inch,
                    max_height=1.5 * inch
                )

                if inst_img:
                    # Create table with image on left, text on right
                    instruction_para = Paragraph(
                        f"<b>{i}.</b> {inst_text}",
                        self.style_manager.styles['Instruction']
                    )

                    inst_table = Table(
                        [[inst_img, instruction_para]],
                        colWidths=[inst_img.drawWidth + 12, None],  # Image width + padding, rest for text
                        spaceBefore=6,
                        spaceAfter=6
                    )
                    inst_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (0, 0), 0),
                        ('RIGHTPADDING', (0, 0), (0, 0), 6),
                        ('LEFTPADDING', (1, 0), (1, 0), 6),
                        ('RIGHTPADDING', (1, 0), (1, 0), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ]))

                    story.append(inst_table)
                    story.append(Spacer(1, 0.15 * inch))
                else:
                    # Image failed to load, use text only
                    story.append(Paragraph(
                        f"{i}. {inst_text}",
                        self.style_manager.styles['Instruction']
                    ))
                    story.append(Spacer(1, 0.1 * inch))
            else:
                # Classic template or no image: simple numbered instruction
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


class BookRecipePDFBuilder:
    """Builds PDF for recipes using elegant book-style layout with two columns"""

    def __init__(self, config: PDFConfig = None):
        from copy import deepcopy
        # Create a deep copy to avoid mutating the original config
        self.config = deepcopy(config) if config else PDFConfig()
        # Force book template for this builder
        self.config.template = PDFTemplate.BOOK
        self.style_manager = PDFStyleManager(self.config.template)
        self.image_handler = PDFImageHandler(self.config)
    
    def build_recipe_pdf(self, recipe: Dict[str, Any]) -> bytes:
        """Generate elegant book-style PDF for a single recipe"""
        buffer = io.BytesIO()
        
        # Determine page size
        page_size = letter if self.config.page_size == PageSize.LETTER else A4
        page_width, page_height = page_size
        
        # Create custom document with two-column layout
        doc = BaseDocTemplate(
            buffer,
            pagesize=page_size,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch
        )
        
        # Calculate frame dimensions for two columns
        frame_width = (page_width - 1.5 * inch) / 2 - 0.2 * inch  # Space for margins and column gap
        frame_height = page_height - 1.5 * inch
        
        # Define frames for two-column layout
        left_frame = Frame(
            0.75 * inch,  # x
            0.75 * inch,  # y 
            frame_width,  # width
            frame_height,  # height
            leftPadding=0,
            rightPadding=0.1 * inch,
            topPadding=0,
            bottomPadding=0
        )
        
        right_frame = Frame(
            0.75 * inch + frame_width + 0.2 * inch,  # x (left margin + left frame + gap)
            0.75 * inch,  # y
            frame_width,  # width  
            frame_height,  # height
            leftPadding=0.1 * inch,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0
        )
        
        # Create page template with frames
        page_template = PageTemplate(
            id='TwoColumn',
            frames=[left_frame, right_frame],
            onPage=self._add_page_elements
        )
        doc.addPageTemplates([page_template])
        
        # Build content story
        story = self._build_recipe_story(recipe)
        
        # Build PDF
        doc.build(story)
        
        # Clean up temporary image files
        self._cleanup_temp_images(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _build_recipe_story(self, recipe: Dict[str, Any]) -> List:
        """Build the complete recipe story with proper formatting"""
        story = []
        
        # Title - spans full width before columns
        story.append(Paragraph(
            recipe.get('title', 'Untitled Recipe'),
            self.style_manager.styles['RecipeTitle']
        ))
        
        # Description if present
        if recipe.get('description'):
            desc_text = sanitize_html_for_reportlab(recipe['description'])
            story.append(Paragraph(desc_text, self.style_manager.styles['RecipeDescription']))
        
        # Metadata bar (Yield • Servings • Times)
        metadata_parts = []
        if recipe.get('servings'):
            metadata_parts.append(f"Serves {recipe['servings']}")
        if recipe.get('prep_time'):
            prep_text = self._format_time(recipe['prep_time'])
            if prep_text:
                metadata_parts.append(f"Prep: {prep_text}")
        if recipe.get('cook_time'):
            cook_text = self._format_time(recipe['cook_time'])
            if cook_text:
                metadata_parts.append(f"Cook: {cook_text}")
        if recipe.get('total_time'):
            total_text = self._format_time(recipe['total_time'])
            if total_text:
                metadata_parts.append(f"Total: {total_text}")
        
        if metadata_parts:
            metadata_text = " • ".join(metadata_parts)
            story.append(Paragraph(metadata_text, self.style_manager.styles['MetadataBar']))
        
        # Ingredients section header
        story.append(Paragraph("INGREDIENTS", self.style_manager.styles['SectionHeader']))
        story.append(Spacer(1, 4))
        
        # Ingredients list
        ingredients = recipe.get('ingredients', [])
        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                ing_text = self._format_ingredient_elegant(ingredient)
            else:
                ing_text = str(ingredient)
            
            story.append(Paragraph(f"• {ing_text}", self.style_manager.styles['Ingredient']))
        
        # Frame break to move to right column
        story.append(FrameBreak())
        
        # Instructions section header
        story.append(Paragraph("METHOD", self.style_manager.styles['SectionHeader']))
        story.append(Spacer(1, 4))
        
        # Instructions
        instructions = recipe.get('instructions', [])
        for i, instruction in enumerate(instructions, 1):
            if isinstance(instruction, dict):
                inst_text = instruction.get('text', '')
            else:
                inst_text = str(instruction)
            
            # Clean HTML
            inst_text = sanitize_html_for_reportlab(inst_text)
            
            story.append(Paragraph(
                f"{i}. {inst_text}",
                self.style_manager.styles['Instruction']
            ))
            story.append(Spacer(1, 4))
        
        # Notes if present (stays in right column)
        if self.config.include_notes and recipe.get('notes'):
            story.append(Spacer(1, 12))
            story.append(Paragraph("NOTE", self.style_manager.styles['SectionHeader']))
            story.append(Spacer(1, 4))
            notes_text = sanitize_html_for_reportlab(recipe['notes'])
            story.append(Paragraph(notes_text, self.style_manager.styles['Notes']))
        
        return story
    
    def _format_ingredient_elegant(self, ingredient: Dict[str, Any]) -> str:
        """Format ingredient with elegant typography and proper units"""
        parts = []
        
        # Quantity and unit
        if ingredient.get('quantity'):
            qty = ingredient['quantity']
            # Convert decimals to fractions for common cooking measurements
            if isinstance(qty, (int, float)):
                qty_text = self._format_quantity(qty)
            else:
                qty_text = str(qty)
            parts.append(qty_text)
        
        if ingredient.get('unit'):
            unit = ingredient['unit']
            # Use proper abbreviations
            unit_abbrev = {
                'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
                'teaspoon': 'tsp', 'teaspoons': 'tsp', 
                'cup': 'cup', 'cups': 'cups',
                'pound': 'lb', 'pounds': 'lbs',
                'ounce': 'oz', 'ounces': 'oz',
                'gram': 'g', 'grams': 'g',
                'kilogram': 'kg', 'kilograms': 'kg',
                'milliliter': 'ml', 'milliliters': 'ml',
                'liter': 'l', 'liters': 'l'
            }.get(unit.lower(), unit)
            parts.append(unit_abbrev)
        
        # Ingredient name
        name = ingredient.get('name', '')
        parts.append(name)
        
        # Preparation in italics
        if ingredient.get('preparation'):
            prep = ingredient['preparation']
            parts.append(f"<i>{prep}</i>")
        
        # Optional ingredients
        if ingredient.get('optional'):
            parts.append("(optional)")
        
        return " ".join(parts)
    
    def _format_quantity(self, qty: Union[int, float]) -> str:
        """Convert decimal quantities to fractions for elegant display"""
        if qty == int(qty):
            return str(int(qty))
        
        # Common fraction conversions
        fraction_map = {
            0.125: '⅛', 0.25: '¼', 0.333: '⅓', 0.375: '⅜',
            0.5: '½', 0.625: '⅝', 0.666: '⅔', 0.75: '¾', 0.875: '⅞'
        }
        
        # Check for exact matches
        for decimal, fraction in fraction_map.items():
            if abs(qty - decimal) < 0.01:
                return fraction
        
        # Check for mixed numbers
        whole = int(qty)
        remainder = qty - whole
        
        if whole > 0:
            for decimal, fraction in fraction_map.items():
                if abs(remainder - decimal) < 0.01:
                    return f"{whole}{fraction}"
        
        # Fall back to decimal
        return str(qty)
    
    def _format_time(self, minutes: int) -> str:
        """Format cooking time elegantly"""
        if not minutes:
            return ""
        
        if minutes < 60:
            return f"{minutes} min"
        
        hours = minutes // 60
        mins = minutes % 60
        
        if mins == 0:
            return f"{hours} hr" if hours == 1 else f"{hours} hrs"
        
        if hours == 1:
            return f"1 hr {mins} min"
        else:
            return f"{hours} hrs {mins} min"
    
    def _add_page_elements(self, canvas, doc):
        """Add page number and other elements to each page"""
        canvas.saveState()
        
        # Page number at bottom center
        page_num = canvas.getPageNumber()
        text = f"{page_num}"
        
        # Use fallback font if Inter is not available
        try:
            canvas.setFont('Inter', 9)
        except KeyError:
            canvas.setFont('Helvetica', 9)
        
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(doc.pagesize[0] / 2 - 5, 0.5 * inch, text)
        
        canvas.restoreState()
    
    def _cleanup_temp_images(self, story):
        """Clean up temporary image files"""
        # Implementation same as RecipePDFBuilder
        def cleanup_element(element):
            if hasattr(element, '_temp_file_path'):
                try:
                    Path(element._temp_file_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {element._temp_file_path}: {e}")
            
            if hasattr(element, '_contents') and element._contents:
                for content in element._contents:
                    cleanup_element(content)
            elif hasattr(element, 'contents') and element.contents:
                for content in element.contents:
                    cleanup_element(content)
        
        for element in story:
            cleanup_element(element)


class CookbookPDFBuilder:
    """Builds PDF for complete cookbooks"""

    def __init__(self, config: PDFConfig = None):
        self.config = config or PDFConfig()
        self.style_manager = PDFStyleManager(self.config.template)
        self.image_handler = PDFImageHandler(self.config)
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

        # Modern template with cover image
        if self.config.template == PDFTemplate.MODERN and cookbook.get('cover_image_url'):
            cover_flowable = self._create_modern_cover(cookbook)
            if cover_flowable:
                elements.append(cover_flowable)
                return elements

        # Classic/fallback cover page (text-based)
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

    def _create_modern_cover(self, cookbook: Dict[str, Any]):
        """Create modern cover page with full-page image and title overlay"""
        from reportlab.platypus import Flowable

        class ModernCoverPage(Flowable):
            """Custom flowable for full-page cover with image and text overlay"""

            def __init__(self, cookbook, image_handler, style_manager, page_width, page_height):
                Flowable.__init__(self)
                self.cookbook = cookbook
                self.image_handler = image_handler
                self.style_manager = style_manager
                self.page_width = page_width
                self.page_height = page_height
                # Report zero size so this doesn't interfere with frame layout
                # The actual drawing uses absolute page coordinates
                self.width = 0
                self.height = 0

            def draw(self):
                """Draw the cover page on canvas using absolute page coordinates"""
                canvas = self.canv
                pw = self.page_width
                ph = self.page_height

                # Save graphics state and reset transforms to draw at absolute coords
                canvas.saveState()
                canvas.resetTransforms()

                # Download and draw full-page cover image
                cover_url = self.cookbook.get('cover_image_url')
                if cover_url:
                    try:
                        cover_img = self.image_handler.get_cover_image(
                            cover_url, pw, ph, cover_fit='cover'
                        )
                        if cover_img:
                            img_x = (pw - cover_img.drawWidth) / 2
                            img_y = (ph - cover_img.drawHeight) / 2
                            cover_img.drawOn(canvas, img_x, img_y)
                    except Exception as e:
                        logger.error(f"Failed to draw cover image: {e}")

                # Draw semi-transparent overlay for text readability
                overlay_color = self.style_manager.apply_opacity(colors.black, 0.35)
                canvas.setFillColor(overlay_color)
                canvas.rect(0, 0, pw, ph, fill=1, stroke=0)

                # Draw title text
                title = self.cookbook.get('title', 'Cookbook')
                canvas.setFillColor(colors.white)
                try:
                    canvas.setFont('Lora-Bold', 48)
                    font_name = 'Lora-Bold'
                except KeyError:
                    canvas.setFont('Helvetica-Bold', 48)
                    font_name = 'Helvetica-Bold'

                title_y = ph * 0.65
                title_width = canvas.stringWidth(title, font_name, 48)
                title_x = (pw - title_width) / 2
                canvas.drawString(title_x, title_y, title)

                # Draw author if present
                author = self.cookbook.get('author')
                if author:
                    author_text = f"by {author}"
                    try:
                        canvas.setFont('Inter', 18)
                        author_font = 'Inter'
                    except KeyError:
                        canvas.setFont('Helvetica', 18)
                        author_font = 'Helvetica'

                    author_y = title_y - 36
                    author_width = canvas.stringWidth(author_text, author_font, 18)
                    author_x = (pw - author_width) / 2
                    canvas.drawString(author_x, author_y, author_text)

                # Draw publication info at bottom
                pub_info = []
                if self.cookbook.get('publisher'):
                    pub_info.append(self.cookbook['publisher'])
                if self.cookbook.get('publication_date'):
                    pub_date = self.cookbook['publication_date']
                    if isinstance(pub_date, str):
                        pub_info.append(pub_date[:4])
                    else:
                        pub_info.append(str(pub_date.year))

                if pub_info:
                    pub_text = " • ".join(pub_info)
                    try:
                        canvas.setFont('Inter', 10)
                        pub_font = 'Inter'
                    except KeyError:
                        canvas.setFont('Helvetica', 10)
                        pub_font = 'Helvetica'

                    pub_y = 0.75 * inch
                    pub_width = canvas.stringWidth(pub_text, pub_font, 10)
                    pub_x = (pw - pub_width) / 2
                    canvas.drawString(pub_x, pub_y, pub_text)

                # Restore graphics state
                canvas.restoreState()

        # Get page size
        page_size = letter if self.config.page_size == PageSize.LETTER else A4
        page_width, page_height = page_size

        # Create and return the custom flowable
        return ModernCoverPage(
            cookbook,
            self.image_handler,
            self.style_manager,
            page_width,
            page_height
        )
    
    def _build_table_of_contents(self, recipes: List[Dict[str, Any]]) -> List:
        """Build table of contents"""
        elements = []

        # Modern template: clean, minimal TOC with generous spacing
        if self.config.template == PDFTemplate.MODERN:
            # TOC Title - use serif, larger, more breathing room
            toc_title_style = ParagraphStyle(
                'ModernTOCTitle',
                parent=self.style_manager.styles.get('CookbookTitle', self.style_manager.styles['Heading1']),
                fontSize=36,
                alignment=TA_CENTER,
                spaceAfter=48,  # More space for modern design
                spaceBefore=24
            )
            elements.append(Paragraph('Contents', toc_title_style))

            # Recipe entries - clean, minimal
            toc_entry_style = ParagraphStyle(
                'ModernTOCEntry',
                parent=self.style_manager.styles.get('ModernBody', self.style_manager.styles['Normal']),
                fontSize=12,
                leftIndent=0,
                spaceBefore=8,
                spaceAfter=8,
                leading=18
            )

            for i, recipe in enumerate(recipes, 1):
                title = recipe.get('title', 'Untitled Recipe')
                # Simple format: recipe number and title (no dot leaders for minimalist style)
                entry = f"{i}. {title}"
                elements.append(Paragraph(entry, toc_entry_style))

        else:
            # Classic TOC style
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

    def _build_section_divider(self, category_name: str) -> List:
        """
        Build a section divider page for recipe categories (e.g., "Appetizers", "Main Courses").
        Modern template uses minimal, elegant divider with generous white space.
        """
        elements = []

        if self.config.template == PDFTemplate.MODERN:
            # Add generous spacing at top
            elements.append(Spacer(1, 3 * inch))

            # Category name - large serif, centered
            divider_style = ParagraphStyle(
                'ModernSectionDivider',
                parent=self.style_manager.styles.get('RecipeTitle', self.style_manager.styles['Heading1']),
                fontSize=32,
                textColor=self.style_manager.modern_colors.get('primary', colors.HexColor('#2B2D42')),
                alignment=TA_CENTER,
                spaceBefore=0,
                spaceAfter=24,
                leading=38
            )
            elements.append(Paragraph(category_name, divider_style))

            # Subtle decorative line
            from reportlab.platypus import HRFlowable
            line = HRFlowable(
                width="30%",
                thickness=0.5,
                color=self.style_manager.modern_colors.get('divider', colors.HexColor('#EDF2F4')),
                spaceAfter=0,
                spaceBefore=12,
                hAlign='CENTER'
            )
            elements.append(line)

        else:
            # Classic template: simple category header
            elements.append(Spacer(1, 1 * inch))

            divider_style = ParagraphStyle(
                'SectionDivider',
                parent=self.style_manager.styles['Heading1'],
                fontSize=24,
                alignment=TA_CENTER,
                spaceAfter=12
            )
            elements.append(Paragraph(category_name, divider_style))
            elements.append(Spacer(1, 0.5 * inch))

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

        # Get page size
        page_width = letter[0] if self.config.page_size == PageSize.LETTER else A4[0]
        page_num = canvas_obj.getPageNumber()

        # Modern template: minimalist page numbers
        if self.config.template == PDFTemplate.MODERN:
            # Use Inter font if available, cleaner styling
            try:
                canvas_obj.setFont('Inter', 9)
            except KeyError:
                canvas_obj.setFont('Helvetica', 9)

            # Use secondary text color from modern palette
            canvas_obj.setFillColor(self.style_manager.modern_colors.get('secondary', colors.HexColor('#8D99AE')))

            # Just the number, no "Page" prefix for minimalism
            text = str(page_num)
            canvas_obj.drawCentredString(page_width / 2, 0.5 * inch, text)

        else:
            # Classic template: traditional page numbers
            canvas_obj.setFont('Helvetica', 9)
            canvas_obj.setFillColor(colors.HexColor('#7F8C8D'))
            text = f"Page {page_num}"
            canvas_obj.drawCentredString(page_width / 2, 0.5 * inch, text)

        canvas_obj.restoreState()


class PDFService:
    """Main service for PDF generation"""
    
    def __init__(self, config: PDFConfig = None):
        self.config = config or PDFConfig()
        self.recipe_builder = RecipePDFBuilder(self.config)
        self.book_recipe_builder = BookRecipePDFBuilder(self.config)
        self.cookbook_builder = CookbookPDFBuilder(self.config)
    
    def generate_recipe_pdf(self, recipe: Dict[str, Any], config: PDFConfig = None) -> bytes:
        """Generate PDF for a single recipe"""
        active_config = config or self.config

        # Use print-ready builder for print-ready PDFs
        if active_config.print_ready:
            from app.services.print_pdf_builder import PrintReadyPDFBuilder
            print_builder = PrintReadyPDFBuilder(active_config)
            return print_builder.build_recipe_pdf(recipe)

        # Use book-style builder for book template
        elif active_config.template == PDFTemplate.BOOK:
            if config:
                self.book_recipe_builder.config = config
                # Reinitialize style_manager and image_handler with new config
                self.book_recipe_builder.style_manager = PDFStyleManager(config.template)
                self.book_recipe_builder.image_handler = PDFImageHandler(config)
            return self.book_recipe_builder.build_recipe_pdf(recipe)
        else:
            if config:
                self.recipe_builder.config = config
                # Reinitialize style_manager and image_handler with new config
                self.recipe_builder.style_manager = PDFStyleManager(config.template)
                self.recipe_builder.image_handler = PDFImageHandler(config)
            return self.recipe_builder.build_recipe_pdf(recipe)
    
    def generate_cookbook_pdf(self, cookbook: Dict[str, Any],
                            recipes: List[Dict[str, Any]],
                            config: PDFConfig = None) -> bytes:
        """Generate PDF for a complete cookbook"""
        active_config = config or self.config

        # Use print-ready builder for print-ready PDFs
        if active_config.print_ready:
            from app.services.print_pdf_builder import PrintReadyPDFBuilder
            print_builder = PrintReadyPDFBuilder(active_config)
            return print_builder.build_cookbook_pdf(cookbook, recipes)

        # Use standard cookbook builder
        if config:
            self.cookbook_builder.config = config
            # Reinitialize style_manager and image_handler with new config
            self.cookbook_builder.style_manager = PDFStyleManager(config.template)
            self.cookbook_builder.image_handler = PDFImageHandler(config)
            # Also update the nested recipe builder
            self.cookbook_builder.recipe_builder.config = config
            self.cookbook_builder.recipe_builder.style_manager = PDFStyleManager(config.template)
            self.cookbook_builder.recipe_builder.image_handler = PDFImageHandler(config)

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
    
    def generate_simple_cover(self, cookbook: Dict[str, Any], config: PDFConfig = None) -> bytes:
        """Generate a simple cover PDF for print-on-demand"""
        active_config = config or self.config
        buffer = io.BytesIO()
        
        # Use the page size from config
        page_size = active_config.page_size
        doc = SimpleDocTemplate(buffer, pagesize=page_size, topMargin=1*inch, bottomMargin=1*inch)
        
        # Build content
        story = []
        styles = getSampleStyleSheet()
        
        # Create custom styles for cover
        title_style = ParagraphStyle(
            'CoverTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=0.5*inch,
            alignment=TA_CENTER,
            textColor=colors.black,
        )
        
        author_style = ParagraphStyle(
            'CoverAuthor',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=0.5*inch,
            alignment=TA_CENTER,
            textColor=colors.grey,
        )
        
        subtitle_style = ParagraphStyle(
            'CoverSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=1*inch,
            alignment=TA_CENTER,
            textColor=colors.grey,
        )
        
        # Add content to cover
        story.append(Spacer(1, 2*inch))  # Top spacing
        
        # Title
        title = cookbook.get('title', 'Untitled Cookbook')
        story.append(Paragraph(title, title_style))
        
        # Author
        author = cookbook.get('author', 'Unknown Author')
        story.append(Paragraph(f"by {author}", author_style))
        
        # Description (if available)
        description = cookbook.get('description')
        if description:
            # Truncate long descriptions
            if len(description) > 200:
                description = description[:197] + "..."
            story.append(Paragraph(description, subtitle_style))
        
        # Build the PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.read()