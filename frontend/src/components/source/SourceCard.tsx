import React from 'react';
import { Link } from 'react-router-dom';
import type { Source } from '../../types';

interface SourceCardProps {
  source: Source;
  onClick?: () => void;
}

const SourceCard: React.FC<SourceCardProps> = ({ source, onClick }) => {
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  return (
    <Link to={`/sources/${source.id}`} onClick={handleClick} className="h-full">
      <div className="group bg-white rounded-xl shadow-sm border transition-all duration-200 hover:shadow-md hover:border-accent/20 overflow-hidden h-full flex flex-col" style={{borderColor: '#e8d7cf'}}>
        {/* Source Header */}
        <div className="p-4 flex items-center gap-3 border-b" style={{borderColor: '#e8d7cf'}}>
          {/* Favicon */}
          <div className="flex-shrink-0">
            {source.favicon_url ? (
              <img
                src={source.favicon_url}
                alt={source.display_name}
                className="w-8 h-8 rounded"
                onError={(e) => {
                  // Fallback to placeholder if favicon fails to load
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  const sibling = target.nextElementSibling;
                  if (sibling) {
                    sibling.classList.remove('hidden');
                  }
                }}
              />
            ) : null}
            <div className={`w-8 h-8 rounded bg-primary-100 flex items-center justify-center ${source.favicon_url ? 'hidden' : ''}`}>
              <svg className="h-4 w-4 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
            </div>
          </div>

          {/* Source info */}
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-text-primary group-hover:text-accent transition-colors truncate">
              {source.display_name}
            </h3>
            {source.name && source.name !== source.domain && (
              <p className="text-xs text-text-secondary truncate">
                {source.domain}
              </p>
            )}
          </div>
        </div>

        {/* Source Content */}
        <div className="p-4 flex-grow flex flex-col justify-center">
          {/* Recipe count - prominent display */}
          <div className="text-center">
            <div className="text-4xl font-bold text-accent mb-1">
              {source.recipe_count}
            </div>
            <p className="text-sm text-text-secondary">
              recipe{source.recipe_count !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        {/* Footer with view link */}
        <div className="px-4 pb-4">
          <div className="text-center">
            <span className="inline-flex items-center text-sm text-accent font-medium group-hover:underline">
              View recipes
              <svg className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
};

export { SourceCard };
export default SourceCard;
