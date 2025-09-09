"""
Print marks renderer for professional print-ready PDFs.

This module provides utilities for adding crop marks, registration marks,
color bars, and other print marks required for commercial printing.
"""

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.utils.trim_sizes import PrintDimensions


@dataclass
class PrintMarksConfig:
    """Configuration for print marks rendering."""
    
    # Which marks to include
    crop_marks: bool = True
    registration_marks: bool = True
    color_bars: bool = False
    page_info: bool = True
    
    # Mark dimensions
    crop_mark_length: float = 0.25 * inch
    crop_mark_width: float = 0.5  # Line width in points
    crop_mark_offset: float = 0.0625 * inch  # Distance from trim edge
    
    registration_mark_size: float = 0.125 * inch
    registration_mark_offset: float = 0.5 * inch
    
    color_bar_width: float = 2.0 * inch
    color_bar_height: float = 0.125 * inch
    color_bar_offset: float = 0.25 * inch
    
    # Text properties
    info_text_size: float = 6
    info_text_color: tuple = (0, 0, 0)  # RGB
    
    # Line properties
    mark_color: tuple = (0, 0, 0)  # RGB for marks


class PrintMarksRenderer:
    """Renders print marks on PDF pages."""
    
    def __init__(self, config: PrintMarksConfig = None):
        self.config = config or PrintMarksConfig()
    
    def render_all_marks(
        self,
        canvas: Canvas,
        dimensions: PrintDimensions,
        page_info: Dict[str, Any] = None
    ):
        """
        Render all configured print marks on a canvas.
        
        Args:
            canvas: ReportLab canvas to draw on
            dimensions: Print dimensions for positioning
            page_info: Optional page information for text marks
        """
        if self.config.crop_marks:
            self.render_crop_marks(canvas, dimensions)
        
        if self.config.registration_marks:
            self.render_registration_marks(canvas, dimensions)
        
        if self.config.color_bars:
            self.render_color_bars(canvas, dimensions)
        
        if self.config.page_info and page_info:
            self.render_page_info(canvas, dimensions, page_info)
    
    def render_crop_marks(self, canvas: Canvas, dimensions: PrintDimensions):
        """Render corner crop marks."""
        canvas.saveState()
        canvas.setStrokeColorRGB(*self.config.mark_color)
        canvas.setLineWidth(self.config.crop_mark_width)
        
        # Get trim boundaries
        trim_bounds = dimensions.trim_area_bounds
        mark_length = self.config.crop_mark_length
        offset = self.config.crop_mark_offset
        
        # Corner positions (trim area corners)
        corners = [
            (trim_bounds['left'], trim_bounds['bottom']),    # Bottom-left
            (trim_bounds['right'], trim_bounds['bottom']),   # Bottom-right
            (trim_bounds['right'], trim_bounds['top']),      # Top-right
            (trim_bounds['left'], trim_bounds['top'])        # Top-left
        ]
        
        for i, (x, y) in enumerate(corners):
            if i == 0:  # Bottom-left
                # Horizontal mark (left)
                canvas.line(x - offset - mark_length, y, x - offset, y)
                # Vertical mark (bottom)
                canvas.line(x, y - offset - mark_length, x, y - offset)
            
            elif i == 1:  # Bottom-right
                # Horizontal mark (right)
                canvas.line(x + offset, y, x + offset + mark_length, y)
                # Vertical mark (bottom)
                canvas.line(x, y - offset - mark_length, x, y - offset)
            
            elif i == 2:  # Top-right
                # Horizontal mark (right)
                canvas.line(x + offset, y, x + offset + mark_length, y)
                # Vertical mark (top)
                canvas.line(x, y + offset, x, y + offset + mark_length)
            
            elif i == 3:  # Top-left
                # Horizontal mark (left)
                canvas.line(x - offset - mark_length, y, x - offset, y)
                # Vertical mark (top)
                canvas.line(x, y + offset, x, y + offset + mark_length)
        
        canvas.restoreState()
    
    def render_registration_marks(self, canvas: Canvas, dimensions: PrintDimensions):
        """Render registration marks for color alignment."""
        canvas.saveState()
        canvas.setStrokeColorRGB(*self.config.mark_color)
        canvas.setFillColorRGB(*self.config.mark_color)
        canvas.setLineWidth(0.5)
        
        trim_bounds = dimensions.trim_area_bounds
        mark_size = self.config.registration_mark_size
        offset = self.config.registration_mark_offset
        
        # Calculate center positions on each side
        center_x = (trim_bounds['left'] + trim_bounds['right']) / 2
        center_y = (trim_bounds['bottom'] + trim_bounds['top']) / 2
        
        # Registration mark positions (outside trim area)
        positions = [
            (center_x, trim_bounds['bottom'] - offset),  # Bottom center
            (center_x, trim_bounds['top'] + offset),     # Top center
            (trim_bounds['left'] - offset, center_y),    # Left center
            (trim_bounds['right'] + offset, center_y)    # Right center
        ]
        
        for x, y in positions:
            self._draw_registration_mark(canvas, x, y, mark_size)
        
        canvas.restoreState()
    
    def _draw_registration_mark(self, canvas: Canvas, x: float, y: float, size: float):
        """Draw a single registration mark (circle with crosshairs)."""
        radius = size / 2
        
        # Draw circle
        canvas.circle(x, y, radius, stroke=1, fill=0)
        
        # Draw crosshairs
        canvas.line(x - radius, y, x + radius, y)  # Horizontal
        canvas.line(x, y - radius, x, y + radius)  # Vertical
    
    def render_color_bars(self, canvas: Canvas, dimensions: PrintDimensions):
        """Render color bars for print quality control."""
        canvas.saveState()
        
        trim_bounds = dimensions.trim_area_bounds
        bar_width = self.config.color_bar_width
        bar_height = self.config.color_bar_height
        offset = self.config.color_bar_offset
        
        # Position color bar at bottom center, outside trim area
        bar_x = (trim_bounds['left'] + trim_bounds['right'] - bar_width) / 2
        bar_y = trim_bounds['bottom'] - offset - bar_height
        
        # Color bar segments (CMYK simulation in RGB)
        colors_rgb = [
            (1, 1, 1),      # White
            (0.75, 0.75, 0.75),  # 25% Gray
            (0.5, 0.5, 0.5),     # 50% Gray
            (0.25, 0.25, 0.25),  # 75% Gray
            (0, 0, 0),      # Black
            (1, 0, 1),      # Magenta
            (1, 1, 0),      # Yellow
            (0, 1, 1),      # Cyan
        ]
        
        segment_width = bar_width / len(colors_rgb)
        
        for i, (r, g, b) in enumerate(colors_rgb):
            canvas.setFillColorRGB(r, g, b)
            canvas.setStrokeColorRGB(0, 0, 0)
            canvas.setLineWidth(0.5)
            
            x = bar_x + (i * segment_width)
            canvas.rect(x, bar_y, segment_width, bar_height, stroke=1, fill=1)
        
        canvas.restoreState()
    
    def render_page_info(
        self,
        canvas: Canvas,
        dimensions: PrintDimensions,
        page_info: Dict[str, Any]
    ):
        """Render page information text."""
        canvas.saveState()
        canvas.setFillColorRGB(*self.config.info_text_color)
        canvas.setFont("Helvetica", self.config.info_text_size)
        
        trim_bounds = dimensions.trim_area_bounds
        
        # Position info text at bottom-left, outside trim area
        info_x = trim_bounds['left']
        info_y = trim_bounds['bottom'] - 0.125 * inch
        
        # Build info string
        info_parts = []
        
        if 'page_number' in page_info:
            info_parts.append(f"Page {page_info['page_number']}")
        
        if 'total_pages' in page_info:
            info_parts.append(f"of {page_info['total_pages']}")
        
        if 'title' in page_info:
            info_parts.append(f"• {page_info['title']}")
        
        if 'trim_size' in page_info:
            info_parts.append(f"• {page_info['trim_size']}")
        
        if 'date' in page_info:
            info_parts.append(f"• {page_info['date']}")
        
        info_text = " ".join(info_parts)
        
        if info_text:
            canvas.drawString(info_x, info_y, info_text)
        
        canvas.restoreState()
    
    def render_bleed_guides(self, canvas: Canvas, dimensions: PrintDimensions):
        """Render optional bleed area guides (typically not used in final output)."""
        canvas.saveState()
        canvas.setStrokeColorRGB(0.8, 0.8, 0.8)  # Light gray
        canvas.setLineWidth(0.25)
        canvas.setDash([2, 2])  # Dashed line
        
        # Draw rectangle around trim area to show bleed
        trim_bounds = dimensions.trim_area_bounds
        canvas.rect(
            trim_bounds['left'],
            trim_bounds['bottom'],
            trim_bounds['right'] - trim_bounds['left'],
            trim_bounds['top'] - trim_bounds['bottom'],
            stroke=1,
            fill=0
        )
        
        canvas.restoreState()
    
    def create_print_ready_template(
        self,
        canvas: Canvas,
        dimensions: PrintDimensions,
        page_info: Dict[str, Any] = None,
        include_guides: bool = False
    ):
        """
        Apply all print marks and prepare canvas for content.
        
        This is typically called at the beginning of each page.
        """
        # Set page size to full dimensions (including bleed)
        canvas.setPageSize(dimensions.full_size_tuple)
        
        # Render print marks
        self.render_all_marks(canvas, dimensions, page_info)
        
        # Optionally render guides for design purposes
        if include_guides:
            self.render_bleed_guides(canvas, dimensions)
    
    @classmethod
    def get_content_frame_bounds(
        cls,
        dimensions: PrintDimensions,
        gutter_margin: float = 0
    ) -> Dict[str, float]:
        """
        Get the frame boundaries where content should be placed.
        
        Args:
            dimensions: Print dimensions
            gutter_margin: Additional margin for binding (added to left margin)
            
        Returns:
            Dictionary with frame boundaries
        """
        safe_bounds = dimensions.safe_area_bounds
        
        # Add gutter margin to left side for binding
        return {
            'left': safe_bounds['left'] + gutter_margin,
            'bottom': safe_bounds['bottom'],
            'right': safe_bounds['right'],
            'top': safe_bounds['top'],
            'width': safe_bounds['right'] - safe_bounds['left'] - gutter_margin,
            'height': safe_bounds['top'] - safe_bounds['bottom']
        }
    
    @classmethod
    def validate_content_placement(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        dimensions: PrintDimensions
    ) -> Dict[str, Any]:
        """
        Validate that content placement is within safe printing bounds.
        
        Returns validation result with warnings if content is outside safe area.
        """
        safe_bounds = dimensions.safe_area_bounds
        trim_bounds = dimensions.trim_area_bounds
        
        result = {
            'is_valid': True,
            'warnings': [],
            'in_safe_area': True,
            'in_trim_area': True,
            'in_bleed_area': True
        }
        
        # Check if content extends beyond safe area
        if (x < safe_bounds['left'] or 
            y < safe_bounds['bottom'] or
            x + width > safe_bounds['right'] or 
            y + height > safe_bounds['top']):
            result['in_safe_area'] = False
            result['warnings'].append("Content extends beyond safe area")
        
        # Check if content extends beyond trim area
        if (x < trim_bounds['left'] or 
            y < trim_bounds['bottom'] or
            x + width > trim_bounds['right'] or 
            y + height > trim_bounds['top']):
            result['in_trim_area'] = False
            result['warnings'].append("Content extends beyond trim area into bleed")
        
        # Check if content extends beyond bleed area (this is an error)
        if (x < 0 or y < 0 or
            x + width > dimensions.full_width or 
            y + height > dimensions.full_height):
            result['in_bleed_area'] = False
            result['is_valid'] = False
            result['warnings'].append("Content extends beyond bleed area - will be cut off")
        
        return result