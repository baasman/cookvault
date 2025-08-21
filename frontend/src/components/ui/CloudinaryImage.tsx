/**
 * Component for displaying images that may come from Cloudinary or local storage
 */
import React, { useState, useEffect } from 'react';
import { useAuthenticatedImage } from '../../hooks/useAuthenticatedImage';

interface CloudinaryImageProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  // Cloudinary URL (if available)
  cloudinaryUrl?: string | null;
  // Thumbnail URL for faster loading
  thumbnailUrl?: string | null;
  // Legacy filename for local images
  filename?: string | null;
  // Fallback component when image fails to load
  fallback?: React.ReactNode;
  // Loading indicator component
  loadingIndicator?: React.ReactNode;
  // Whether to prefer thumbnail for initial load
  preferThumbnail?: boolean;
}

/**
 * Image component that handles both Cloudinary and local authenticated images
 */
export const CloudinaryImage: React.FC<CloudinaryImageProps> = ({
  cloudinaryUrl,
  thumbnailUrl,
  filename,
  fallback,
  loadingIndicator,
  preferThumbnail = false,
  className = '',
  alt = '',
  ...imgProps
}) => {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [showImage, setShowImage] = useState(false);
  const [currentSrc, setCurrentSrc] = useState<string | null>(null);
  const [isLoadingCloudinary, setIsLoadingCloudinary] = useState(false);
  const [cloudinaryError, setCloudinaryError] = useState(false);
  
  // Use authenticated image hook for legacy local images
  const { src: authenticatedSrc, loading: authLoading, error: authError } = useAuthenticatedImage(
    // Only use authenticated image if we don't have Cloudinary URL
    (!cloudinaryUrl && !thumbnailUrl) ? filename || null : null
  );

  // Determine the best image source to use
  useEffect(() => {
    setImageLoaded(false);
    setShowImage(false);
    setCloudinaryError(false);

    let imageUrl: string | null = null;

    // Priority order:
    // 1. Cloudinary thumbnail (if preferThumbnail and available)
    // 2. Cloudinary main URL
    // 3. Authenticated local image
    if (preferThumbnail && thumbnailUrl) {
      imageUrl = thumbnailUrl;
    } else if (cloudinaryUrl) {
      imageUrl = cloudinaryUrl;
    } else if (authenticatedSrc) {
      imageUrl = authenticatedSrc;
    }

    if (imageUrl) {
      setCurrentSrc(imageUrl);
      
      // For Cloudinary URLs, set loading state
      if (cloudinaryUrl && imageUrl.includes('cloudinary')) {
        setIsLoadingCloudinary(true);
      }
      
      // Preload the image
      const img = new Image();
      img.onload = () => {
        setImageLoaded(true);
        setIsLoadingCloudinary(false);
        requestAnimationFrame(() => {
          setShowImage(true);
        });
      };
      img.onerror = () => {
        setIsLoadingCloudinary(false);
        if (imageUrl?.includes('cloudinary')) {
          setCloudinaryError(true);
          // If Cloudinary fails and we have a filename, try authenticated image
          if (filename && !authenticatedSrc) {
            // This will trigger the useAuthenticatedImage hook to try loading
            setCurrentSrc(null);
          }
        }
      };
      img.src = imageUrl;
    } else {
      setCurrentSrc(null);
    }
  }, [cloudinaryUrl, thumbnailUrl, authenticatedSrc, preferThumbnail, filename]);

  // Determine loading state
  const isLoading = isLoadingCloudinary || (authLoading && !cloudinaryUrl && !thumbnailUrl);
  
  // Determine error state
  const hasError = (cloudinaryError && authError) || (authError && !cloudinaryUrl && !thumbnailUrl);

  // Show loading state
  if (isLoading && !currentSrc) {
    return (
      <div className={`flex items-center justify-center relative ${className}`}>
        {loadingIndicator || (
          <div className="animate-pulse bg-gray-200 rounded" style={{ width: '100%', height: '100%' }}>
            <div className="flex items-center justify-center h-full">
              <svg className="animate-spin h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Show error state
  if (hasError || (!currentSrc && !isLoading)) {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        {fallback || (
          <div className="bg-gradient-to-br from-gray-100 to-gray-200 rounded flex items-center justify-center w-full h-full">
            <svg className="h-12 w-12 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
          </div>
        )}
      </div>
    );
  }

  // Render image
  return (
    <div className={`relative ${className}`}>
      {/* Show loading overlay while image loads */}
      {(isLoading && currentSrc) && !imageLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-200 animate-pulse rounded z-10">
          <svg className="animate-spin h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      )}
      
      <img
        {...imgProps}
        src={currentSrc || undefined}
        alt={alt}
        className={`${className} transition-opacity duration-300 ${showImage ? 'opacity-100' : 'opacity-0'}`}
        onError={() => {
          console.error('Image failed to display:', { cloudinaryUrl, filename, currentSrc });
          setImageLoaded(false);
          setShowImage(false);
          
          // If Cloudinary image failed and we have a filename, try authenticated fallback
          if (currentSrc?.includes('cloudinary') && filename) {
            setCloudinaryError(true);
          }
        }}
        onLoad={() => {
          if (!imageLoaded) {
            setImageLoaded(true);
            setIsLoadingCloudinary(false);
            requestAnimationFrame(() => {
              setShowImage(true);
            });
          }
        }}
        style={{ ...imgProps.style }}
      />
    </div>
  );
};