import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { recipesApi } from '../../services/recipesApi';
import type { Recipe } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../ui';

interface FeatureToggleButtonProps {
  recipe: Recipe;
  size?: 'sm' | 'md' | 'lg';
  onUpdate?: (updatedRecipe: Recipe) => void;
}

export const FeatureToggleButton: React.FC<FeatureToggleButtonProps> = ({
  recipe,
  size = 'sm',
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
      toast.error('Failed to feature recipe. ' + (error instanceof Error ? error.message : 'Please try again.'));
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
      toast.error('Failed to unfeature recipe. ' + (error instanceof Error ? error.message : 'Please try again.'));
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
    <Button
      onClick={handleToggleFeature}
      disabled={isProcessing}
      variant="secondary"
      size={size}
      style={recipe.is_featured ? { backgroundColor: '#fef9c3', color: '#a16207' } : undefined}
      title={recipe.is_featured ? 'Remove from featured recipes' : 'Add to featured recipes (max 3)'}
    >
      {isProcessing ? (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
      ) : (
        <span className="text-lg mr-2">
          {recipe.is_featured ? '⭐' : '☆'}
        </span>
      )}
      <span>
        {recipe.is_featured ? 'Featured' : 'Feature Recipe'}
      </span>
    </Button>
  );
};