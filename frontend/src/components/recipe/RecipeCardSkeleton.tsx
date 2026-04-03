import React from 'react';
import { Skeleton } from '../ui/Skeleton';

/**
 * Skeleton loading state for RecipeCard.
 * Matches the layout of the actual RecipeCard component.
 */
const RecipeCardSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden" style={{ borderColor: '#e8d7cf' }}>
      {/* Image placeholder */}
      <Skeleton className="w-full h-48" />

      {/* Content */}
      <div className="p-4">
        {/* Title */}
        <Skeleton className="h-6 w-3/4 mb-2" />

        {/* Description */}
        <Skeleton className="h-4 w-full mb-1" />
        <Skeleton className="h-4 w-2/3 mb-4" />

        {/* Meta info (time, servings) */}
        <div className="flex items-center gap-4">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-20" />
        </div>
      </div>
    </div>
  );
};

export { RecipeCardSkeleton };
