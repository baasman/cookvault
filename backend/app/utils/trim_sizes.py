"""
Utility for mapping trim sizes to exact print dimensions.

This module provides precise dimension mapping for print-ready PDF generation,
including bleed calculations and safe area definitions for professional printing.
"""

from typing import Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

from reportlab.lib.units import inch, mm
from app.models.print_order import TrimSize


@dataclass
class PrintDimensions:
    """Represents all dimensions needed for print-ready PDF generation."""
    
    # Base trim size (final book size)
    trim_width: float
    trim_height: float
    
    # Full page size including bleed
    full_width: float
    full_height: float
    
    # Safe area (content should stay within this)
    safe_width: float
    safe_height: float
    
    # Margins and offsets
    bleed_margin: float
    safety_margin: float
    
    # Positioning offsets from bottom-left corner
    content_offset_x: float
    content_offset_y: float
    trim_offset_x: float
    trim_offset_y: float
    
    @property
    def trim_size_tuple(self) -> Tuple[float, float]:
        """Return trim size as tuple for ReportLab."""
        return (self.trim_width, self.trim_height)
    
    @property
    def full_size_tuple(self) -> Tuple[float, float]:
        """Return full page size including bleed."""
        return (self.full_width, self.full_height)
    
    @property
    def safe_area_bounds(self) -> Dict[str, float]:
        """Return safe area boundaries."""
        return {
            'left': self.content_offset_x,
            'bottom': self.content_offset_y,
            'right': self.content_offset_x + self.safe_width,
            'top': self.content_offset_y + self.safe_height
        }
    
    @property
    def trim_area_bounds(self) -> Dict[str, float]:
        """Return trim area boundaries (final book edges)."""
        return {
            'left': self.trim_offset_x,
            'bottom': self.trim_offset_y,
            'right': self.trim_offset_x + self.trim_width,
            'top': self.trim_offset_y + self.trim_height
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'trim_width': self.trim_width,
            'trim_height': self.trim_height,
            'full_width': self.full_width,
            'full_height': self.full_height,
            'safe_width': self.safe_width,
            'safe_height': self.safe_height,
            'bleed_margin': self.bleed_margin,
            'safety_margin': self.safety_margin,
            'trim_size_inches': (self.trim_width / inch, self.trim_height / inch),
            'full_size_inches': (self.full_width / inch, self.full_height / inch)
        }


class TrimSizeMapper:
    """Maps trim sizes to precise print dimensions."""
    
    # Standard bleed margin for book printing (1/8 inch)
    DEFAULT_BLEED = 0.125 * inch
    
    # Safety margin inside trim area (1/4 inch from edge)
    DEFAULT_SAFETY = 0.25 * inch
    
    # Precise trim size dimensions in ReportLab units (points)
    TRIM_SIZE_DIMENSIONS = {
        TrimSize.US_LETTER: (8.5 * inch, 11.0 * inch),
        TrimSize.US_TRADE: (6.0 * inch, 9.0 * inch),
        TrimSize.DIGEST: (5.5 * inch, 8.5 * inch),
        TrimSize.SQUARE_8: (8.0 * inch, 8.0 * inch),
        TrimSize.LANDSCAPE_9x7: (9.0 * inch, 7.0 * inch),
        TrimSize.A4: (210 * mm, 297 * mm),
        TrimSize.A5: (148 * mm, 210 * mm),
    }
    
    @classmethod
    def get_dimensions(
        self,
        trim_size: TrimSize,
        bleed_margin: float = None,
        safety_margin: float = None
    ) -> PrintDimensions:
        """
        Get complete print dimensions for a trim size.
        
        Args:
            trim_size: The target book trim size
            bleed_margin: Custom bleed margin (defaults to 1/8 inch)
            safety_margin: Custom safety margin (defaults to 1/4 inch)
            
        Returns:
            PrintDimensions object with all calculated dimensions
        """
        if trim_size not in self.TRIM_SIZE_DIMENSIONS:
            raise ValueError(f"Unsupported trim size: {trim_size}")
        
        bleed_margin = bleed_margin or self.DEFAULT_BLEED
        safety_margin = safety_margin or self.DEFAULT_SAFETY
        
        # Get base trim dimensions
        trim_width, trim_height = self.TRIM_SIZE_DIMENSIONS[trim_size]
        
        # Calculate full page size (trim + bleed on all sides)
        full_width = trim_width + (2 * bleed_margin)
        full_height = trim_height + (2 * bleed_margin)
        
        # Calculate safe area (trim - safety margin on all sides)
        safe_width = trim_width - (2 * safety_margin)
        safe_height = trim_height - (2 * safety_margin)
        
        # Calculate positioning offsets
        # Bleed margin positions the trim area within the full page
        trim_offset_x = bleed_margin
        trim_offset_y = bleed_margin
        
        # Content offset positions the safe area within the full page
        content_offset_x = bleed_margin + safety_margin
        content_offset_y = bleed_margin + safety_margin
        
        return PrintDimensions(
            trim_width=trim_width,
            trim_height=trim_height,
            full_width=full_width,
            full_height=full_height,
            safe_width=safe_width,
            safe_height=safe_height,
            bleed_margin=bleed_margin,
            safety_margin=safety_margin,
            content_offset_x=content_offset_x,
            content_offset_y=content_offset_y,
            trim_offset_x=trim_offset_x,
            trim_offset_y=trim_offset_y
        )
    
    @classmethod
    def get_gutter_margin(
        self,
        binding_type: str,
        page_count: int = None
    ) -> float:
        """
        Calculate appropriate gutter margin for binding.
        
        Args:
            binding_type: Type of binding (from BindingType enum)
            page_count: Number of pages (affects spine thickness)
            
        Returns:
            Additional gutter margin in points
        """
        # Base gutter margins by binding type
        gutter_margins = {
            'perfect_bound': 0.5 * inch,  # Standard paperback
            'coil_bound': 0.75 * inch,    # Spiral binding needs more space
            'saddle_stitch': 0.25 * inch, # Stapled binding
            'case_wrap': 0.75 * inch,     # Hardcover
            'dust_jacket': 0.75 * inch,   # Hardcover with dust jacket
        }
        
        base_gutter = gutter_margins.get(binding_type.lower(), 0.5 * inch)
        
        # Adjust for page count (thicker books need more gutter)
        if page_count:
            if page_count > 300:
                base_gutter += 0.125 * inch
            elif page_count > 200:
                base_gutter += 0.0625 * inch
        
        return base_gutter
    
    @classmethod
    def calculate_spine_width(
        self,
        page_count: int,
        paper_type: str = 'standard_white'
    ) -> float:
        """
        Calculate spine width based on page count and paper type.
        
        Args:
            page_count: Total number of pages
            paper_type: Type of paper (affects thickness)
            
        Returns:
            Spine width in points
        """
        # Pages per inch by paper type (approximate)
        pages_per_inch = {
            'standard_white': 440,    # 60# white paper
            'standard_cream': 440,    # 60# cream paper
            'premium_white': 380,     # 70# white paper (thicker)
            'premium_color': 380,     # 70# color paper (thicker)
        }
        
        ppi = pages_per_inch.get(paper_type.lower(), 440)
        spine_inches = page_count / ppi
        
        return spine_inches * inch
    
    @classmethod
    def get_all_supported_sizes(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all supported trim sizes."""
        result = {}
        
        for trim_size in TrimSize:
            try:
                dimensions = self.get_dimensions(trim_size)
                result[trim_size.value] = {
                    'name': trim_size.name,
                    'trim_inches': (
                        dimensions.trim_width / inch,
                        dimensions.trim_height / inch
                    ),
                    'description': self._get_size_description(trim_size),
                    'suitable_for': self._get_size_recommendations(trim_size)
                }
            except ValueError:
                continue
        
        return result
    
    @classmethod
    def _get_size_description(self, trim_size: TrimSize) -> str:
        """Get human-readable description of a trim size."""
        descriptions = {
            TrimSize.US_LETTER: "8.5\" × 11\" - Standard US letter size",
            TrimSize.US_TRADE: "6\" × 9\" - Popular book size, great for novels and cookbooks",
            TrimSize.DIGEST: "5.5\" × 8.5\" - Compact size, good for pocket guides",
            TrimSize.SQUARE_8: "8\" × 8\" - Square format, ideal for photo books",
            TrimSize.LANDSCAPE_9x7: "9\" × 7\" - Landscape orientation, great for visual content",
            TrimSize.A4: "210mm × 297mm - International standard",
            TrimSize.A5: "148mm × 210mm - Half A4 size, compact and portable"
        }
        return descriptions.get(trim_size, f"{trim_size.name} - Professional print size")
    
    @classmethod
    def _get_size_recommendations(self, trim_size: TrimSize) -> str:
        """Get recommendations for when to use this size."""
        recommendations = {
            TrimSize.US_LETTER: "Technical manuals, reference materials",
            TrimSize.US_TRADE: "Cookbooks, novels, general non-fiction",
            TrimSize.DIGEST: "Pocket guides, small format books",
            TrimSize.SQUARE_8: "Photo cookbooks, coffee table books",
            TrimSize.LANDSCAPE_9x7: "Recipe collections with large images",
            TrimSize.A4: "International publications, technical documents",
            TrimSize.A5: "Portable cookbooks, pocket recipe collections"
        }
        return recommendations.get(trim_size, "General purpose book printing")