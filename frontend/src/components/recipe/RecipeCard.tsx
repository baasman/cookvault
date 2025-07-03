import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { Recipe } from '../../types';

interface RecipeCardProps {
  recipe: Recipe;
  onClick?: () => void;
}

const RecipeCard: React.FC<RecipeCardProps> = ({ recipe, onClick }) => {
  const navigate = useNavigate();
  
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  const handleCookbookClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    navigate(`/cookbooks/${recipe.cookbook?.id}`);
  };

  const formatTime = (minutes: number | undefined) => {
    if (!minutes) return '';
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  const getDifficultyColor = (difficulty: string | undefined) => {
    switch (difficulty?.toLowerCase()) {
      case 'easy': return '#22c55e';
      case 'medium': return '#f59e0b';
      case 'hard': return '#ef4444';
      default: return '#9b644b';
    }
  };

  // Get the first image from the recipe
  const primaryImage = recipe.images && recipe.images.length > 0 ? recipe.images[0] : null;
  const imageUrl = primaryImage ? `/api/images/${primaryImage.filename}` : null;

  return (
    <Link to={`/recipes/${recipe.id}`} onClick={handleClick}>
      <div className="group bg-white rounded-xl shadow-sm border transition-all duration-200 hover:shadow-md hover:border-accent/20 overflow-hidden" style={{borderColor: '#e8d7cf'}}>
        {/* Recipe Image */}
        <div className="aspect-video bg-gradient-to-br from-background-secondary to-primary-200 relative overflow-hidden">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={recipe.title}
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
          <div className={`absolute inset-0 flex items-center justify-center ${imageUrl ? 'hidden' : ''}`}>
            <svg className="h-12 w-12 text-primary-300" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
          </div>
          
          {/* Recipe difficulty badge */}
          {recipe.difficulty && (
            <div className="absolute top-3 right-3">
              <span 
                className="px-2 py-1 text-xs font-medium text-white rounded-full"
                style={{backgroundColor: getDifficultyColor(recipe.difficulty)}}
              >
                {recipe.difficulty}
              </span>
            </div>
          )}
        </div>

        {/* Recipe Content */}
        <div className="p-4">
          {/* Recipe Title */}
          <h3 className="text-lg font-semibold text-text-primary group-hover:text-accent transition-colors line-clamp-2 mb-2">
            {recipe.title}
          </h3>

          {/* Recipe Description */}
          {recipe.description && (
            <p className="text-sm text-text-secondary line-clamp-2 mb-3">
              {recipe.description}
            </p>
          )}

          {/* Recipe Metadata */}
          <div className="flex items-center justify-between text-xs text-text-secondary mb-3">
            <div className="flex items-center space-x-3">
              {recipe.prep_time && (
                <div className="flex items-center space-x-1">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{formatTime(recipe.prep_time)}</span>
                </div>
              )}
              
              {recipe.cook_time && (
                <div className="flex items-center space-x-1">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
                  </svg>
                  <span>{formatTime(recipe.cook_time)}</span>
                </div>
              )}

              {recipe.servings && (
                <div className="flex items-center space-x-1">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <span>{recipe.servings}</span>
                </div>
              )}
            </div>
          </div>

          {/* Recipe Tags */}
          {recipe.tags && recipe.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {recipe.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag.id}
                  className="px-2 py-1 text-xs rounded-full bg-background-secondary text-text-secondary"
                >
                  {tag.name}
                </span>
              ))}
              {recipe.tags.length > 3 && (
                <span className="px-2 py-1 text-xs text-text-secondary">
                  +{recipe.tags.length - 3}
                </span>
              )}
            </div>
          )}

          {/* Cookbook info */}
          {recipe.cookbook && (
            <div className="mt-3 pt-3 border-t border-primary-200">
              <p className="text-xs text-text-secondary">
                From: <button 
                  onClick={handleCookbookClick}
                  className="font-medium text-text-primary hover:text-accent transition-colors underline cursor-pointer bg-transparent border-none p-0"
                >
                  {recipe.cookbook.title}
                </button>
                {recipe.page_number && ` • Page ${recipe.page_number}`}
              </p>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
};

export { RecipeCard };