import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { recipesApi } from '../../services/recipesApi';
import type { Recipe } from '../../types';

interface AddToCollectionButtonProps {
  recipe: Recipe;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary';
  onSuccess?: () => void;
}

const AddToCollectionButton: React.FC<AddToCollectionButtonProps> = ({
  recipe,
  size = 'md',
  variant = 'primary',
  onSuccess
}) => {
  const queryClient = useQueryClient();

  const addToCollectionMutation = useMutation({
    mutationFn: () => recipesApi.addToCollection(recipe.id),
    onSuccess: (data) => {
      // Invalidate relevant queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['discover-recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      
      // Show success toast
      toast.success(data.message || 'Recipe added to collection!');
      console.log('Recipe added to collection:', recipe.title);
      
      onSuccess?.();
    },
    onError: (error) => {
      console.error('Error adding recipe to collection:', error);
      toast.error(error.message || 'Failed to add recipe to collection');
    },
  });

  const removeFromCollectionMutation = useMutation({
    mutationFn: () => recipesApi.removeFromCollection(recipe.id),
    onSuccess: (data) => {
      // Invalidate relevant queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['discover-recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      
      // Show success toast
      toast.success(data.message || 'Recipe removed from collection');
      console.log('Recipe removed from collection:', recipe.title);
      
      onSuccess?.();
    },
    onError: (error) => {
      console.error('Error removing recipe from collection:', error);
      toast.error(error.message || 'Failed to remove recipe from collection');
    },
  });

  const isInCollection = recipe.is_in_collection || false;
  const isProcessing = addToCollectionMutation.isPending || removeFromCollectionMutation.isPending;

  const handleClick = (e: React.MouseEvent) => {
    // Prevent event bubbling to parent Link component
    e.preventDefault();
    e.stopPropagation();
    
    if (isProcessing) return;

    console.log('AddToCollectionButton clicked:', {
      recipeId: recipe.id,
      recipeTitle: recipe.title,
      isInCollection,
      isProcessing
    });

    if (isInCollection) {
      removeFromCollectionMutation.mutate();
    } else {
      addToCollectionMutation.mutate();
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'px-2 py-1 text-xs';
      case 'lg':
        return 'px-6 py-3 text-base';
      case 'md':
      default:
        return 'px-4 py-2 text-sm';
    }
  };

  const getVariantClasses = () => {
    if (isInCollection) {
      return 'bg-green-100 text-green-800 border border-green-200 hover:bg-green-200';
    }
    
    switch (variant) {
      case 'secondary':
        return 'bg-gray-100 text-gray-900 border border-gray-300 hover:bg-gray-200';
      case 'primary':
      default:
        return 'bg-blue-600 text-white hover:bg-blue-700';
    }
  };

  const getIcon = () => {
    if (isProcessing) {
      return (
        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      );
    }

    if (isInCollection) {
      return (
        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      );
    }

    return (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
      </svg>
    );
  };

  const getButtonText = () => {
    if (isProcessing) {
      return isInCollection ? 'Removing...' : 'Adding...';
    }
    return isInCollection ? 'In Collection' : 'Add to Collection';
  };

  return (
    <button
      onClick={handleClick}
      disabled={isProcessing}
      className={`
        inline-flex items-center justify-center space-x-1 font-medium rounded-md
        transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
        ${getSizeClasses()} ${getVariantClasses()}
      `}
    >
      {getIcon()}
      <span>{getButtonText()}</span>
    </button>
  );
};

export { AddToCollectionButton };