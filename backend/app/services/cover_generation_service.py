"""
Cover generation service for print-ready cookbook PDFs.

This service generates professional book covers for print-on-demand services,
including front cover, back cover, and spine with proper dimensions and bleed.
"""

import io
import logging
from typing import Dict, Any
from datetime import datetime

from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors

from app.utils.trim_sizes import TrimSizeMapper, PrintDimensions
from app.utils.print_marks import PrintMarksRenderer, PrintMarksConfig
from app.models.print_order import TrimSize

logger = logging.getLogger(__name__)


class CoverDimensions:
    """Calculates cover dimensions for different binding types."""

    def __init__(
        self, trim_size: TrimSize, page_count: int, binding_type: str = "perfect_bound"
    ):
        self.trim_size = trim_size
        self.page_count = page_count
        self.binding_type = binding_type

        # Get base dimensions
        self.interior_dims = TrimSizeMapper.get_dimensions(trim_size)

        # Calculate spine width
        self.spine_width = TrimSizeMapper.calculate_spine_width(
            page_count=page_count, paper_type="standard_white"
        )

        # Cover dimensions
        self.cover_width = (2 * self.interior_dims.trim_width) + self.spine_width
        self.cover_height = self.interior_dims.trim_height

        # Full cover with bleed
        self.full_width = self.cover_width + (2 * self.interior_dims.bleed_margin)
        self.full_height = self.cover_height + (2 * self.interior_dims.bleed_margin)

        # Area boundaries
        self.bleed_margin = self.interior_dims.bleed_margin
        self.safety_margin = self.interior_dims.safety_margin

    @property
    def front_cover_bounds(self) -> Dict[str, float]:
        """Get front cover area boundaries."""
        return {
            "left": self.bleed_margin
            + self.interior_dims.trim_width
            + self.spine_width,
            "bottom": self.bleed_margin,
            "right": self.full_width - self.bleed_margin,
            "top": self.full_height - self.bleed_margin,
            "width": self.interior_dims.trim_width,
            "height": self.interior_dims.trim_height,
        }

    @property
    def back_cover_bounds(self) -> Dict[str, float]:
        """Get back cover area boundaries."""
        return {
            "left": self.bleed_margin,
            "bottom": self.bleed_margin,
            "right": self.bleed_margin + self.interior_dims.trim_width,
            "top": self.full_height - self.bleed_margin,
            "width": self.interior_dims.trim_width,
            "height": self.interior_dims.trim_height,
        }

    @property
    def spine_bounds(self) -> Dict[str, float]:
        """Get spine area boundaries."""
        return {
            "left": self.bleed_margin + self.interior_dims.trim_width,
            "bottom": self.bleed_margin,
            "right": self.bleed_margin
            + self.interior_dims.trim_width
            + self.spine_width,
            "top": self.full_height - self.bleed_margin,
            "width": self.spine_width,
            "height": self.interior_dims.trim_height,
        }

    @property
    def front_safe_area(self) -> Dict[str, float]:
        """Get front cover safe area (content should stay within this)."""
        front = self.front_cover_bounds
        return {
            "left": front["left"] + self.safety_margin,
            "bottom": front["bottom"] + self.safety_margin,
            "right": front["right"] - self.safety_margin,
            "top": front["top"] - self.safety_margin,
            "width": front["width"] - (2 * self.safety_margin),
            "height": front["height"] - (2 * self.safety_margin),
        }

    @property
    def back_safe_area(self) -> Dict[str, float]:
        """Get back cover safe area."""
        back = self.back_cover_bounds
        return {
            "left": back["left"] + self.safety_margin,
            "bottom": back["bottom"] + self.safety_margin,
            "right": back["right"] - self.safety_margin,
            "top": back["top"] - self.safety_margin,
            "width": back["width"] - (2 * self.safety_margin),
            "height": back["height"] - (2 * self.safety_margin),
        }


class CoverTemplate:
    """Base template for book cover generation."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def render_front_cover(
        self,
        canvas: Canvas,
        bounds: Dict[str, float],
        safe_area: Dict[str, float],
        cookbook_data: Dict[str, Any],
    ):
        """Render the front cover design."""
        raise NotImplementedError("Subclasses must implement render_front_cover")

    def render_back_cover(
        self,
        canvas: Canvas,
        bounds: Dict[str, float],
        safe_area: Dict[str, float],
        cookbook_data: Dict[str, Any],
    ):
        """Render the back cover design."""
        raise NotImplementedError("Subclasses must implement render_back_cover")

    def render_spine(
        self, canvas: Canvas, bounds: Dict[str, float], cookbook_data: Dict[str, Any]
    ):
        """Render the spine design."""
        raise NotImplementedError("Subclasses must implement render_spine")


class MinimalistCoverTemplate(CoverTemplate):
    """Minimalist cover template with clean typography."""

    def __init__(self):
        super().__init__("Minimalist", "Clean typography with subtle design elements")
        self.primary_color = colors.Color(0.2, 0.2, 0.2)  # Dark gray
        self.accent_color = colors.Color(0.8, 0.6, 0.4)  # Warm brown
        self.text_color = colors.Color(0.1, 0.1, 0.1)  # Nearly black

    def render_front_cover(
        self,
        canvas: Canvas,
        bounds: Dict[str, float],
        safe_area: Dict[str, float],
        cookbook_data: Dict[str, Any],
    ):
        canvas.saveState()

        # Background color to bleed
        canvas.setFillColor(colors.Color(0.98, 0.96, 0.94))  # Warm white
        canvas.rect(
            bounds["left"] - 18,  # Extend to bleed
            bounds["bottom"] - 18,
            bounds["width"] + 36,
            bounds["height"] + 36,
            fill=1,
            stroke=0,
        )

        # Title
        title = cookbook_data.get("title", "Cookbook")
        canvas.setFillColor(self.primary_color)

        # Title font size based on text length
        if len(title) > 20:
            title_size = 28
        elif len(title) > 15:
            title_size = 32
        else:
            title_size = 36

        canvas.setFont("Helvetica-Bold", title_size)

        # Center title horizontally, position in upper third
        title_y = safe_area["top"] - (safe_area["height"] * 0.25)
        title_width = canvas.stringWidth(title, "Helvetica-Bold", title_size)
        title_x = safe_area["left"] + (safe_area["width"] - title_width) / 2

        canvas.drawString(title_x, title_y, title)

        # Subtitle/tagline if available
        subtitle = cookbook_data.get("subtitle")
        if subtitle:
            canvas.setFont("Helvetica", 16)
            canvas.setFillColor(self.accent_color)
            subtitle_width = canvas.stringWidth(subtitle, "Helvetica", 16)
            subtitle_x = safe_area["left"] + (safe_area["width"] - subtitle_width) / 2
            subtitle_y = title_y - 30
            canvas.drawString(subtitle_x, subtitle_y, subtitle)

        # Author name at bottom
        author = cookbook_data.get("author", "Author")
        canvas.setFont("Helvetica", 18)
        canvas.setFillColor(self.primary_color)
        author_width = canvas.stringWidth(author, "Helvetica", 18)
        author_x = safe_area["left"] + (safe_area["width"] - author_width) / 2
        author_y = safe_area["bottom"] + 40
        canvas.drawString(author_x, author_y, author)

        # Decorative line
        line_y = author_y + 25
        line_length = min(120, safe_area["width"] * 0.4)
        line_x = safe_area["left"] + (safe_area["width"] - line_length) / 2
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(2)
        canvas.line(line_x, line_y, line_x + line_length, line_y)

        canvas.restoreState()

    def render_back_cover(
        self,
        canvas: Canvas,
        bounds: Dict[str, float],
        safe_area: Dict[str, float],
        cookbook_data: Dict[str, Any],
    ):
        canvas.saveState()

        # Background color to bleed
        canvas.setFillColor(colors.Color(0.98, 0.96, 0.94))
        canvas.rect(
            bounds["left"] - 18,
            bounds["bottom"] - 18,
            bounds["width"] + 36,
            bounds["height"] + 36,
            fill=1,
            stroke=0,
        )

        # Description
        description = cookbook_data.get(
            "description", "A collection of delicious recipes."
        )
        canvas.setFont("Helvetica", 12)
        canvas.setFillColor(self.text_color)

        # Word wrap description
        words = description.split()
        lines = []
        current_line = ""
        line_width = safe_area["width"] - 40

        for word in words:
            test_line = current_line + " " + word if current_line else word
            if canvas.stringWidth(test_line, "Helvetica", 12) <= line_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # Draw description lines
        y_position = safe_area["top"] - 60
        line_height = 16

        for line in lines[:15]:  # Limit to 15 lines
            canvas.drawString(safe_area["left"] + 20, y_position, line)
            y_position -= line_height

        # Recipe count if available
        recipe_count = len(cookbook_data.get("recipes", []))
        if recipe_count > 0:
            count_text = f"Features {recipe_count} carefully tested recipes"
            canvas.setFont("Helvetica-Oblique", 11)
            canvas.setFillColor(self.accent_color)
            canvas.drawString(safe_area["left"] + 20, y_position - 30, count_text)

        canvas.restoreState()

    def render_spine(
        self, canvas: Canvas, bounds: Dict[str, float], cookbook_data: Dict[str, Any]
    ):
        if bounds["width"] < 0.25 * inch:  # Too thin for text
            return

        canvas.saveState()

        # Background
        canvas.setFillColor(colors.Color(0.98, 0.96, 0.94))
        canvas.rect(
            bounds["left"],
            bounds["bottom"] - 18,
            bounds["width"],
            bounds["height"] + 36,
            fill=1,
            stroke=0,
        )

        # Rotate for spine text
        canvas.translate(
            bounds["left"] + bounds["width"] / 2,
            bounds["bottom"] + bounds["height"] / 2,
        )
        canvas.rotate(90)

        # Title on spine
        title = cookbook_data.get("title", "Cookbook")

        # Adjust font size based on spine width and title length
        max_font_size = int(bounds["width"] * 0.6)
        font_size = min(max_font_size, 14)

        canvas.setFont("Helvetica-Bold", font_size)
        canvas.setFillColor(self.primary_color)

        # Center text
        text_width = canvas.stringWidth(title, "Helvetica-Bold", font_size)
        max_text_width = bounds["height"] - 40

        if text_width > max_text_width:
            # Truncate if too long
            while text_width > max_text_width and len(title) > 3:
                title = title[:-4] + "..."
                text_width = canvas.stringWidth(title, "Helvetica-Bold", font_size)

        canvas.drawCentredText(0, 0, title)

        canvas.restoreState()


class ClassicCoverTemplate(CoverTemplate):
    """Classic cover template with traditional professional styling.

    Matches the Classic PDF interior template colors and typography.
    Uses Helvetica family for a professional, traditional look.
    """

    def __init__(self):
        super().__init__("Classic", "Traditional professional cookbook cover")
        # Colors matching PDFStyleManager._apply_classic_styles()
        self.primary_color = colors.HexColor("#2C3E50")  # Dark blue-gray
        self.secondary_color = colors.HexColor("#34495E")  # Slightly lighter
        self.accent_color = colors.HexColor("#E74C3C")  # Warm red
        self.text_color = colors.HexColor("#2C3E50")
        self.bg_color = colors.Color(0.98, 0.97, 0.96)  # Warm off-white

    def render_front_cover(
        self,
        canvas: Canvas,
        bounds: Dict[str, float],
        safe_area: Dict[str, float],
        cookbook_data: Dict[str, Any],
    ):
        canvas.saveState()

        # Background color extending to bleed
        canvas.setFillColor(self.bg_color)
        canvas.rect(
            bounds["left"] - 18,
            bounds["bottom"] - 18,
            bounds["width"] + 36,
            bounds["height"] + 36,
            fill=1,
            stroke=0,
        )

        # Decorative top border
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(3)
        border_y = safe_area["top"] - 20
        canvas.line(safe_area["left"], border_y, safe_area["right"], border_y)

        # Title
        title = cookbook_data.get("title", "Cookbook")
        canvas.setFillColor(self.primary_color)

        # Adaptive title font size
        if len(title) > 25:
            title_size = 28
        elif len(title) > 18:
            title_size = 34
        else:
            title_size = 42

        canvas.setFont("Helvetica-Bold", title_size)

        # Center title, position in upper area
        title_y = safe_area["top"] - (safe_area["height"] * 0.30)
        title_width = canvas.stringWidth(title, "Helvetica-Bold", title_size)
        title_x = safe_area["left"] + (safe_area["width"] - title_width) / 2
        canvas.drawString(title_x, title_y, title)

        # Subtitle/tagline if available
        subtitle = (
            cookbook_data.get("subtitle") or cookbook_data.get("description", "")[:60]
        )
        if subtitle:
            canvas.setFont("Helvetica-Oblique", 14)
            canvas.setFillColor(self.secondary_color)
            # Truncate if too long
            if len(subtitle) > 50:
                subtitle = subtitle[:47] + "..."
            subtitle_width = canvas.stringWidth(subtitle, "Helvetica-Oblique", 14)
            subtitle_x = safe_area["left"] + (safe_area["width"] - subtitle_width) / 2
            subtitle_y = title_y - 30
            canvas.drawString(subtitle_x, subtitle_y, subtitle)

        # Decorative divider
        divider_y = title_y - 60
        divider_length = min(150, safe_area["width"] * 0.5)
        divider_x = safe_area["left"] + (safe_area["width"] - divider_length) / 2
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(1.5)
        canvas.line(divider_x, divider_y, divider_x + divider_length, divider_y)

        # Author name at bottom
        author = cookbook_data.get("author", "")
        if author:
            canvas.setFont("Helvetica", 18)
            canvas.setFillColor(self.primary_color)
            author_width = canvas.stringWidth(author, "Helvetica", 18)
            author_x = safe_area["left"] + (safe_area["width"] - author_width) / 2
            author_y = safe_area["bottom"] + 50
            canvas.drawString(author_x, author_y, author)

        # Bottom border
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(3)
        canvas.line(
            safe_area["left"],
            safe_area["bottom"] + 20,
            safe_area["right"],
            safe_area["bottom"] + 20,
        )

        canvas.restoreState()

    def render_back_cover(
        self,
        canvas: Canvas,
        bounds: Dict[str, float],
        safe_area: Dict[str, float],
        cookbook_data: Dict[str, Any],
    ):
        canvas.saveState()

        # Background
        canvas.setFillColor(self.bg_color)
        canvas.rect(
            bounds["left"] - 18,
            bounds["bottom"] - 18,
            bounds["width"] + 36,
            bounds["height"] + 36,
            fill=1,
            stroke=0,
        )

        # Top decorative border
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(2)
        canvas.line(
            safe_area["left"],
            safe_area["top"] - 20,
            safe_area["right"],
            safe_area["top"] - 20,
        )

        # "About This Cookbook" header
        canvas.setFont("Helvetica-Bold", 16)
        canvas.setFillColor(self.primary_color)
        header_text = "About This Cookbook"
        header_width = canvas.stringWidth(header_text, "Helvetica-Bold", 16)
        header_x = safe_area["left"] + (safe_area["width"] - header_width) / 2
        canvas.drawString(header_x, safe_area["top"] - 60, header_text)

        # Description
        description = cookbook_data.get(
            "description", "A collection of delicious recipes."
        )
        canvas.setFont("Helvetica", 11)
        canvas.setFillColor(self.text_color)

        # Word wrap description
        words = description.split()
        lines = []
        current_line = ""
        line_width = safe_area["width"] - 40

        for word in words:
            test_line = current_line + " " + word if current_line else word
            if canvas.stringWidth(test_line, "Helvetica", 11) <= line_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Draw description centered
        y_position = safe_area["top"] - 100
        line_height = 16

        for line in lines[:12]:
            line_w = canvas.stringWidth(line, "Helvetica", 11)
            line_x = safe_area["left"] + (safe_area["width"] - line_w) / 2
            canvas.drawString(line_x, y_position, line)
            y_position -= line_height

        # Recipe count
        recipe_count = len(cookbook_data.get("recipes", []))
        if recipe_count > 0:
            count_text = f"Featuring {recipe_count} Recipes"
            canvas.setFont("Helvetica-Bold", 13)
            canvas.setFillColor(self.accent_color)
            count_width = canvas.stringWidth(count_text, "Helvetica-Bold", 13)
            count_x = safe_area["left"] + (safe_area["width"] - count_width) / 2
            canvas.drawString(count_x, y_position - 30, count_text)

        # Bottom border
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(2)
        canvas.line(
            safe_area["left"],
            safe_area["bottom"] + 20,
            safe_area["right"],
            safe_area["bottom"] + 20,
        )

        canvas.restoreState()

    def render_spine(
        self, canvas: Canvas, bounds: Dict[str, float], cookbook_data: Dict[str, Any]
    ):
        if bounds["width"] < 0.25 * inch:
            return

        canvas.saveState()

        # Background
        canvas.setFillColor(self.bg_color)
        canvas.rect(
            bounds["left"],
            bounds["bottom"] - 18,
            bounds["width"],
            bounds["height"] + 36,
            fill=1,
            stroke=0,
        )

        # Rotate for spine text
        canvas.translate(
            bounds["left"] + bounds["width"] / 2,
            bounds["bottom"] + bounds["height"] / 2,
        )
        canvas.rotate(90)

        # Title on spine
        title = cookbook_data.get("title", "Cookbook")

        max_font_size = int(bounds["width"] * 0.6)
        font_size = min(max_font_size, 14)

        canvas.setFont("Helvetica-Bold", font_size)
        canvas.setFillColor(self.primary_color)

        text_width = canvas.stringWidth(title, "Helvetica-Bold", font_size)
        max_text_width = bounds["height"] - 40

        if text_width > max_text_width:
            while text_width > max_text_width and len(title) > 3:
                title = title[:-4] + "..."
                text_width = canvas.stringWidth(title, "Helvetica-Bold", font_size)

        canvas.drawCentredText(0, 0, title)

        canvas.restoreState()


class BookCoverTemplate(CoverTemplate):
    """Elegant book-style cover template with sophisticated typography.

    Matches the Book PDF interior template with serif fonts and refined styling.
    Uses Times-Roman family for an elegant, literary appearance.
    """

    def __init__(self):
        super().__init__("Book", "Elegant book-style cookbook cover")
        # Colors matching PDFStyleManager._apply_book_styles()
        self.primary_color = colors.black
        self.secondary_color = colors.HexColor("#333333")
        self.accent_color = colors.HexColor("#666666")  # Subtle gray accent
        self.text_color = colors.black
        self.bg_color = colors.Color(0.99, 0.98, 0.96)  # Cream/ivory

    def render_front_cover(
        self,
        canvas: Canvas,
        bounds: Dict[str, float],
        safe_area: Dict[str, float],
        cookbook_data: Dict[str, Any],
    ):
        canvas.saveState()

        # Elegant cream background extending to bleed
        canvas.setFillColor(self.bg_color)
        canvas.rect(
            bounds["left"] - 18,
            bounds["bottom"] - 18,
            bounds["width"] + 36,
            bounds["height"] + 36,
            fill=1,
            stroke=0,
        )

        # Elegant thin border frame
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(0.5)
        inset = 15
        canvas.rect(
            safe_area["left"] + inset,
            safe_area["bottom"] + inset,
            safe_area["width"] - 2 * inset,
            safe_area["height"] - 2 * inset,
            fill=0,
            stroke=1,
        )

        # Title - elegant serif
        title = cookbook_data.get("title", "Cookbook")
        canvas.setFillColor(self.primary_color)

        # Adaptive title font size
        if len(title) > 25:
            title_size = 32
        elif len(title) > 18:
            title_size = 40
        else:
            title_size = 48

        canvas.setFont("Times-Bold", title_size)

        # Center title vertically in upper third
        title_y = safe_area["top"] - (safe_area["height"] * 0.35)
        title_width = canvas.stringWidth(title, "Times-Bold", title_size)
        title_x = safe_area["left"] + (safe_area["width"] - title_width) / 2
        canvas.drawString(title_x, title_y, title)

        # Elegant ornamental divider
        divider_y = title_y - 25
        # Simple elegant line with small ornaments
        line_length = min(100, safe_area["width"] * 0.35)
        line_x = safe_area["left"] + (safe_area["width"] - line_length) / 2
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(0.75)
        canvas.line(line_x, divider_y, line_x + line_length, divider_y)
        # Small dots at ends
        canvas.setFillColor(self.accent_color)
        canvas.circle(line_x - 3, divider_y, 1.5, fill=1, stroke=0)
        canvas.circle(line_x + line_length + 3, divider_y, 1.5, fill=1, stroke=0)

        # Subtitle if available
        subtitle = cookbook_data.get("subtitle")
        if subtitle:
            canvas.setFont("Times-Italic", 14)
            canvas.setFillColor(self.secondary_color)
            subtitle_width = canvas.stringWidth(subtitle, "Times-Italic", 14)
            subtitle_x = safe_area["left"] + (safe_area["width"] - subtitle_width) / 2
            subtitle_y = divider_y - 30
            canvas.drawString(subtitle_x, subtitle_y, subtitle)

        # Author name - elegant placement at bottom
        author = cookbook_data.get("author", "")
        if author:
            canvas.setFont("Times-Roman", 16)
            canvas.setFillColor(self.primary_color)
            author_width = canvas.stringWidth(author, "Times-Roman", 16)
            author_x = safe_area["left"] + (safe_area["width"] - author_width) / 2
            author_y = safe_area["bottom"] + 60
            canvas.drawString(author_x, author_y, author)

            # Small line above author
            line_len = min(60, author_width + 20)
            line_x = safe_area["left"] + (safe_area["width"] - line_len) / 2
            canvas.setStrokeColor(self.accent_color)
            canvas.setLineWidth(0.5)
            canvas.line(line_x, author_y + 20, line_x + line_len, author_y + 20)

        canvas.restoreState()

    def render_back_cover(
        self,
        canvas: Canvas,
        bounds: Dict[str, float],
        safe_area: Dict[str, float],
        cookbook_data: Dict[str, Any],
    ):
        canvas.saveState()

        # Cream background
        canvas.setFillColor(self.bg_color)
        canvas.rect(
            bounds["left"] - 18,
            bounds["bottom"] - 18,
            bounds["width"] + 36,
            bounds["height"] + 36,
            fill=1,
            stroke=0,
        )

        # Elegant thin border
        canvas.setStrokeColor(self.accent_color)
        canvas.setLineWidth(0.5)
        inset = 15
        canvas.rect(
            safe_area["left"] + inset,
            safe_area["bottom"] + inset,
            safe_area["width"] - 2 * inset,
            safe_area["height"] - 2 * inset,
            fill=0,
            stroke=1,
        )

        # Description in elegant italic
        description = cookbook_data.get(
            "description", "A collection of delicious recipes."
        )
        canvas.setFont("Times-Italic", 11)
        canvas.setFillColor(self.text_color)

        # Word wrap description
        words = description.split()
        lines = []
        current_line = ""
        line_width = safe_area["width"] - 60

        for word in words:
            test_line = current_line + " " + word if current_line else word
            if canvas.stringWidth(test_line, "Times-Italic", 11) <= line_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Draw description centered
        y_position = safe_area["top"] - 80
        line_height = 16

        for line in lines[:12]:
            line_w = canvas.stringWidth(line, "Times-Italic", 11)
            line_x = safe_area["left"] + (safe_area["width"] - line_w) / 2
            canvas.drawString(line_x, y_position, line)
            y_position -= line_height

        # Recipe count in elegant style
        recipe_count = len(cookbook_data.get("recipes", []))
        if recipe_count > 0:
            # Ornamental divider
            div_len = 40
            div_x = safe_area["left"] + (safe_area["width"] - div_len) / 2
            canvas.setStrokeColor(self.accent_color)
            canvas.setLineWidth(0.5)
            canvas.line(div_x, y_position - 20, div_x + div_len, y_position - 20)

            count_text = f"{recipe_count} Recipes"
            canvas.setFont("Times-Roman", 12)
            canvas.setFillColor(self.secondary_color)
            count_width = canvas.stringWidth(count_text, "Times-Roman", 12)
            count_x = safe_area["left"] + (safe_area["width"] - count_width) / 2
            canvas.drawString(count_x, y_position - 45, count_text)

        canvas.restoreState()

    def render_spine(
        self, canvas: Canvas, bounds: Dict[str, float], cookbook_data: Dict[str, Any]
    ):
        if bounds["width"] < 0.25 * inch:
            return

        canvas.saveState()

        # Cream background
        canvas.setFillColor(self.bg_color)
        canvas.rect(
            bounds["left"],
            bounds["bottom"] - 18,
            bounds["width"],
            bounds["height"] + 36,
            fill=1,
            stroke=0,
        )

        # Rotate for spine text
        canvas.translate(
            bounds["left"] + bounds["width"] / 2,
            bounds["bottom"] + bounds["height"] / 2,
        )
        canvas.rotate(90)

        # Title on spine in elegant serif
        title = cookbook_data.get("title", "Cookbook")

        max_font_size = int(bounds["width"] * 0.55)
        font_size = min(max_font_size, 13)

        canvas.setFont("Times-Bold", font_size)
        canvas.setFillColor(self.primary_color)

        text_width = canvas.stringWidth(title, "Times-Bold", font_size)
        max_text_width = bounds["height"] - 50

        if text_width > max_text_width:
            while text_width > max_text_width and len(title) > 3:
                title = title[:-4] + "..."
                text_width = canvas.stringWidth(title, "Times-Bold", font_size)

        canvas.drawCentredText(0, 0, title)

        canvas.restoreState()


class CoverGenerationService:
    """Service for generating print-ready book covers."""

    def __init__(self):
        self.templates = {
            "minimalist": MinimalistCoverTemplate(),
            "classic": ClassicCoverTemplate(),
            "book": BookCoverTemplate(),
        }
        self.default_template = "minimalist"

    def generate_cover_pdf(
        self,
        cookbook_data: Dict[str, Any],
        trim_size: TrimSize,
        page_count: int,
        template_name: str = None,
        binding_type: str = "perfect_bound",
    ) -> bytes:
        """Generate a print-ready cover PDF."""

        template_name = template_name or self.default_template
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")

        template = self.templates[template_name]

        # Calculate cover dimensions
        cover_dims = CoverDimensions(trim_size, page_count, binding_type)

        # Create PDF buffer
        buffer = io.BytesIO()
        canvas = Canvas(
            buffer, pagesize=(cover_dims.full_width, cover_dims.full_height)
        )

        # Set up print marks
        print_marks_config = PrintMarksConfig(
            crop_marks=True, registration_marks=True, color_bars=False, page_info=True
        )
        print_marks_renderer = PrintMarksRenderer(print_marks_config)

        # Create fake dimensions for print marks (covers use different dimensions)
        cover_print_dims = PrintDimensions(
            trim_width=cover_dims.cover_width,
            trim_height=cover_dims.cover_height,
            full_width=cover_dims.full_width,
            full_height=cover_dims.full_height,
            safe_width=cover_dims.cover_width - (2 * cover_dims.safety_margin),
            safe_height=cover_dims.cover_height - (2 * cover_dims.safety_margin),
            bleed_margin=cover_dims.bleed_margin,
            safety_margin=cover_dims.safety_margin,
            content_offset_x=cover_dims.bleed_margin + cover_dims.safety_margin,
            content_offset_y=cover_dims.bleed_margin + cover_dims.safety_margin,
            trim_offset_x=cover_dims.bleed_margin,
            trim_offset_y=cover_dims.bleed_margin,
        )

        # Add print marks
        page_info = {
            "page_number": 1,
            "title": f"{cookbook_data.get('title', 'Cookbook')} - Cover",
            "trim_size": trim_size.value,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "spine_width": f"{cover_dims.spine_width / inch:.3f}in",
        }

        print_marks_renderer.render_all_marks(canvas, cover_print_dims, page_info)

        # Render cover elements
        try:
            # Back cover
            template.render_back_cover(
                canvas,
                cover_dims.back_cover_bounds,
                cover_dims.back_safe_area,
                cookbook_data,
            )

            # Spine
            template.render_spine(canvas, cover_dims.spine_bounds, cookbook_data)

            # Front cover
            template.render_front_cover(
                canvas,
                cover_dims.front_cover_bounds,
                cover_dims.front_safe_area,
                cookbook_data,
            )

        except Exception as e:
            logger.error(f"Error rendering cover template: {str(e)}", exc_info=True)
            raise

        # Finalize PDF
        canvas.save()
        buffer.seek(0)
        return buffer.read()

    def get_available_templates(self) -> Dict[str, str]:
        """Get list of available cover templates."""
        return {name: template.description for name, template in self.templates.items()}

    def estimate_page_count(
        self, recipe_count: int, include_extras: bool = True
    ) -> int:
        """Estimate total page count for cover spine calculation."""
        # Base pages per recipe (varies by template and content)
        pages_per_recipe = 1.5  # Average

        base_pages = int(recipe_count * pages_per_recipe)

        if include_extras:
            # Add pages for title, TOC, index, etc.
            base_pages += 10

        # Round up to even number (books typically have even page counts)
        if base_pages % 2 == 1:
            base_pages += 1

        return max(base_pages, 20)  # Minimum 20 pages for spine

    def validate_cover_content(
        self, cookbook_data: Dict[str, Any], trim_size: TrimSize
    ) -> Dict[str, Any]:
        """Validate cookbook data for cover generation."""
        warnings = []
        is_valid = True

        # Check required fields
        if not cookbook_data.get("title"):
            warnings.append("Title is required for cover generation")
            is_valid = False

        if not cookbook_data.get("author"):
            warnings.append("Author name is recommended for professional covers")

        # Check title length
        title = cookbook_data.get("title", "")
        if len(title) > 50:
            warnings.append("Title may be too long for smaller trim sizes")

        # Check description length
        description = cookbook_data.get("description", "")
        if len(description) > 800:
            warnings.append("Description may be too long for back cover")
        elif len(description) < 100:
            warnings.append("Description is quite short - consider expanding")

        return {
            "is_valid": is_valid,
            "warnings": warnings,
            "estimated_page_count": self.estimate_page_count(
                len(cookbook_data.get("recipes", []))
            ),
        }
