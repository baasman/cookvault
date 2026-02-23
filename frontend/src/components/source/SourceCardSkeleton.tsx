import React from 'react';
import { Skeleton } from '../ui/Skeleton';

/**
 * Skeleton loading state for SourceCard.
 * Matches the layout of the actual SourceCard component.
 */
const SourceCardSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden h-full flex flex-col" style={{ borderColor: '#e8d7cf' }}>
      {/* Header */}
      <div className="p-4 flex items-center gap-3 border-b" style={{ borderColor: '#e8d7cf' }}>
        {/* Favicon placeholder */}
        <Skeleton className="w-8 h-8 rounded flex-shrink-0" />

        {/* Source info placeholder */}
        <div className="flex-1 min-w-0">
          <Skeleton className="h-6 w-3/4 mb-1" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>

      {/* Content */}
      <div className="p-4 flex-grow flex flex-col justify-center">
        {/* Recipe count placeholder */}
        <div className="text-center">
          <Skeleton className="h-10 w-16 mx-auto mb-1" />
          <Skeleton className="h-4 w-12 mx-auto" />
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 pb-4">
        <div className="text-center">
          <Skeleton className="h-4 w-24 mx-auto" />
        </div>
      </div>
    </div>
  );
};

export { SourceCardSkeleton };
export default SourceCardSkeleton;
