import React from 'react';
import { Skeleton } from '../ui/Skeleton';

/**
 * Skeleton loading state for CookbookCard.
 * Matches the layout of the actual CookbookCard component.
 */
const CookbookCardSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden" style={{ borderColor: '#e8d7cf' }}>
      {/* Cover image placeholder */}
      <Skeleton className="w-full h-40" />

      {/* Content */}
      <div className="p-4">
        {/* Title */}
        <Skeleton className="h-6 w-3/4 mb-2" />

        {/* Author */}
        <Skeleton className="h-4 w-1/2 mb-3" />

        {/* Description */}
        <Skeleton className="h-4 w-full mb-1" />
        <Skeleton className="h-4 w-4/5 mb-4" />

        {/* Recipe count */}
        <Skeleton className="h-4 w-24" />
      </div>
    </div>
  );
};

export { CookbookCardSkeleton };
