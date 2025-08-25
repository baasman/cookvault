import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { recipesApi } from '../../services/recipesApi';
import type { Recipe } from '../../types';
import { useAuth } from '../../contexts/AuthContext';

interface FeatureToggleButtonProps {
  recipe: Recipe;
  onUpdate?: (updatedRecipe: Recipe) => void;
}

export const FeatureToggleButton: React.FC<FeatureToggleButtonProps> = ({
  recipe,
  onUpdate
}) => {
  const { isAdmin } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const queryClient = useQueryClient();

  const featureMutation = useMutation({
    mutationFn: () => recipesApi.featureRecipe(recipe.id),
    onSuccess: (updatedRecipe) => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      queryClient.invalidateQueries({ queryKey: ['featured-recipes'] });
      onUpdate?.(updatedRecipe);
    },
    onError: (error) => {
      console.error('Error featuring recipe:', error);
      alert('Failed to feature recipe. ' + (error instanceof Error ? error.message : 'Please try again.'));
    }
  });

  const unfeatureMutation = useMutation({
    mutationFn: () => recipesApi.unfeatureRecipe(recipe.id),
    onSuccess: (updatedRecipe) => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      queryClient.invalidateQueries({ queryKey: ['featured-recipes'] });
      onUpdate?.(updatedRecipe);
    },
    onError: (error) => {
      console.error('Error unfeaturing recipe:', error);
      alert('Failed to unfeature recipe. ' + (error instanceof Error ? error.message : 'Please try again.'));
    }
  });

  const handleToggleFeature = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    try {
      if (recipe.is_featured) {
        await unfeatureMutation.mutateAsync();
      } else {
        await featureMutation.mutateAsync();
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Only show for admins
  if (!isAdmin) {
    return null;
  }

  const isProcessing = isLoading || featureMutation.isPending || unfeatureMutation.isPending;

  return (
    <button
      onClick={handleToggleFeature}
      disabled={isProcessing}
      className={`
        inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors
        ${recipe.is_featured
          ? 'bg-yellow-50 border-yellow-300 text-yellow-700 hover:bg-yellow-100'
          : 'bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100'
        }
        ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
      title={recipe.is_featured ? 'Remove from featured recipes' : 'Add to featured recipes (max 3)'}
    >
      {isProcessing ? (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        <span className="text-lg">
          {recipe.is_featured ? '⭐' : '☆'}
        </span>
      )}
      
      <span>
        {recipe.is_featured ? 'Featured' : 'Feature Recipe'}
      </span>
    </button>
  );
};