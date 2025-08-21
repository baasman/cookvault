import os
import logging
from typing import Optional, Dict, Any, Tuple
from io import BytesIO

import cloudinary
import cloudinary.uploader
import cloudinary.api
from PIL import Image
from flask import current_app

logger = logging.getLogger(__name__)


class CloudinaryService:
    """Service for handling image uploads and management with Cloudinary"""
    
    def __init__(self):
        self._initialized = False
        self._init_cloudinary()
    
    def _init_cloudinary(self):
        """Initialize Cloudinary configuration"""
        try:
            from flask import has_app_context
            
            # Skip initialization if no app context (during startup)
            if not has_app_context():
                self._initialized = False
                return
                
            cloudinary.config(
                cloud_name=current_app.config.get('CLOUDINARY_CLOUD_NAME'),
                api_key=current_app.config.get('CLOUDINARY_API_KEY'),
                api_secret=current_app.config.get('CLOUDINARY_API_SECRET')
            )
            
            # Verify configuration
            if not all([
                current_app.config.get('CLOUDINARY_CLOUD_NAME'),
                current_app.config.get('CLOUDINARY_API_KEY'),
                current_app.config.get('CLOUDINARY_API_SECRET')
            ]):
                raise ValueError("Missing Cloudinary configuration")
            
            self._initialized = True
            logger.info("Cloudinary initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cloudinary: {e}")
            self._initialized = False
    
    def is_enabled(self) -> bool:
        """Check if Cloudinary is enabled and properly configured"""
        # Try to initialize if not already done (for requests after startup)
        if not self._initialized:
            self._init_cloudinary()
            
        return (
            current_app.config.get('USE_CLOUDINARY', False) and 
            self._initialized
        )
    
    def upload_image(
        self, 
        image_data: bytes, 
        filename: str,
        folder: str = "recipes",
        generate_thumbnail: bool = True
    ) -> Dict[str, Any]:
        """
        Upload an image to Cloudinary with automatic optimization
        
        Args:
            image_data: Raw image bytes
            filename: Original filename (used for public_id generation)
            folder: Cloudinary folder to upload to
            generate_thumbnail: Whether to generate a thumbnail version
            
        Returns:
            Dict containing Cloudinary response with URLs and metadata
        """
        if not self.is_enabled():
            raise RuntimeError("Cloudinary service is not enabled or configured")
        
        try:
            # Generate a unique public_id
            base_name = os.path.splitext(filename)[0]
            public_id = f"{folder}/{base_name}"
            
            # Upload main image with optimization
            upload_result = cloudinary.uploader.upload(
                image_data,
                public_id=public_id,
                folder=folder,
                resource_type="image",
                format="jpg",  # Convert to JPG for consistency and smaller size
                quality="auto:good",  # Automatic quality optimization
                fetch_format="auto",  # Serve in optimal format (WebP, AVIF when supported)
                width=1200,  # Max width for recipe images
                height=1200,  # Max height for recipe images
                crop="limit",  # Don't upscale, only downscale if needed
                overwrite=True,  # Allow overwriting existing images
                unique_filename=True,  # Ensure unique filenames
                use_filename=False,  # Don't use original filename in public_id
            )
            
            result = {
                'public_id': upload_result['public_id'],
                'url': upload_result['secure_url'],
                'width': upload_result['width'],
                'height': upload_result['height'],
                'bytes': upload_result['bytes'],
                'format': upload_result['format'],
                'created_at': upload_result['created_at']
            }
            
            # Generate thumbnail if requested
            if generate_thumbnail:
                try:
                    thumbnail_url = cloudinary.utils.cloudinary_url(
                        upload_result['public_id'],
                        width=300,
                        height=300,
                        crop="fill",
                        quality="auto:good",
                        fetch_format="auto"
                    )[0]
                    result['thumbnail_url'] = thumbnail_url
                except Exception as e:
                    logger.warning(f"Failed to generate thumbnail URL: {e}")
                    result['thumbnail_url'] = result['url']  # Fallback to main image
            
            logger.info(f"Successfully uploaded image to Cloudinary: {public_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload image to Cloudinary: {e}")
            raise RuntimeError(f"Cloudinary upload failed: {str(e)}")
    
    def delete_image(self, public_id: str) -> bool:
        """
        Delete an image from Cloudinary
        
        Args:
            public_id: The Cloudinary public ID of the image to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Cloudinary service is not enabled, cannot delete image")
            return False
        
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type="image")
            success = result.get('result') == 'ok'
            
            if success:
                logger.info(f"Successfully deleted image from Cloudinary: {public_id}")
            else:
                logger.warning(f"Failed to delete image from Cloudinary: {public_id}, result: {result}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting image from Cloudinary: {e}")
            return False
    
    def get_image_info(self, public_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an image from Cloudinary
        
        Args:
            public_id: The Cloudinary public ID of the image
            
        Returns:
            Dict with image information or None if not found
        """
        if not self.is_enabled():
            return None
        
        try:
            result = cloudinary.api.resource(public_id, resource_type="image")
            return {
                'public_id': result['public_id'],
                'url': result['secure_url'],
                'width': result['width'],
                'height': result['height'],
                'bytes': result['bytes'],
                'format': result['format'],
                'created_at': result['created_at']
            }
            
        except Exception as e:
            logger.error(f"Error getting image info from Cloudinary: {e}")
            return None
    
    def optimize_image_for_upload(self, image_data: bytes, max_size_mb: int = 8) -> bytes:
        """
        Optimize image before uploading to reduce size and improve quality
        
        Args:
            image_data: Raw image bytes
            max_size_mb: Maximum file size in MB
            
        Returns:
            Optimized image bytes
        """
        try:
            # Open image with PIL
            with Image.open(BytesIO(image_data)) as img:
                # Convert RGBA to RGB if necessary
                if img.mode == 'RGBA':
                    # Create white background
                    white_bg = Image.new('RGB', img.size, (255, 255, 255))
                    white_bg.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
                    img = white_bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Apply basic optimization
                max_dimension = current_app.config.get('MAX_IMAGE_DIMENSION', 1200)
                if img.width > max_dimension or img.height > max_dimension:
                    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                
                # Save optimized image
                output = BytesIO()
                quality = current_app.config.get('JPEG_QUALITY', 85)
                img.save(output, format='JPEG', quality=quality, optimize=True)
                
                optimized_data = output.getvalue()
                
                # Check if size is acceptable
                size_mb = len(optimized_data) / (1024 * 1024)
                if size_mb > max_size_mb:
                    # Further reduce quality if needed
                    quality = max(60, int(quality * (max_size_mb / size_mb)))
                    output = BytesIO()
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                    optimized_data = output.getvalue()
                
                logger.info(f"Optimized image: {len(image_data)} -> {len(optimized_data)} bytes")
                return optimized_data
                
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            # Return original data if optimization fails
            return image_data
    
    def generate_transformation_url(
        self, 
        public_id: str, 
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: str = "limit",
        quality: str = "auto:good"
    ) -> str:
        """
        Generate a transformed image URL
        
        Args:
            public_id: The Cloudinary public ID
            width: Target width
            height: Target height  
            crop: Crop mode
            quality: Quality setting
            
        Returns:
            Transformed image URL
        """
        try:
            transformations = {
                'quality': quality,
                'fetch_format': 'auto'
            }
            
            if width:
                transformations['width'] = width
            if height:
                transformations['height'] = height
            if width or height:
                transformations['crop'] = crop
            
            url, _ = cloudinary.utils.cloudinary_url(public_id, **transformations)
            return url
            
        except Exception as e:
            logger.error(f"Error generating transformation URL: {e}")
            # Return a basic URL as fallback
            return f"https://res.cloudinary.com/{current_app.config.get('CLOUDINARY_CLOUD_NAME')}/image/upload/{public_id}"


# Global service instance
cloudinary_service = CloudinaryService()