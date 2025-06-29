import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { recipesApi } from '../services/recipesApi';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui';

const RecipeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const recipeId = id ? parseInt(id, 10) : null;

  const { 
    data: recipe, 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['recipe', recipeId],
    queryFn: () => recipeId ? recipesApi.fetchRecipe(recipeId) : Promise.reject('No recipe ID'),
    enabled: isAuthenticated && !!recipeId,
  });

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
      {/* Back Navigation */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/recipes')}
          className="flex items-center space-x-2 text-text-secondary hover:text-accent transition-colors"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to Recipes</span>
        </button>
      </div>

      {/* Recipe Header */}
      <div className="bg-white rounded-xl shadow-sm border p-8 mb-6" style={{borderColor: '#e8d7cf'}}>
        <div className="flex flex-col lg:flex-row lg:items-start lg:space-x-8">
          {/* Recipe Image */}
          <div className="w-full lg:w-1/3 mb-6 lg:mb-0">
            <div className="aspect-square bg-gradient-to-br from-background-secondary to-primary-200 rounded-xl flex items-center justify-center">
              <svg className="h-16 w-16 text-primary-300" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
            </div>
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
                <p className="font-medium text-text-primary">{recipe.cookbook.title}</p>
                {recipe.cookbook.author && (
                  <p className="text-sm text-text-secondary">by {recipe.cookbook.author}</p>
                )}
                {recipe.page_number && (
                  <p className="text-sm text-text-secondary">Page {recipe.page_number}</p>
                )}
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
                          {ingredient.optional && (
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
                      <div className="flex-shrink-0 w-8 h-8 bg-accent text-white rounded-full flex items-center justify-center font-medium">
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