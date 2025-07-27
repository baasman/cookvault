import React, { useState, useEffect, useRef } from 'react';
import type { Recipe, RecipeImage } from '../../types';

interface RecipeImageCarouselProps {
  recipe: Recipe;
  className?: string;
}

const RecipeImageCarousel: React.FC<RecipeImageCarouselProps> = ({ recipe, className = '' }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);
  const carouselRef = useRef<HTMLDivElement>(null);

  // Sort images by image_order, fallback to id if order is not set
  const sortedImages = recipe.images 
    ? [...recipe.images].sort((a, b) => (a.image_order || a.id) - (b.image_order || b.id))
    : [];

  const hasMultipleImages = sortedImages.length > 1;

  // Reset current index if it's out of bounds
  useEffect(() => {
    if (currentIndex >= sortedImages.length && sortedImages.length > 0) {
      setCurrentIndex(0);
    }
  }, [sortedImages.length, currentIndex]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (!showModal) return;
      
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        goToPrevious();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        goToNext();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        setShowModal(false);
      }
    };

    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [showModal, currentIndex, sortedImages.length]);

  const goToNext = () => {
    setCurrentIndex((prev) => (prev + 1) % sortedImages.length);
  };

  const goToPrevious = () => {
    setCurrentIndex((prev) => (prev - 1 + sortedImages.length) % sortedImages.length);
  };

  const goToIndex = (index: number) => {
    setCurrentIndex(index);
  };

  // Touch/swipe handling for mobile
  const minSwipeDistance = 50;

  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe && hasMultipleImages) {
      goToNext();
    }
    if (isRightSwipe && hasMultipleImages) {
      goToPrevious();
    }
  };

  if (!sortedImages.length) {
    // No images placeholder
    return (
      <div className={`aspect-square bg-gradient-to-br from-background-secondary to-primary-200 rounded-xl flex items-center justify-center ${className}`}>
        <svg className="h-16 w-16 text-primary-300" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
        </svg>
      </div>
    );
  }

  const currentImage = sortedImages[currentIndex];
  const imageUrl = `/api/images/${currentImage.filename}`;

  return (
    <>
      <style jsx>{`
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
      <div className={`relative ${className}`}>
        {/* Multi-image indicator badge */}
        {hasMultipleImages && (
          <div className="absolute top-3 right-3 z-10 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded-full flex items-center space-x-1">
            <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
              <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/>
            </svg>
            <span>{currentIndex + 1} of {sortedImages.length}</span>
            {currentImage.page_number && (
              <span>• Page {currentImage.page_number}</span>
            )}
          </div>
        )}

        {/* Main image display */}
        <div 
          ref={carouselRef}
          className="aspect-square bg-gradient-to-br from-background-secondary to-primary-200 rounded-xl overflow-hidden relative group"
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          role="img"
          aria-label={`Recipe image ${currentIndex + 1} of ${sortedImages.length}${currentImage.page_number ? `, page ${currentImage.page_number}` : ''}`}
        >
          <img
            src={imageUrl}
            alt={`${recipe.title} - Image ${currentIndex + 1}`}
            className="w-full h-full object-cover cursor-pointer"
            onClick={() => setShowModal(true)}
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
              target.nextElementSibling?.classList.remove('hidden');
            }}
          />
          
          {/* Fallback placeholder */}
          <div className="hidden absolute inset-0 flex items-center justify-center">
            <svg className="h-16 w-16 text-primary-300" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
          </div>

          {/* View hint overlay */}
          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-200 cursor-pointer flex items-center justify-center opacity-0 group-hover:opacity-100">
            <div className="text-white text-center">
              <svg className="h-8 w-8 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
              </svg>
              <span className="text-sm font-medium">View Full Size</span>
            </div>
          </div>

          {/* Navigation arrows for multiple images */}
          {hasMultipleImages && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  goToPrevious();
                }}
                className="absolute left-2 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-75 text-white rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label="Previous image"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  goToNext();
                }}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-75 text-white rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label="Next image"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </>
          )}
        </div>

        {/* Thumbnail navigation strip for multiple images */}
        {hasMultipleImages && (
          <div 
            className="mt-3 flex space-x-2 overflow-x-auto pb-2 scrollbar-hide"
            role="tablist"
            aria-label="Recipe images navigation"
          >
            {sortedImages.map((image, index) => (
              <button
                key={image.id}
                onClick={() => goToIndex(index)}
                className={`flex-shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-lg overflow-hidden border-2 transition-all focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1 ${
                  index === currentIndex 
                    ? 'border-accent shadow-md ring-2 ring-accent ring-offset-1' 
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                role="tab"
                aria-selected={index === currentIndex}
                aria-controls={`image-panel-${index}`}
                aria-label={`View image ${index + 1}${image.page_number ? ` (Page ${image.page_number})` : ''}`}
                tabIndex={index === currentIndex ? 0 : -1}
              >
                <img
                  src={`/api/images/${image.filename}`}
                  alt={`Thumbnail ${index + 1}`}
                  className="w-full h-full object-cover"
                />
                {image.page_number && (
                  <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-75 text-white text-xs text-center py-1">
                    {image.page_number}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Full-size modal */}
      {showModal && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50" 
          onClick={() => setShowModal(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Full size recipe image viewer"
        >
          <div 
            className="relative max-w-6xl max-h-screen w-full h-full flex items-center justify-center p-4"
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
          >
            {/* Close button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowModal(false);
              }}
              className="absolute top-4 right-4 text-white bg-black bg-opacity-50 rounded-full p-3 hover:bg-opacity-75 transition-colors z-10 focus:outline-none focus:ring-2 focus:ring-white"
              aria-label="Close image viewer"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Image info */}
            <div className="absolute top-4 left-4 text-white bg-black bg-opacity-50 rounded-lg px-3 py-2 z-10">
              <div className="text-sm font-medium" role="status" aria-live="polite">
                Image {currentIndex + 1} of {sortedImages.length}
                {currentImage.page_number && ` • Page ${currentImage.page_number}`}
              </div>
            </div>

            {/* Main modal image */}
            <img
              src={imageUrl}
              alt={`${recipe.title} - Image ${currentIndex + 1}`}
              className="max-w-full max-h-full object-contain"
              onClick={(e) => e.stopPropagation()}
            />

            {/* Navigation arrows in modal */}
            {hasMultipleImages && (
              <>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    goToPrevious();
                  }}
                  className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-75 text-white rounded-full p-3 transition-colors focus:outline-none focus:ring-2 focus:ring-white"
                  aria-label="Previous image"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    goToNext();
                  }}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-75 text-white rounded-full p-3 transition-colors focus:outline-none focus:ring-2 focus:ring-white"
                  aria-label="Next image"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </>
            )}

            {/* Thumbnail strip in modal */}
            {hasMultipleImages && (
              <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex space-x-2 bg-black bg-opacity-50 rounded-lg p-2">
                {sortedImages.map((image, index) => (
                  <button
                    key={image.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      goToIndex(index);
                    }}
                    className={`w-12 h-12 rounded overflow-hidden border transition-all ${
                      index === currentIndex 
                        ? 'border-accent border-2' 
                        : 'border-gray-400 hover:border-gray-200'
                    }`}
                    aria-label={`Go to image ${index + 1}`}
                  >
                    <img
                      src={`/api/images/${image.filename}`}
                      alt={`Thumbnail ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export { RecipeImageCarousel };