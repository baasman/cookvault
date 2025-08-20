/**
 * Component for displaying authenticated images with loading states
 */
import React, { useState, useEffect } from 'react';
import { useAuthenticatedImage } from '../../hooks/useAuthenticatedImage';

interface AuthenticatedImageProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  filename: string | null;
  fallback?: React.ReactNode;
  loadingIndicator?: React.ReactNode;
}

/**
 * Image component that handles JWT authentication for image loading
 */
export const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({
  filename,
  fallback,
  loadingIndicator,
  className = '',
  alt = '',
  ...imgProps
}) => {
  const { src, loading, error } = useAuthenticatedImage(filename);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [showImage, setShowImage] = useState(false);

  useEffect(() => {
    if (src) {
      // Preload the image before showing it
      const img = new Image();
      img.onload = () => {
        setImageLoaded(true);
        // Small delay to ensure smooth transition
        requestAnimationFrame(() => {
          setShowImage(true);
        });
      };
      img.src = src;
    } else {
      setImageLoaded(false);
      setShowImage(false);
    }
  }, [src]);

  // Show loading state only if no image is loaded yet
  if (loading && !src && !error) {
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

  if (error || (!src && !loading)) {
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

  return (
    <div className={`relative ${className}`}>
      {/* Show loading overlay while new image loads */}
      {loading && !imageLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-200 animate-pulse rounded z-10">
          <svg className="animate-spin h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      )}
      <img
        {...imgProps}
        src={src || undefined}
        alt={alt}
        className={`${className} transition-opacity duration-300 ${showImage ? 'opacity-100' : 'opacity-0'}`}
        onError={() => {
          console.error('Image failed to display:', filename);
          setImageLoaded(false);
          setShowImage(false);
        }}
        style={{ ...imgProps.style }}
      />
    </div>
  );
};