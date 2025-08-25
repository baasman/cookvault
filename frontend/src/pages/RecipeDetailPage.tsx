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
import { NotesSection } from '../components/recipe/NotesSection';
import { CommentsSection } from '../components/recipe/CommentsSection';
import { PaywallMessage } from '../components/recipe/PaywallMessage';
import { RecipeScaler } from '../components/recipe/RecipeScaler';
import { scaleQuantity, isScalableQuantity } from '../utils/recipeScaling';
import type { Recipe } from '../types';

const RecipeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const queryClient = useQueryClient();
  const recipeId = id ? parseInt(id, 10) : null;
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [scaleFactor, setScaleFactor] = useState(1);
  const [desiredServings, setDesiredServings] = useState<number | undefined>(undefined);

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

  // Debug logging for button visibility issues
  if (recipe && user) {
    console.log('RecipeDetailPage Debug:', {
      recipeId: recipe.id,
      recipeTitle: recipe.title,
      recipeUserId: recipe.user_id,
      recipeUserIdType: typeof recipe.user_id,
      currentUserId: user.id,
      currentUserIdType: typeof user.id,
      parsedUserId: parseInt(user.id),
      canEdit,
      isOwnRecipe,
      userRole: user.role,
      isAdmin: user.role === 'admin',
      isInCollection: recipe.is_in_collection,
      hasIsInCollection: 'is_in_collection' in recipe,
      isPublic: recipe.is_public,
      isEditing
    });
  }

  const handleSaveEdit = (updatedRecipe: Recipe) => {
    // Update the query cache with the new recipe data
    queryClient.setQueryData(['recipe', recipeId], updatedRecipe);
    setIsEditing(false);
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
      {/* Back Navigation and Edit Button */}
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
        
        <div className="flex items-center space-x-3">
          {/* Add to Collection Button - show for authenticated users viewing public recipes not owned by them */}
          {recipe && isAuthenticated && !isOwnRecipe && recipe.is_public && !isEditing && (
            <AddToCollectionButton recipe={recipe} />
          )}
          
          {/* Add to Group Button - show for authenticated users viewing any recipe */}
          {recipe && isAuthenticated && !isEditing && (
            <AddToGroupButton recipe={recipe} size="sm" />
          )}
          
          {/* Copy Recipe Button - show for authenticated users viewing public recipes not owned by them */}
          {recipe && isAuthenticated && !isOwnRecipe && recipe.is_public && !isEditing && (
            <CopyRecipeButton recipe={recipe} size="sm" />
          )}
          
          {/* Make Public Button - show for recipes owned by current user */}
          {recipe && isOwnRecipe && !isEditing && (
            <MakePublicButton recipe={recipe} size="sm" />
          )}

          {/* Feature Toggle Button - show for admins only */}
          {recipe && !isEditing && (
            <FeatureToggleButton 
              recipe={recipe} 
              onUpdate={(updatedRecipe) => {
                queryClient.setQueryData(['recipe', recipeId], updatedRecipe);
              }} 
            />
          )}
          
          {/* Edit Button */}
          {canEdit && !isEditing && (
            <Button onClick={() => setIsEditing(true)} variant="secondary" size="sm">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit Recipe
            </Button>
          )}
          
          {/* Delete Button */}
          {canEdit && !isEditing && (
            <Button 
              onClick={handleDeleteClick} 
              variant="secondary" 
              size="sm"
              className="ml-2 bg-red-50 text-red-600 border-red-200 hover:bg-red-100"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete Recipe
            </Button>
          )}
        </div>
      </div>

      {/* Recipe Content */}
      {isEditing ? (
        <RecipeEditForm
          recipe={recipe}
          onSave={handleSaveEdit}
          onCancel={handleCancelEdit}
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
                />
              </div>

              {/* Recipe Info */}
              <div className="flex-1">
                <h1 className="text-3xl font-bold mb-4" style={{color: '#1c120d'}}>
                  {recipe.title}
                </h1>

                {recipe.description && (
                  <p className="text-lg text-text-secondary mb-6">
                    {recipe.description}
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

                {/* User Information - Show for public recipes or recipes from other users */}
                {recipe.user && (recipe.is_public || recipe.user_id !== parseInt(user?.id || '0')) && (
                  <div className="mb-6 p-4 bg-background-secondary rounded-lg border border-primary-200">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-accent rounded-full flex items-center justify-center">
                        <svg className="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
                        </svg>
                      </div>
                      <div>
                        <div className="text-sm text-text-secondary">Uploaded by</div>
                        <div className="font-medium text-text-primary">
                          {recipe.user.first_name && recipe.user.last_name 
                            ? `${recipe.user.first_name} ${recipe.user.last_name}`
                            : recipe.user.username
                          }
                        </div>
                        {recipe.created_at && (
                          <div className="text-xs text-text-secondary">
                            {new Date(recipe.created_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric'
                            })}
                          </div>
                        )}
                      </div>
                    </div>
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

                {/* Cookbook Info */}
                {recipe.cookbook && (
                  <div className="p-4 bg-background-secondary rounded-lg">
                    <h3 className="text-sm font-medium text-text-secondary mb-1">From Cookbook</h3>
                    <Link 
                      to={`/cookbooks/${recipe.cookbook.id}`}
                      className="font-medium text-text-primary hover:text-accent transition-colors underline hover:no-underline"
                    >
                      {recipe.cookbook.title}
                    </Link>
                    {recipe.cookbook.author && (
                      <p className="text-sm text-text-secondary">by {recipe.cookbook.author}</p>
                    )}
                    {recipe.page_number && (
                      <p className="text-sm text-text-secondary">Page {recipe.page_number}</p>
                    )}
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
                      .map((instruction) => (
                        <li key={instruction.id} className="flex space-x-4">
                          <div className="flex-shrink-0 w-8 h-8 bg-accent text-black rounded-full flex items-center justify-center font-medium">
                            {instruction.step_number}
                          </div>
                          <div className="flex-1 pt-1">
                            <p className="text-text-primary leading-relaxed">{instruction.text}</p>
                          </div>
                        </li>
                      ))}
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
    </div>
  );
};

export { RecipeDetailPage };