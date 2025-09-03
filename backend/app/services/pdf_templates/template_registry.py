"""Template Registry for PDF Generation

Manages available templates and provides easy access.
"""

from typing import Dict, Type, Optional, List
from enum import Enum

from .base_template import BasePDFTemplate
from .classic_template import ClassicPDFTemplate


class TemplateType(Enum):
    """Available template types"""
    CLASSIC = "classic"
    MODERN = "modern"
    MINIMALIST = "minimalist"
    CUSTOM = "custom"


class TemplateRegistry:
    """Registry for PDF templates"""
    
    _templates: Dict[TemplateType, Type[BasePDFTemplate]] = {
        TemplateType.CLASSIC: ClassicPDFTemplate,
        # Future templates will be added here
        # TemplateType.MODERN: ModernPDFTemplate,
        # TemplateType.MINIMALIST: MinimalistPDFTemplate,
    }
    
    @classmethod
    def get_template(cls, template_type: TemplateType) -> BasePDFTemplate:
        """Get an instance of the specified template"""
        template_class = cls._templates.get(template_type)
        
        if not template_class:
            # Default to classic if template not found
            template_class = ClassicPDFTemplate
        
        return template_class()
    
    @classmethod
    def register_template(cls, template_type: TemplateType, 
                         template_class: Type[BasePDFTemplate]):
        """Register a new template"""
        cls._templates[template_type] = template_class
    
    @classmethod
    def list_templates(cls) -> List[str]:
        """List available template names"""
        return [t.value for t in cls._templates.keys()]


def get_template(template_name: str = "classic") -> BasePDFTemplate:
    """Convenience function to get a template by name"""
    try:
        template_type = TemplateType(template_name.lower())
    except ValueError:
        template_type = TemplateType.CLASSIC
    
    return TemplateRegistry.get_template(template_type)