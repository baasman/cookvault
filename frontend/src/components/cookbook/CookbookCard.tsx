import React from 'react';
import { Link } from 'react-router-dom';
import type { Cookbook } from '../../types';
import { decodeHtmlEntities } from '../../utils/textUtils';

interface CookbookCardProps {
  cookbook: Cookbook;
  onClick?: () => void;
}

const CookbookCard: React.FC<CookbookCardProps> = ({ cookbook, onClick }) => {
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.getFullYear().toString();
    } catch {
      return '';
    }
  };

  return (
    <Link to={`/cookbooks/${cookbook.id}`} onClick={handleClick}>
      <div className="group bg-white rounded-xl shadow-sm border transition-all duration-200 hover:shadow-md hover:border-accent/20 overflow-hidden" style={{borderColor: '#e8d7cf'}}>
        {/* Cookbook Cover */}
        <div className="aspect-[3/4] bg-gradient-to-br from-background-secondary to-primary-200 relative overflow-hidden">
          {cookbook.cover_image_url ? (
            <img 
              src={cookbook.cover_image_url} 
              alt={cookbook.title}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Fallback to placeholder if image fails to load
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                target.nextElementSibling?.classList.remove('hidden');
              }}
            />
          ) : null}
          
          {/* Placeholder when no cover image */}
          <div className={`absolute inset-0 flex items-center justify-center ${cookbook.cover_image_url ? 'hidden' : ''}`}>
            <div className="text-center px-4">
              <svg className="h-12 w-12 mx-auto text-primary-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={1} 
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" 
                />
              </svg>
              <p className="text-xs text-primary-400 font-medium leading-tight">{cookbook.title}</p>
            </div>
          </div>
          
          {/* Recipe count badge */}
          <div className="absolute top-3 right-3">
            <span className="px-2 py-1 text-xs font-medium text-white rounded-full bg-accent">
              {cookbook.recipe_count} recipe{cookbook.recipe_count !== 1 ? 's' : ''}
            </span>
          </div>
        </div>

        {/* Cookbook Content */}
        <div className="p-4">
          {/* Cookbook Title */}
          <h3 className="text-lg font-semibold text-text-primary group-hover:text-accent transition-colors line-clamp-2 mb-1">
            {cookbook.title}
          </h3>

          {/* Author */}
          {cookbook.author && (
            <p className="text-sm text-text-secondary mb-2">
              by {cookbook.author}
            </p>
          )}

          {/* Description */}
          {cookbook.description && (
            <p className="text-xs text-text-secondary line-clamp-4 mb-3 description-text-compact">
              {decodeHtmlEntities(cookbook.description)}
            </p>
          )}

          {/* Metadata */}
          <div className="text-xs text-text-secondary space-y-1">
            {cookbook.publisher && (
              <div className="flex items-center">
                <svg className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H7m5 0v-9a2 2 0 00-2-2H7a2 2 0 00-2 2v9m14 0h2" />
                </svg>
                <span>{cookbook.publisher}</span>
              </div>
            )}
            
            {cookbook.publication_date && (
              <div className="flex items-center">
                <svg className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>{formatDate(cookbook.publication_date)}</span>
              </div>
            )}

            {cookbook.isbn && (
              <div className="flex items-center">
                <svg className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                </svg>
                <span>ISBN: {cookbook.isbn}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
};

export { CookbookCard };