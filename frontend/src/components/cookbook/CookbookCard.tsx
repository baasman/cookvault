import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import type { Cookbook } from '../../types';
import { decodeHtmlEntities } from '../../utils/textUtils';
import { CookbookPurchaseButton } from '../payments';

interface CookbookCardProps {
  cookbook: Cookbook & {
    is_purchasable?: boolean;
    price?: number;
    has_purchased?: boolean;
    is_available_for_purchase?: boolean;
  };
  onClick?: () => void;
  showPurchaseButton?: boolean;
}

const CookbookCard: React.FC<CookbookCardProps> = ({ cookbook, onClick, showPurchaseButton = false }) => {
  const { user } = useAuth();
  
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  // Check if current user owns this cookbook
  const isOwnCookbook = user && cookbook.user_id && cookbook.user_id.toString() === user.id.toString();

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
          {/* Ownership indicator */}
          {isOwnCookbook && (
            <div className="absolute top-3 right-3 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full flex items-center gap-1 z-10">
              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
              </svg>
              Mine
            </div>
          )}
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
          <div className="absolute top-3 left-3">
            <span className="px-2 py-1 text-xs font-medium text-white rounded-full bg-accent">
              {cookbook.recipe_count} recipe{cookbook.recipe_count !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Price badge */}
          {cookbook.is_purchasable && cookbook.price && cookbook.price > 0 && (
            <div className="absolute top-3 right-3">
              <span className="px-2 py-1 text-xs font-medium text-white rounded-full bg-green-600">
                ${cookbook.price.toFixed(2)}
              </span>
            </div>
          )}
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

          {/* Purchase Button */}
          {showPurchaseButton && cookbook.is_purchasable && !isOwnCookbook && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <CookbookPurchaseButton
                cookbook={{
                  id: cookbook.id,
                  title: cookbook.title,
                  price: cookbook.price || 0,
                  is_purchasable: cookbook.is_purchasable || false,
                  has_purchased: cookbook.has_purchased,
                  is_available_for_purchase: cookbook.is_available_for_purchase,
                }}
                size="sm"
                onPurchaseSuccess={() => {
                  // Refresh the page or update the cookbook state
                  window.location.reload();
                }}
              />
            </div>
          )}
        </div>
      </div>
    </Link>
  );
};

export { CookbookCard };