import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recipesApi } from '../../services/recipesApi';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';

interface StarRatingProps {
  recipeId: number;
  readOnly?: boolean;
  size?: 'sm' | 'md' | 'lg';
  showCount?: boolean;
  className?: string;
}

const StarRating: React.FC<StarRatingProps> = ({
  recipeId,
  readOnly = false,
  size = 'md',
  showCount = true,
  className = '',
}) => {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [hoverRating, setHoverRating] = useState<number | null>(null);

  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  // Fetch rating data
  const { data: ratingData, isLoading } = useQuery({
    queryKey: ['recipe-rating', recipeId],
    queryFn: () => recipesApi.getRating(recipeId),
    staleTime: 30000, // 30 seconds
  });

  // Submit rating mutation
  const submitMutation = useMutation({
    mutationFn: (rating: number) => recipesApi.submitRating(recipeId, rating),
    onSuccess: (data) => {
      queryClient.setQueryData(['recipe-rating', recipeId], data);
      toast.success('Rating saved!');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to save rating');
    },
  });

  // Delete rating mutation
  const deleteMutation = useMutation({
    mutationFn: () => recipesApi.deleteRating(recipeId),
    onSuccess: (data) => {
      queryClient.setQueryData(['recipe-rating', recipeId], {
        aggregate: data.aggregate,
        user_rating: null,
      });
      toast.success('Rating removed');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to remove rating');
    },
  });

  const aggregate = ratingData?.aggregate;
  const userRating = ratingData?.user_rating;
  const averageRating = aggregate?.average_rating ?? 0;
  const ratingCount = aggregate?.rating_count ?? 0;

  const handleStarClick = useCallback(
    (rating: number) => {
      if (readOnly || !isAuthenticated) return;

      // If clicking the same star as current rating, remove the rating
      if (userRating && userRating.rating === rating) {
        deleteMutation.mutate();
      } else {
        submitMutation.mutate(rating);
      }
    },
    [readOnly, isAuthenticated, userRating, deleteMutation, submitMutation]
  );

  const handleMouseEnter = useCallback(
    (rating: number) => {
      if (readOnly || !isAuthenticated) return;
      setHoverRating(rating);
    },
    [readOnly, isAuthenticated]
  );

  const handleMouseLeave = useCallback(() => {
    setHoverRating(null);
  }, []);

  // Determine which rating to display
  const displayRating = hoverRating ?? (userRating?.rating || averageRating);
  const isInteractive = !readOnly && isAuthenticated;
  const isPending = submitMutation.isPending || deleteMutation.isPending;

  // Star rendering
  const renderStar = (index: number) => {
    const starNumber = index + 1;
    const filled = starNumber <= displayRating;
    const halfFilled = !filled && starNumber - 0.5 <= displayRating;
    const isUserRating = userRating && starNumber <= userRating.rating;
    const isHovered = hoverRating && starNumber <= hoverRating;

    // Determine star color
    let starColor = 'text-gray-300';
    if (filled || halfFilled) {
      if (isUserRating && !isHovered) {
        starColor = 'text-yellow-500'; // User's rating
      } else if (isHovered) {
        starColor = 'text-yellow-400'; // Hover preview
      } else {
        starColor = 'text-yellow-400'; // Average rating
      }
    }

    return (
      <button
        key={index}
        type="button"
        disabled={!isInteractive || isPending}
        onClick={() => handleStarClick(starNumber)}
        onMouseEnter={() => handleMouseEnter(starNumber)}
        onMouseLeave={handleMouseLeave}
        className={`
          ${sizeClasses[size]}
          ${isInteractive ? 'cursor-pointer hover:scale-110' : 'cursor-default'}
          transition-all duration-100
          focus:outline-none
          disabled:cursor-not-allowed
          ${starColor}
        `}
        aria-label={`Rate ${starNumber} stars`}
      >
        {filled || halfFilled ? (
          <svg fill="currentColor" viewBox="0 0 24 24" className="w-full h-full">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        ) : (
          <svg
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            viewBox="0 0 24 24"
            className="w-full h-full"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
            />
          </svg>
        )}
      </button>
    );
  };

  if (isLoading) {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        {[0, 1, 2, 3, 4].map((index) => (
          <div
            key={index}
            className={`${sizeClasses[size]} bg-gray-200 rounded animate-pulse`}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {/* Stars */}
      <div className="flex items-center" onMouseLeave={handleMouseLeave}>
        {[0, 1, 2, 3, 4].map(renderStar)}
      </div>

      {/* Rating info */}
      {showCount && (
        <span className={`${textSizeClasses[size]} text-text-secondary ml-1`}>
          {ratingCount > 0 ? (
            <>
              <span className="font-medium">{averageRating.toFixed(1)}</span>
              <span className="text-gray-400 mx-1">·</span>
              <span>
                {ratingCount} {ratingCount === 1 ? 'rating' : 'ratings'}
              </span>
            </>
          ) : (
            <span className="text-gray-400">No ratings yet</span>
          )}
        </span>
      )}

      {/* User rating indicator */}
      {userRating && !readOnly && (
        <span className={`${textSizeClasses[size]} text-blue-600 ml-2`}>
          (Your rating: {userRating.rating})
        </span>
      )}

      {/* Login prompt for interactive mode */}
      {!readOnly && !isAuthenticated && (
        <span className={`${textSizeClasses[size]} text-gray-400 ml-2 italic`}>
          Sign in to rate
        </span>
      )}

      {/* Loading indicator */}
      {isPending && (
        <svg
          className={`${sizeClasses[size]} animate-spin text-gray-400 ml-1`}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
    </div>
  );
};

export { StarRating };
