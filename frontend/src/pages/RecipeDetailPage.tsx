import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { recipesApi } from '../services/recipesApi';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui';
import { RecipeImageCarousel } from '../components/recipe/RecipeImageCarousel';
import { RecipeEditForm } from '../components/recipe/RecipeEditForm';
import { AddToCollectionButton } from '../components/recipe/AddToCollectionButton';
import { CopyRecipeButton } from '../components/recipe/CopyRecipeButton';
import { AddToGroupButton } from '../components/recipe/AddToGroupButton';
import { MakePublicButton } from '../components/recipe/MakePublicButton';
import { FeatureToggleButton } from '../components/recipe/FeatureToggleButton';
import { ShareButton } from '../components/recipe/ShareButton';
import { HaveMadeButton } from '../components/recipe/HaveMadeButton';
import { WantToMakeButton } from '../components/recipe/WantToMakeButton';
import { RecipeActionsDropdown } from '../components/recipe/RecipeActionsDropdown';
import { NotesSection } from '../components/recipe/NotesSection';
import { CommentsSection } from '../components/recipe/CommentsSection';
import { PaywallMessage } from '../components/recipe/PaywallMessage';
import { RecipeScaler } from '../components/recipe/RecipeScaler';
import { StarRating } from '../components/recipe/StarRating';
import { ExportButton } from '../components/export';
import { ActionSheet, type ActionSheetOption } from '../components/ui/ActionSheet';
import { CookingMode } from '../components/cooking-mode/CookingMode';
import { scaleQuantity, isScalableQuantity } from '../utils/recipeScaling';
import { isIOS, isNativePlatform } from '../utils/platform';
import type { Recipe } from '../types';

// Check if we're on native iOS
const isNativeIOS = (): boolean => isIOS() && isNativePlatform();

const RecipeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const queryClient = useQueryClient();
  const recipeId = id ? parseInt(id, 10) : null;
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [scaleFactor, setScaleFactor] = useState(1);
  const [showCookingMode, setShowCookingMode] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [showMobileActionSheet, setShowMobileActionSheet] = useState(false);
  const [desiredServings, setDesiredServings] = useState<number | undefined>(undefined);
  const [showOriginalText, setShowOriginalText] = useState(false);

  // Check if we should show iOS-style action sheet
  const showIOSActionSheet = isNativeIOS();

  const { 
    data: recipe, 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['recipe', recipeId],
    queryFn: () => recipeId ? recipesApi.fetchRecipe(recipeId) : Promise.reject('No recipe ID'),
    enabled: !!recipeId, // Allow fetching for both authenticated and unauthenticated users
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => recipesApi.deleteRecipe(id),
    onSuccess: () => {
      // Invalidate and refetch recipes list
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      // Navigate to recipes page
      navigate('/recipes');
    },
    onError: (error: any) => {
      console.error('Error deleting recipe:', error);
      alert('Failed to delete recipe. Please try again.');
    }
  });

  const canEdit = Boolean(
    recipe && 
    user && 
    (user.role === 'admin' || 
     (recipe.user_id && user.id && !isNaN(parseInt(user.id)) && recipe.user_id === parseInt(user.id)))
  );
  const isOwnRecipe = Boolean(
    recipe && 
    user && 
    recipe.user_id && 
    user.id && 
    !isNaN(parseInt(user.id)) &&
    recipe.user_id === parseInt(user.id)
  );


  const handleSaveEdit = (updatedRecipe: Recipe) => {
    // Update the query cache with the new recipe data
    queryClient.setQueryData(['recipe', recipeId], updatedRecipe);
    setIsEditing(false);
  };

  const handleRecipeUpdate = (updatedRecipe: Recipe) => {
    // Update the query cache with the new recipe data but stay in editing mode
    queryClient.setQueryData(['recipe', recipeId], updatedRecipe);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleDeleteClick = () => {
    setShowDeleteConfirm(true);
  };

  const handleDeleteConfirm = () => {
    if (recipeId) {
      deleteMutation.mutate(recipeId);
    }
    setShowDeleteConfirm(false);
  };

  const handleDeleteCancel = () => {
    setShowDeleteConfirm(false);
  };

  const handleScaleChange = (newScaleFactor: number, newDesiredServings: number) => {
    setScaleFactor(newScaleFactor);
    setDesiredServings(newDesiredServings);
  };

  const formatTime = (minutes: number | undefined) => {
    if (!minutes) return 'Not specified';
    if (minutes < 60) return `${minutes} minutes`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours} hour${hours > 1 ? 's' : ''} ${mins} minutes` : `${hours} hour${hours > 1 ? 's' : ''}`;
  };

  const getDifficultyColor = (difficulty: string | undefined) => {
    switch (difficulty?.toLowerCase()) {
      case 'easy': return '#22c55e';
      case 'medium': return '#f59e0b';
      case 'hard': return '#ef4444';
      default: return '#9b644b';
    }
  };

  // Allow unauthenticated users to view public recipes

  if (!recipeId) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Invalid recipe
        </h2>
        <Button onClick={() => navigate('/recipes')}>
          Back to Recipes
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
          <p style={{color: '#9b644b'}}>Loading recipe...</p>
        </div>
      </div>
    );
  }

  if (error || !recipe) {
    // Check if this might be a private recipe and user is not authenticated
    const isLikelyPrivateRecipe = error && !isAuthenticated;
    
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          {isLikelyPrivateRecipe ? 'Please log in to view this recipe' : 'Recipe not found'}
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          {isLikelyPrivateRecipe 
            ? 'This recipe may be private. Please log in to access it.'
            : 'The recipe you\'re looking for doesn\'t exist or you don\'t have permission to view it.'
          }
        </p>
        <div className="flex justify-center gap-3">
          {isLikelyPrivateRecipe ? (
            <>
              <Button 
                onClick={() => navigate('/login')}
                className="bg-blue-700 text-white hover:bg-blue-800 border-blue-700"
              >
                Sign In
              </Button>
              <Button 
                variant="secondary" 
                onClick={() => navigate('/recipes')}
                className="bg-white text-blue-700 border-white hover:bg-blue-50"
              >
                Browse Public Recipes
              </Button>
            </>
          ) : (
            <Button onClick={() => navigate('/recipes')}>
              Back to Recipes
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back Navigation and Action Buttons */}
      <div className="mb-6 flex justify-between items-center">
        <button
          onClick={() => navigate('/recipes')}
          className="flex items-center space-x-2 text-text-secondary hover:text-accent transition-colors"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to Recipes</span>
        </button>

        {/* Desktop: simplified action buttons (hidden on mobile) */}
        <div className="hidden md:flex items-center space-x-2">
          {/* Quick toggle buttons - icon only */}
          {recipe && isAuthenticated && !isEditing && (
            <HaveMadeButton recipe={recipe} size="sm" iconOnly />
          )}
          {recipe && isAuthenticated && !isEditing && (
            <WantToMakeButton recipe={recipe} size="sm" iconOnly />
          )}

          {/* More actions dropdown */}
          {recipe && !isEditing && (
            <RecipeActionsDropdown
              recipe={recipe}
              isOwnRecipe={isOwnRecipe}
              canEdit={canEdit}
              onEditClick={() => setIsEditing(true)}
              onDeleteClick={handleDeleteClick}
              onRecipeUpdate={(updatedRecipe) => {
                queryClient.setQueryData(['recipe', recipeId], updatedRecipe);
              }}
            />
          )}
        </div>

        {/* Mobile: overflow menu (hidden on desktop) */}
        {!isEditing && (
          <div className="md:hidden relative">
            <button
              onClick={() => showIOSActionSheet ? setShowMobileActionSheet(true) : setShowMobileMenu(!showMobileMenu)}
              className="p-2 rounded-lg hover:bg-gray-100 active:bg-gray-200 transition-colors"
              aria-label="More actions"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>

            {/* Traditional dropdown menu for non-iOS */}
            {!showIOSActionSheet && showMobileMenu && (
              <>
                {/* Backdrop to close menu */}
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setShowMobileMenu(false)}
                />

                {/* Dropdown menu - unified styling */}
                <div className="absolute right-0 top-full mt-2 bg-white rounded-lg shadow-lg border z-50 min-w-[200px] py-1" style={{borderColor: '#e8d7cf'}}>
                  {recipe && isAuthenticated && !isOwnRecipe && recipe.is_public && (
                    <div className="mobile-menu-item" onClick={() => setShowMobileMenu(false)}>
                      <AddToCollectionButton recipe={recipe} />
                    </div>
                  )}
                  {recipe && isAuthenticated && (
                    <div className="mobile-menu-item" onClick={() => setShowMobileMenu(false)}>
                      <AddToGroupButton recipe={recipe} size="sm" />
                    </div>
                  )}
                  {recipe && isAuthenticated && (
                    <div className="mobile-menu-item" onClick={() => setShowMobileMenu(false)}>
                      <HaveMadeButton recipe={recipe} size="sm" />
                    </div>
                  )}
                  {recipe && isAuthenticated && (
                    <div className="mobile-menu-item" onClick={() => setShowMobileMenu(false)}>
                      <WantToMakeButton recipe={recipe} size="sm" />
                    </div>
                  )}
                  {recipe && isAuthenticated && !isOwnRecipe && recipe.is_public && (
                    <div className="mobile-menu-item" onClick={() => setShowMobileMenu(false)}>
                      <CopyRecipeButton recipe={recipe} size="sm" />
                    </div>
                  )}
                  {recipe && isOwnRecipe && (
                    <div className="mobile-menu-item" onClick={() => setShowMobileMenu(false)}>
                      <MakePublicButton recipe={recipe} size="sm" />
                    </div>
                  )}
                  {recipe && (
                    <div className="mobile-menu-item" onClick={() => setShowMobileMenu(false)}>
                      <FeatureToggleButton
                        recipe={recipe}
                        onUpdate={(updatedRecipe) => {
                          queryClient.setQueryData(['recipe', recipeId], updatedRecipe);
                        }}
                      />
                    </div>
                  )}
                  {canEdit && (
                    <button
                      onClick={() => { setIsEditing(true); setShowMobileMenu(false); }}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
                    >
                      <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                      Edit Recipe
                    </button>
                  )}
                  {recipe.has_full_access && (
                    <div className="mobile-menu-item" onClick={(e) => e.stopPropagation()}>
                      <ExportButton
                        type="recipe"
                        recipeId={recipeId}
                        buttonText="Download"
                        showOptions={true}
                      />
                    </div>
                  )}
                  {recipe && recipe.is_public && (
                    <div className="mobile-menu-item" onClick={() => setShowMobileMenu(false)}>
                      <ShareButton recipe={recipe} size="sm" />
                    </div>
                  )}
                  {canEdit && (
                    <button
                      onClick={() => { handleDeleteClick(); setShowMobileMenu(false); }}
                      className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center"
                    >
                      <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Delete Recipe
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Recipe Content */}
      {isEditing ? (
        <RecipeEditForm
          recipe={recipe}
          onSave={handleSaveEdit}
          onCancel={handleCancelEdit}
          onRecipeUpdate={handleRecipeUpdate}
        />
      ) : (
        <>
          {/* Recipe Header */}
          <div className="bg-white rounded-xl shadow-sm border p-8 mb-6" style={{borderColor: '#e8d7cf'}}>
            <div className="flex flex-col lg:flex-row lg:items-start lg:space-x-8">
              {/* Recipe Images */}
              <div className="w-full lg:w-1/3 mb-6 lg:mb-0">
                <RecipeImageCarousel
                  recipe={recipe}
                  canEdit={canEdit}
                />
              </div>

              {/* Recipe Info */}
              <div className="flex-1">
                {/* Translation Badge */}
                {recipe.is_translated && recipe.source_language_name && (
                  <div className="mb-3 flex items-center gap-2 flex-wrap">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                      <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                      </svg>
                      Translated from {recipe.source_language_name}
                    </span>
                    <button
                      onClick={() => setShowOriginalText(!showOriginalText)}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
                    >
                      {showOriginalText ? (
                        <>
                          <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                          Show English
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                          </svg>
                          Show Original
                        </>
                      )}
                    </button>
                  </div>
                )}

                <h1 className="text-3xl font-bold mb-2" style={{color: '#1c120d'}}>
                  {showOriginalText && recipe.original_title ? recipe.original_title : recipe.title}
                </h1>

                {/* Recipe Rating */}
                <div className="mb-4">
                  <StarRating recipeId={recipe.id} size="md" showCount />
                </div>

                {(recipe.description || (showOriginalText && recipe.original_description)) && (
                  <p className="text-lg text-text-secondary mb-6">
                    {showOriginalText && recipe.original_description ? recipe.original_description : recipe.description}
                  </p>
                )}

                {/* Recipe Metadata */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="text-center p-3 bg-background-secondary rounded-lg">
                    <div className="text-sm text-text-secondary mb-1">Prep Time</div>
                    <div className="font-medium text-text-primary">{formatTime(recipe.prep_time)}</div>
                  </div>

                  <div className="text-center p-3 bg-background-secondary rounded-lg">
                    <div className="text-sm text-text-secondary mb-1">Cook Time</div>
                    <div className="font-medium text-text-primary">{formatTime(recipe.cook_time)}</div>
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
                {recipe.user && (recipe.is_public || recipe.user_id !== parseInt(user?.id || '0')) && (
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
              </div>
            </div>
          </div>

          {/* Start Cooking Button */}
          {recipe.instructions && recipe.instructions.length > 0 && recipe.has_full_access !== false && !isEditing && (
            <div className="mb-6">
              <button
                onClick={() => setShowCookingMode(true)}
                className="w-full md:w-auto flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-white font-medium text-lg active:scale-[0.97] transition-transform"
                style={{ backgroundColor: '#f15f1c' }}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Start Cooking
              </button>
            </div>
          )}

          {/* Cooking Mode Overlay */}
          {showCookingMode && recipe && (
            <CookingMode
              recipe={recipe}
              scaleFactor={scaleFactor}
              onClose={() => setShowCookingMode(false)}
            />
          )}

          {/* Recipe Content */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Ingredients */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-xl shadow-sm border p-6 overflow-hidden" style={{borderColor: '#e8d7cf'}}>
                <h2 className="text-xl font-bold mb-4" style={{color: '#1c120d'}}>
                  Ingredients
                  {scaleFactor !== 1 && (
                    <span className="ml-2 text-sm font-normal text-blue-600">
                      (Scaled)
                    </span>
                  )}
                </h2>
                
                {/* Recipe Scaler Component */}
                {recipe.has_full_access !== false && !isEditing && (
                  <RecipeScaler
                    originalServings={recipe.servings}
                    onScaleChange={handleScaleChange}
                  />
                )}
                
                {recipe.has_full_access === false ? (
                  <PaywallMessage 
                    type="ingredients" 
                    cookbook={recipe.cookbook}
                    message={recipe.paywall_message}
                  />
                ) : recipe.ingredients && recipe.ingredients.length > 0 ? (
                  <ul className="space-y-3">
                    {recipe.ingredients
                      .sort((a, b) => a.order - b.order)
                      .map((ingredient) => {
                        const scaledQuantity = ingredient.quantity && isScalableQuantity(ingredient.quantity)
                          ? scaleQuantity(ingredient.quantity, scaleFactor)
                          : ingredient.quantity?.toString();
                        
                        return (
                          <li key={ingredient.id} className="flex items-start space-x-3">
                            <div className="w-2 h-2 bg-accent rounded-full mt-2 flex-shrink-0"></div>
                            <div className="flex-1">
                              <span className="text-text-primary">
                                {scaledQuantity && ingredient.unit ? (
                                  <span className="font-medium">
                                    {scaledQuantity} {ingredient.unit}{' '}
                                  </span>
                                ) : scaledQuantity ? (
                                  <span className="font-medium">{scaledQuantity} </span>
                                ) : null}
                                {ingredient.name}
                                {ingredient.preparation && (
                                  <span className="text-text-secondary">, {ingredient.preparation}</span>
                                )}
                                {Boolean(ingredient.optional) && (
                                  <span className="text-text-secondary italic"> (optional)</span>
                                )}
                            </span>
                          </div>
                        </li>
                        );
                      })}
                  </ul>
                ) : (
                  <p className="text-text-secondary">No ingredients listed</p>
                )}
              </div>
            </div>

            {/* Instructions */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
                <h2 className="text-xl font-bold mb-4" style={{color: '#1c120d'}}>
                  Instructions
                </h2>
                {recipe.has_full_access === false ? (
                  <PaywallMessage 
                    type="instructions" 
                    cookbook={recipe.cookbook}
                    message={recipe.paywall_message}
                  />
                ) : recipe.instructions && recipe.instructions.length > 0 ? (
                  <ol className="space-y-4">
                    {recipe.instructions
                      .sort((a, b) => a.step_number - b.step_number)
                      .map((instruction) => {
                        // Determine which text to display based on toggle
                        const displayText = showOriginalText && instruction.original_text
                          ? instruction.original_text
                          : instruction.text;

                        return (
                          <li key={instruction.id} className="flex space-x-4">
                            <div className="flex-shrink-0 w-8 h-8 bg-accent text-black rounded-full flex items-center justify-center font-medium">
                              {instruction.step_number}
                            </div>
                            <div className="flex-1 pt-1">
                              <p className="text-text-primary leading-relaxed mb-3">{displayText}</p>

                              {/* Step image if available */}
                              {(instruction.cloudinary_thumbnail_url || instruction.image_url) && (
                                <div className="mt-3">
                                  <img
                                    src={instruction.cloudinary_thumbnail_url || instruction.image_url || undefined}
                                    alt={`Step ${instruction.step_number} illustration`}
                                    className="max-w-sm h-48 object-cover rounded-lg border border-gray-200 cursor-pointer hover:opacity-90 transition-opacity"
                                    onClick={() => {
                                      // Open larger image in new tab/window
                                      const fullImageUrl = instruction.cloudinary_url || instruction.image_url;
                                      if (fullImageUrl) {
                                        window.open(fullImageUrl, '_blank');
                                      }
                                    }}
                                  />
                                </div>
                              )}

                              {/* User's step note */}
                              {instruction.user_note && (
                                <div className="mt-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
                                  <p className="text-sm text-amber-800 flex items-start gap-1.5">
                                    <svg className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                    </svg>
                                    {instruction.user_note}
                                  </p>
                                </div>
                              )}
                            </div>
                          </li>
                        );
                      })}
                  </ol>
                ) : (
                  <p className="text-text-secondary">No instructions provided</p>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Login prompt for unauthenticated users */}
      {!isAuthenticated && (
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-xl p-6 text-center">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            Want to do more with recipes?
          </h3>
          <p className="text-blue-700 mb-4">
            Sign in to add recipes to your collection, leave comments, create your own recipes, and more!
          </p>
          <div className="flex justify-center gap-3">
            <Button 
              onClick={() => navigate('/register')}
              className="bg-blue-700 text-white hover:bg-blue-800 border-blue-700"
            >
              Create Free Account
            </Button>
            <Button 
              variant="secondary" 
              onClick={() => navigate('/login')}
              className="bg-white text-blue-700 border-white hover:bg-blue-50"
            >
              Sign In
            </Button>
          </div>
        </div>
      )}

      {/* Notes Section - Only show for authenticated users when not editing */}
      {isAuthenticated && !isEditing && (
        <div className="mt-6">
          <NotesSection recipe={recipe} />
        </div>
      )}

      {/* Comments Section - Show for all users when not editing, but functionality limited by authentication */}
      {!isEditing && (
        <div className="mt-6">
          <CommentsSection recipe={recipe} />
        </div>
      )}

      {/* Recipe Source */}
      {recipe.source && (
        <div className="mt-6 bg-white rounded-xl shadow-sm border p-4" style={{borderColor: '#e8d7cf'}}>
          <p className="text-sm text-text-secondary">
            <span className="font-medium">Source:</span> {recipe.source}
          </p>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Delete Recipe</h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete "{recipe?.title}"? This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <Button
                onClick={handleDeleteCancel}
                variant="secondary"
                size="sm"
              >
                Cancel
              </Button>
              <Button
                onClick={handleDeleteConfirm}
                variant="primary"
                size="sm"
                className="bg-red-600 hover:bg-red-700 text-white"
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* iOS Action Sheet for mobile menu */}
      <ActionSheet
        isOpen={showMobileActionSheet}
        onClose={() => setShowMobileActionSheet(false)}
        title="Recipe Actions"
        options={(() => {
          const options: ActionSheetOption[] = [];

          if (recipe && isAuthenticated && !isOwnRecipe && recipe.is_public) {
            options.push({
              label: 'Add to Cookbook',
              onClick: () => {
                // Trigger the AddToCollectionButton action programmatically
                // For now, just close - the component handles its own modal
              },
            });
          }

          if (recipe && isAuthenticated) {
            options.push({
              label: recipe.have_made ? 'Unmark as Made' : 'Mark as Made',
              onClick: () => {
                // Toggle have made status
              },
            });
            options.push({
              label: recipe.want_to_make ? 'Remove from Want to Make' : 'Add to Want to Make',
              onClick: () => {
                // Toggle want to make status
              },
            });
          }

          if (recipe && isOwnRecipe) {
            options.push({
              label: recipe.is_public ? 'Make Private' : 'Make Public',
              onClick: () => {
                // Toggle visibility
              },
            });
          }

          if (canEdit) {
            options.push({
              label: 'Edit Recipe',
              onClick: () => setIsEditing(true),
            });
          }

          if (recipe && recipe.is_public) {
            options.push({
              label: 'Share Recipe',
              onClick: () => {
                // Share via native share
              },
            });
          }

          if (canEdit) {
            options.push({
              label: 'Delete Recipe',
              onClick: handleDeleteClick,
              destructive: true,
            });
          }

          return options;
        })()}
      />
    </div>
  );
};

export { RecipeDetailPage };