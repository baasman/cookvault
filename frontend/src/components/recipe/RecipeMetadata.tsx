import React from 'react';
import { Link } from 'react-router-dom';
import { formatCookingTime } from '../../utils/formatters';
import { DIFFICULTY_COLORS } from '../../utils/constants';
import type { Recipe } from '../../types';

interface RecipeMetadataProps {
  recipe: Recipe;
  scaleFactor: number;
  desiredServings: number | undefined;
  currentUserId: string | undefined;
  isOwnRecipe: boolean;
}

const getDifficultyColor = (difficulty: string | undefined) => {
  return DIFFICULTY_COLORS[difficulty?.toLowerCase() ?? ''] ?? '#9b644b';
};

const RecipeMetadata: React.FC<RecipeMetadataProps> = ({
  recipe,
  scaleFactor,
  desiredServings,
  currentUserId,
  isOwnRecipe,
}) => {
  return (
    <>
      {/* Recipe Metadata */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="text-center p-3 bg-background-secondary rounded-lg">
          <div className="text-sm text-text-secondary mb-1">Prep Time</div>
          <div className="font-medium text-text-primary">{formatCookingTime(recipe.prep_time)}</div>
        </div>

        <div className="text-center p-3 bg-background-secondary rounded-lg">
          <div className="text-sm text-text-secondary mb-1">Cook Time</div>
          <div className="font-medium text-text-primary">{formatCookingTime(recipe.cook_time)}</div>
        </div>

        <div className="text-center p-3 bg-background-secondary rounded-lg">
          <div className="text-sm text-text-secondary mb-1">Servings</div>
          <div className="font-medium text-text-primary">
            {scaleFactor !== 1 && desiredServings ? (
              <>
                <span className="text-blue-600">{desiredServings}</span>
                <span className="text-xs text-text-secondary ml-1">
                  (from {recipe.servings})
                </span>
              </>
            ) : (
              recipe.servings || 'Not specified'
            )}
          </div>
        </div>

        <div className="text-center p-3 bg-background-secondary rounded-lg">
          <div className="text-sm text-text-secondary mb-1">Difficulty</div>
          <div className="font-medium" style={{color: getDifficultyColor(recipe.difficulty)}}>
            {recipe.difficulty ? recipe.difficulty.charAt(0).toUpperCase() + recipe.difficulty.slice(1) : 'Not specified'}
          </div>
        </div>
      </div>

      {/* Course Type */}
      {recipe.course_type && (
        <div className="mb-6">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-orange-100 text-orange-800">
            <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            {recipe.course_type}
          </span>
        </div>
      )}

      {/* User Information - Streamlined inline display */}
      {recipe.user && (recipe.is_public || recipe.user_id !== parseInt(currentUserId || '0')) && (
        <div className="mb-4 flex items-center text-sm text-text-secondary">
          <svg className="h-4 w-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
          </svg>
          <span>Uploaded by </span>
          <Link
            to={`/users/${recipe.user.id}`}
            className="font-medium text-blue-600 hover:text-blue-800 hover:underline transition-colors mx-1"
          >
            {recipe.user.first_name && recipe.user.last_name
              ? `${recipe.user.first_name} ${recipe.user.last_name}`
              : recipe.user.username
            }
          </Link>
          {recipe.created_at && (
            <span className="text-text-secondary">
              on {new Date(recipe.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
              })}
            </span>
          )}
        </div>
      )}

      {/* Tags */}
      {recipe.tags && recipe.tags.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-text-secondary mb-2">Tags</h3>
          <div className="flex flex-wrap gap-2">
            {recipe.tags.map((tag) => (
              <span
                key={tag.id}
                className="px-3 py-1 text-sm rounded-full bg-background-secondary text-text-secondary"
              >
                {tag.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Publish Restriction Notice - shown for own recipes that cannot be made public */}
      {isOwnRecipe && !recipe.is_public && recipe.can_be_published === false && (
        <div className="mb-6 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-3">
          <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <div>
            <p className="text-sm text-blue-700 font-medium">Personal Recipe</p>
            <p className="text-sm text-blue-600">
              {recipe.publish_restriction_reason || 'This recipe is saved for personal use only and cannot be shared publicly.'}
            </p>
          </div>
        </div>
      )}

      {/* Enhanced Cookbook Info */}
      {recipe.cookbook && (
        <div className="mb-6 p-4 bg-gradient-to-r from-background-secondary to-primary-50 rounded-lg border border-primary-200 hover:shadow-md transition-shadow">
          <div className="flex gap-4">
            {/* Cookbook Cover Thumbnail */}
            {recipe.cookbook.cover_image_url && (
              <Link
                to={`/cookbooks/${recipe.cookbook.id}`}
                className="flex-shrink-0"
              >
                <img
                  src={recipe.cookbook.cover_image_url}
                  alt={recipe.cookbook.title}
                  className="w-16 h-20 object-cover rounded shadow-sm hover:shadow-md transition-shadow"
                  onError={(e) => {
                    // Hide image if it fails to load
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                  }}
                />
              </Link>
            )}

            {/* Cookbook Details */}
            <div className="flex-grow">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">From Cookbook</h3>
                  <Link
                    to={`/cookbooks/${recipe.cookbook.id}`}
                    className="font-semibold text-lg text-text-primary hover:text-accent transition-colors block mb-1"
                  >
                    {recipe.cookbook.title}
                  </Link>

                  <div className="flex flex-wrap gap-3 text-sm text-text-secondary">
                    {recipe.cookbook.author && (
                      <span className="flex items-center">
                        <svg className="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        {recipe.cookbook.author}
                      </span>
                    )}

                    {recipe.cookbook.publisher && (
                      <span className="flex items-center">
                        <svg className="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H7m5 0v-9a2 2 0 00-2-2H7a2 2 0 00-2 2v9m14 0h2" />
                        </svg>
                        {recipe.cookbook.publisher}
                      </span>
                    )}

                    {recipe.cookbook.recipe_count > 0 && (
                      <span className="flex items-center">
                        <svg className="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                        {recipe.cookbook.recipe_count} recipes
                      </span>
                    )}

                    {recipe.cookbook.isbn && (
                      <span className="flex items-center">
                        <svg className="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                        </svg>
                        ISBN: {recipe.cookbook.isbn}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Source Info (for URL-imported recipes) */}
      {recipe.source_info && (
        <div className="mb-6 p-4 bg-gradient-to-r from-background-secondary to-gray-50 rounded-lg border border-gray-200 hover:shadow-md transition-shadow">
          <div className="flex items-center gap-4">
            {/* Source Favicon */}
            {recipe.source_info.favicon_url && (
              <Link
                to={`/sources/${recipe.source_info.id}`}
                className="flex-shrink-0"
              >
                <img
                  src={recipe.source_info.favicon_url}
                  alt={recipe.source_info.display_name}
                  className="w-10 h-10 rounded-lg shadow-sm hover:shadow-md transition-shadow"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                  }}
                />
              </Link>
            )}

            {/* Source Details */}
            <div className="flex-grow">
              <h3 className="text-xs font-medium text-text-secondary mb-1 uppercase tracking-wider">Imported From</h3>
              <Link
                to={`/sources/${recipe.source_info.id}`}
                className="font-semibold text-text-primary hover:text-accent transition-colors"
              >
                {recipe.source_info.display_name}
              </Link>
              {recipe.source_info.name && recipe.source_info.name !== recipe.source_info.domain && (
                <p className="text-sm text-text-secondary">{recipe.source_info.domain}</p>
              )}
            </div>

            {/* External link to original */}
            <a
              href={`https://${recipe.source_info.domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 p-2 text-text-secondary hover:text-accent transition-colors"
              title={`Visit ${recipe.source_info.domain}`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      )}

      {/* Recipe Groups Info */}
      {recipe.groups && recipe.groups.length > 0 && (
        <div className="p-4 bg-background-secondary rounded-lg">
          <h3 className="text-sm font-medium text-text-secondary mb-1">In Recipe Groups</h3>
          <div className="space-y-1">
            {recipe.groups.map((group) => (
              <div key={group.id}>
                <Link
                  to={`/recipe-groups/${group.id}`}
                  className="font-medium text-text-primary hover:text-accent transition-colors underline hover:no-underline"
                >
                  {group.name}
                </Link>
                {group.description && (
                  <p className="text-xs text-text-secondary">{group.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
};

export { RecipeMetadata };
