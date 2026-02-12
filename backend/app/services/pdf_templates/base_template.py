"""Base Template for PDF Generation

Abstract base class that defines the interface for all PDF templates.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from dataclasses import dataclass

from reportlab.lib.styles import ParagraphStyle


@dataclass
class TemplateColors:
    """Color scheme for a template"""

    primary: str = "#2C3E50"
    secondary: str = "#34495E"
    accent: str = "#3498DB"
    text: str = "#2C3E50"
    text_light: str = "#7F8C8D"
    background: str = "#FFFFFF"


@dataclass
class TemplateFonts:
    """Font configuration for a template"""

    title: str = "Helvetica-Bold"
    heading: str = "Helvetica-Bold"
    body: str = "Helvetica"
    body_italic: str = "Helvetica-Oblique"
    monospace: str = "Courier"


class BasePDFTemplate(ABC):
    """Abstract base class for PDF templates"""

    def __init__(self):
        self.colors = self.get_colors()
        self.fonts = self.get_fonts()
        self.styles = {}
        self._initialize_styles()

    @abstractmethod
    def get_colors(self) -> TemplateColors:
        """Get color scheme for this template"""
        pass

    @abstractmethod
    def get_fonts(self) -> TemplateFonts:
        """Get font configuration for this template"""
        pass

    @abstractmethod
    def get_title_style(self) -> ParagraphStyle:
        """Get style for recipe titles"""
        pass

    @abstractmethod
    def get_subtitle_style(self) -> ParagraphStyle:
        """Get style for recipe subtitles/descriptions"""
        pass

    @abstractmethod
    def get_section_header_style(self) -> ParagraphStyle:
        """Get style for section headers (Ingredients, Instructions, etc.)"""
        pass

    @abstractmethod
    def get_ingredient_style(self) -> ParagraphStyle:
        """Get style for ingredient items"""
        pass

    @abstractmethod
    def get_instruction_style(self) -> ParagraphStyle:
        """Get style for instruction steps"""
        pass

    @abstractmethod
    def get_metadata_style(self) -> ParagraphStyle:
        """Get style for metadata (prep time, servings, etc.)"""
        pass

    @abstractmethod
    def get_cover_title_style(self) -> ParagraphStyle:
        """Get style for cookbook cover title"""
        pass

    @abstractmethod
    def get_cover_author_style(self) -> ParagraphStyle:
        """Get style for cookbook cover author"""
        pass

    def _initialize_styles(self):
        """Initialize all styles for the template"""
        self.styles["title"] = self.get_title_style()
        self.styles["subtitle"] = self.get_subtitle_style()
        self.styles["section_header"] = self.get_section_header_style()
        self.styles["ingredient"] = self.get_ingredient_style()
        self.styles["instruction"] = self.get_instruction_style()
        self.styles["metadata"] = self.get_metadata_style()
        self.styles["cover_title"] = self.get_cover_title_style()
        self.styles["cover_author"] = self.get_cover_author_style()

    def format_ingredient(self, ingredient: Dict[str, Any]) -> str:
        """Format an ingredient for display"""
        parts = []

        if ingredient.get("quantity"):
            parts.append(str(ingredient["quantity"]))

        if ingredient.get("unit"):
            parts.append(ingredient["unit"])

        parts.append(ingredient.get("name", ""))

        if ingredient.get("preparation"):
            parts.append(f", {ingredient['preparation']}")

        if ingredient.get("optional"):
            parts.append(" (optional)")

        return " ".join(parts)

    def format_instruction(self, instruction: Any, number: int) -> str:
        """Format an instruction step"""
        if isinstance(instruction, dict):
            text = instruction.get("text", "")
        else:
            text = str(instruction)

        return f"{number}. {text}"

    def get_page_margins(self) -> Dict[str, float]:
        """Get page margins for this template"""
        from reportlab.lib.units import inch

        return {
            "top": 1 * inch,
            "bottom": 1 * inch,
            "left": 1 * inch,
            "right": 1 * inch,
        }

    def get_element_spacing(self) -> Dict[str, float]:
        """Get spacing between elements"""
        from reportlab.lib.units import inch

        return {
            "after_title": 0.3 * inch,
            "after_section": 0.3 * inch,
            "between_ingredients": 0.05 * inch,
            "between_instructions": 0.1 * inch,
            "between_recipes": 1 * inch,
        }
