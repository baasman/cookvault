import React from 'react';
import { Link } from 'react-router-dom';

interface RecipeGroup {
  id: number;
  name: string;
  description?: string;
  cover_image_url?: string;
  recipe_count: number;
  created_at: string;
  updated_at: string;
}

interface RecipeGroupCardProps {
  group: RecipeGroup;
  onClick?: () => void;
}

const RecipeGroupCard: React.FC<RecipeGroupCardProps> = ({ group, onClick }) => {
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <Link to={`/recipe-groups/${group.id}`} onClick={handleClick}>
      <div className="group bg-white rounded-xl shadow-sm border transition-all duration-200 hover:shadow-md hover:border-accent/20 overflow-hidden" style={{borderColor: '#e8d7cf'}}>
        {/* Group Cover */}
        <div className="aspect-video bg-gradient-to-br from-background-secondary to-primary-200 relative overflow-hidden">
          {group.cover_image_url ? (
            <img
              src={group.cover_image_url}
              alt={group.name}
              className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
              onError={(e) => {
                // Hide the image and show placeholder if loading fails
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                target.nextElementSibling?.classList.remove('hidden');
              }}
            />
          ) : null}
          
          {/* Placeholder - shown when no image or image fails to load */}
          <div className={`absolute inset-0 flex items-center justify-center ${group.cover_image_url ? 'hidden' : ''}`}>
            <div className="text-center">
              <svg className="h-12 w-12 text-primary-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <p className="text-xs text-primary-400 font-medium">Recipe Group</p>
            </div>
          </div>
          
          {/* Recipe count badge */}
          <div className="absolute top-3 right-3">
            <div className="px-2 py-1 text-xs font-medium bg-accent text-white rounded-full">
              {group.recipe_count} recipe{group.recipe_count !== 1 ? 's' : ''}
            </div>
          </div>
        </div>

        {/* Group Content */}
        <div className="p-4">
          {/* Group Name */}
          <h3 className="text-lg font-semibold text-text-primary group-hover:text-accent transition-colors line-clamp-2 mb-2">
            {group.name}
          </h3>

          {/* Group Description */}
          {group.description && (
            <p className="text-sm text-text-secondary line-clamp-2 mb-3">
              {group.description}
            </p>
          )}

          {/* Group Metadata */}
          <div className="flex items-center justify-between text-xs text-text-secondary">
            <div className="flex items-center space-x-1">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Updated {formatDate(group.updated_at)}</span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
};

export { RecipeGroupCard };