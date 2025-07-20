import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { recipesApi } from '../services/recipesApi';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui';
import { RecipeImageDisplay } from '../components/recipe/RecipeImageDisplay';
import { RecipeEditForm } from '../components/recipe/RecipeEditForm';
import { AddToCollectionButton } from '../components/recipe/AddToCollectionButton';
import { CopyRecipeButton } from '../components/recipe/CopyRecipeButton';
import { AddToGroupButton } from '../components/recipe/AddToGroupButton';
import { NotesSection } from '../components/recipe/NotesSection';
import { CommentsSection } from '../components/recipe/CommentsSection';
import type { Recipe } from '../types';

const RecipeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const queryClient = useQueryClient();
  const recipeId = id ? parseInt(id, 10) : null;
  const [isEditing, setIsEditing] = useState(false);

  const { 
    data: recipe, 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['recipe', recipeId],
    queryFn: () => recipeId ? recipesApi.fetchRecipe(recipeId) : Promise.reject('No recipe ID'),
    enabled: isAuthenticated && !!recipeId,
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

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Please log in to view this recipe
        </h2>
        <Button onClick={() => navigate('/login')}>
          Sign In
        </Button>
      </div>
    );
  }

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
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Recipe not found
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          The recipe you're looking for doesn't exist or you don't have permission to view it.
        </p>
        <Button onClick={() => navigate('/recipes')}>
          Back to Recipes
        </Button>
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
          {/* Add to Collection Button - show for public recipes not owned by current user */}
          {recipe && !isOwnRecipe && recipe.is_public && !isEditing && (
            <AddToCollectionButton recipe={recipe} />
          )}
          
          {/* Add to Group Button - show for authenticated users viewing any recipe */}
          {recipe && isAuthenticated && !isEditing && (
            <AddToGroupButton recipe={recipe} size="sm" />
          )}
          
          {/* Copy Recipe Button - show for public recipes not owned by current user */}
          {recipe && !isOwnRecipe && recipe.is_public && !isEditing && (
            <CopyRecipeButton recipe={recipe} size="sm" />
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
              {/* Recipe Image */}
              <div className="w-full lg:w-1/3 mb-6 lg:mb-0">
                <RecipeImageDisplay 
                  recipe={recipe} 
                  canEdit={canEdit}
                  isEditMode={false}
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
                    <div className="font-medium text-text-primary">{recipe.servings || 'Not specified'}</div>
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
              <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
                <h2 className="text-xl font-bold mb-4" style={{color: '#1c120d'}}>
                  Ingredients
                </h2>
                {recipe.ingredients && recipe.ingredients.length > 0 ? (
                  <ul className="space-y-3">
                    {recipe.ingredients
                      .sort((a, b) => a.order - b.order)
                      .map((ingredient) => (
                        <li key={ingredient.id} className="flex items-start space-x-3">
                          <div className="w-2 h-2 bg-accent rounded-full mt-2 flex-shrink-0"></div>
                          <div className="flex-1">
                            <span className="text-text-primary">
                              {ingredient.quantity && ingredient.unit ? (
                                <span className="font-medium">
                                  {ingredient.quantity} {ingredient.unit}{' '}
                                </span>
                              ) : ingredient.quantity ? (
                                <span className="font-medium">{ingredient.quantity} </span>
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
                      ))}
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
                {recipe.instructions && recipe.instructions.length > 0 ? (
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

      {/* Notes Section - Only show when not editing */}
      {!isEditing && (
        <NotesSection recipe={recipe} />
      )}

      {/* Comments Section - Only show when not editing */}
      {!isEditing && (
        <CommentsSection recipe={recipe} />
      )}

      {/* Recipe Source */}
      {recipe.source && (
        <div className="mt-6 bg-white rounded-xl shadow-sm border p-4" style={{borderColor: '#e8d7cf'}}>
          <p className="text-sm text-text-secondary">
            <span className="font-medium">Source:</span> {recipe.source}
          </p>
        </div>
      )}
    </div>
  );
};

export { RecipeDetailPage };