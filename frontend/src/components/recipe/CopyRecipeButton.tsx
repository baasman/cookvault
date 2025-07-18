import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { recipesApi } from '../../services/recipesApi';
import type { Recipe } from '../../types';
import toast from 'react-hot-toast';

interface CopyRecipeButtonProps {
  recipe: Recipe;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary';
  onSuccess?: () => void;
}

const CopyRecipeButton: React.FC<CopyRecipeButtonProps> = ({
  recipe,
  size = 'md',
  variant = 'secondary',
  onSuccess
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const copyRecipeMutation = useMutation({
    mutationFn: () => recipesApi.copyRecipe(recipe.id),
    onSuccess: (data) => {
      // Invalidate relevant queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      
      toast.success('Recipe copied successfully!');
      
      // Navigate to the copied recipe
      if (data.recipe && data.recipe.id) {
        navigate(`/recipes/${data.recipe.id}`);
      }
      
      onSuccess?.();
    },
    onError: (error: Error) => {
      console.error('Error copying recipe:', error);
      toast.error(error.message || 'Failed to copy recipe');
    },
  });

  const isProcessing = copyRecipeMutation.isPending;

  const handleClick = () => {
    if (isProcessing) return;
    copyRecipeMutation.mutate();
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
    switch (variant) {
      case 'primary':
        return 'bg-blue-600 text-white hover:bg-blue-700';
      case 'secondary':
      default:
        return 'bg-gray-100 text-gray-900 border border-gray-300 hover:bg-gray-200';
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

    return (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    );
  };

  const getButtonText = () => {
    if (isProcessing) {
      return 'Copying...';
    }
    return 'Copy Recipe';
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

export { CopyRecipeButton };