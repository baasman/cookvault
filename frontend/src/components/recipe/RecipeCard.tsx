import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { recipesApi } from '../../services/recipesApi';
import { useAuth } from '../../contexts/AuthContext';
import { AddToCollectionButton } from './AddToCollectionButton';
import { AddToGroupButton } from './AddToGroupButton';
import { CopyrightConsentModal } from '../ui';
import type { Recipe } from '../../types';
import toast from 'react-hot-toast';

interface RecipeCardProps {
  recipe: Recipe;
  onClick?: () => void;
  showPrivacyControls?: boolean;
  showAddToCollection?: boolean;
  showAddToGroup?: boolean;
}

const RecipeCard: React.FC<RecipeCardProps> = ({ recipe, onClick, showPrivacyControls = true, showAddToCollection = false, showAddToGroup = false }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [isTogglingPrivacy, setIsTogglingPrivacy] = useState(false);
  const [showCopyrightModal, setShowCopyrightModal] = useState(false);
  
  // Check if current user owns this recipe
  const isOwnRecipe = Boolean(
    user && 
    recipe.user_id && 
    user.id && 
    !isNaN(parseInt(user.id)) &&
    recipe.user_id === parseInt(user.id)
  );
  
  // Debug logging for button visibility issues
  console.log('RecipeCard Debug:', {
    recipeId: recipe.id,
    recipeTitle: recipe.title,
    recipeUserId: recipe.user_id,
    recipeUserIdType: typeof recipe.user_id,
    currentUserId: user?.id,
    currentUserIdType: typeof user?.id,
    parsedUserId: user?.id ? parseInt(user.id) : null,
    isOwnRecipe,
    userRole: user?.role,
    isInCollection: recipe.is_in_collection,
    hasIsInCollection: 'is_in_collection' in recipe,
    isPublic: recipe.is_public
  });
  
  // Check if current user can control this recipe's privacy
  const canControlPrivacy = user && (
    user.role === 'admin' || isOwnRecipe
  );
  


  // Mutation for toggling privacy
  const privacyMutation = useMutation({
    mutationFn: (params: { isPublic: boolean; consents?: Record<string, boolean> }) => 
      recipesApi.toggleRecipePrivacy(recipe.id, params.isPublic, params.consents),
    onMutate: () => {
      setIsTogglingPrivacy(true);
    },
    onSuccess: (updatedRecipe) => {
      // Update all recipe queries in the cache (they have different keys like ['recipes', page, searchTerm, filter])
      queryClient.setQueriesData(
        { queryKey: ['recipes'] }, 
        (oldData: any) => {
          if (!oldData) return oldData;
          return {
            ...oldData,
            recipes: oldData.recipes.map((r: Recipe) => 
              r.id === recipe.id ? updatedRecipe : r
            )
          };
        }
      );
      
      // Also update individual recipe cache if it exists
      queryClient.setQueryData(['recipe', recipe.id], updatedRecipe);
      
      toast.success(updatedRecipe.is_public ? 'Recipe published!' : 'Recipe made private');
      setIsTogglingPrivacy(false);
    },
    onError: (error) => {
      console.error('Privacy toggle failed:', error);
      toast.error('Failed to update recipe privacy');
      setIsTogglingPrivacy(false);
    }
  });

  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  const handlePrivacyToggle = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!canControlPrivacy || isTogglingPrivacy) {
      return;
    }
    
    // Only allow making private recipes public (public recipes cannot be made private)
    if (!recipe.is_public) {
      setShowCopyrightModal(true);
    }
    // Note: No else clause needed since button only shows for private recipes
  };

  const handleCopyrightConsent = (consents: Record<string, boolean>) => {
    setShowCopyrightModal(false);
    privacyMutation.mutate({ isPublic: true, consents });
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


  // Get the first image from the recipe and check for multiple images
  const primaryImage = recipe.images && recipe.images.length > 0 ? recipe.images[0] : null;
  const imageUrl = primaryImage ? `/api/images/${primaryImage.filename}` : null;
  const hasMultipleImages = recipe.images && recipe.images.length > 1;

  return (
    <>
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

            {/* Multi-image indicator - positioned on the left */}
            {hasMultipleImages && (
              <div className="absolute top-3 left-3 px-2 py-1 text-xs font-medium bg-black bg-opacity-75 text-white rounded-full flex items-center gap-1">
                <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/>
                </svg>
                <span>{recipe.images?.length} pages</span>
              </div>
            )}
            
            {/* Recipe badges */}
            <div className="absolute top-3 right-3 flex flex-col gap-2">
              {/* Ownership indicator */}
              {isOwnRecipe && (
                <div className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full flex items-center gap-1">
                  <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
                  </svg>
                  Mine
                </div>
              )}
              
              {/* Privacy badge */}
              <div className="flex items-center gap-1">
                {/* Privacy indicator */}
                <div className={`px-2 py-1 text-xs font-medium rounded-full flex items-center gap-1 ${
                  recipe.is_public 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-600'
                }`}>
                  {recipe.is_public ? (
                    <>
                      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                        <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd"/>
                      </svg>
                      Public
                    </>
                  ) : (
                    <>
                      <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd"/>
                      </svg>
                      Private
                    </>
                  )}
                </div>

                {/* Privacy toggle button (only for private recipes - public recipes cannot be made private) */}
                {canControlPrivacy && showPrivacyControls && !recipe.is_public && (
                  <button
                    onClick={handlePrivacyToggle}
                    disabled={isTogglingPrivacy}
                    className={`p-1 rounded-full transition-colors ${
                      isTogglingPrivacy 
                        ? 'bg-gray-200 cursor-not-allowed' 
                        : 'bg-white/80 hover:bg-white shadow-sm'
                    }`}
                    title="Make public"
                  >
                    {isTogglingPrivacy ? (
                      <svg className="h-3 w-3 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                      </svg>
                    ) : (
                      <svg className="h-3 w-3 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                        <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd"/>
                      </svg>
                    )}
                  </button>
                )}
              </div>

            </div>
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
            <div className="flex flex-wrap gap-1 min-h-[28px]">
              {recipe.tags && recipe.tags.length > 0 && (
                <>
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
                </>
              )}
            </div>

            {/* Add to Collection Button */}
            {showAddToCollection && (
              <div className="mt-3" onClick={(e) => e.stopPropagation()}>
                <AddToCollectionButton recipe={recipe} size="sm" />
              </div>
            )}

            {/* Add to Group Button */}
            {showAddToGroup && (
              <div className="mt-3" onClick={(e) => e.stopPropagation()}>
                <AddToGroupButton recipe={recipe} size="sm" />
              </div>
            )}

            {/* User info for public recipes */}
            {recipe.is_public && recipe.user && (
              <div className="mt-3 pt-3 border-t border-primary-200">
                <p className="text-xs text-text-secondary">
                  By: <span className="font-medium text-text-primary">
                    {recipe.user.first_name && recipe.user.last_name 
                      ? `${recipe.user.first_name} ${recipe.user.last_name}` 
                      : recipe.user.username}
                  </span>
                  {recipe.published_at && (
                    <span className="ml-2">
                      • Published {new Date(recipe.published_at).toLocaleDateString()}
                    </span>
                  )}
                </p>
              </div>
            )}

            {/* Cookbook info */}
            {recipe.cookbook && (
              <div className={`mt-3 pt-3 border-t border-primary-200 ${recipe.is_public && recipe.user ? 'mt-2 pt-2' : ''}`}>
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
      
      {/* Copyright Consent Modal */}
      <CopyrightConsentModal
        isOpen={showCopyrightModal}
        onClose={() => setShowCopyrightModal(false)}
        onConfirm={handleCopyrightConsent}
        recipeName={recipe.title}
        isLoading={isTogglingPrivacy}
      />
    </>
  );
};

export { RecipeCard };