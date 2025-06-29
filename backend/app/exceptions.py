class RecipeProcessingError(Exception):
    """Base exception for recipe processing errors."""
    pass


class OCRExtractionError(RecipeProcessingError):
    """Raised when OCR text extraction fails."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class ImagePreprocessingError(RecipeProcessingError):
    """Raised when image preprocessing fails."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class RecipeParsingError(RecipeProcessingError):
    """Raised when recipe text parsing fails."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error