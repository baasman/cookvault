import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { recipeGroupsApi } from '../../services/recipeGroupsApi';
import type { Recipe } from '../../types';

interface WantToMakeButtonProps {
  recipe: Recipe;
  size?: 'sm' | 'md' | 'lg';
  iconOnly?: boolean;
  onSuccess?: () => void;
}

const WantToMakeButton: React.FC<WantToMakeButtonProps> = ({
  recipe,
  size = 'sm',
  iconOnly = false,
  onSuccess
}) => {
  const queryClient = useQueryClient();

  const toggleMutation = useMutation({
    mutationFn: () => recipeGroupsApi.toggleSystemGroup('want_to_make', recipe.id),
    onSuccess: (data) => {
      // Invalidate relevant queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      queryClient.invalidateQueries({ queryKey: ['recipe-groups'] });

      // Show success toast
      toast.success(data.message);

      onSuccess?.();
    },
    onError: (error: Error) => {
      console.error('Error toggling want to make status:', error);
      toast.error(error.message || 'Failed to update status');
    },
  });

  const wantToMake = recipe.want_to_make || false;
  const isProcessing = toggleMutation.isPending;

  const handleClick = (e: React.MouseEvent) => {
    // Prevent event bubbling to parent Link component
    e.preventDefault();
    e.stopPropagation();

    if (isProcessing) return;

    toggleMutation.mutate();
  };

  const getSizeClasses = () => {
    if (iconOnly) {
      switch (size) {
        case 'sm':
          return 'p-1.5';
        case 'lg':
          return 'p-3';
        case 'md':
        default:
          return 'p-2';
      }
    }
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
    if (wantToMake) {
      return 'bg-amber-100 text-amber-800 border border-amber-200 hover:bg-amber-200';
    }
    return 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200';
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

    // Heart icon
    return (
      <svg
        className={`h-4 w-4 ${wantToMake ? 'text-amber-600' : 'text-gray-500'}`}
        fill={wantToMake ? 'currentColor' : 'none'}
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
        />
      </svg>
    );
  };

  const getButtonText = () => {
    if (isProcessing) {
      return 'Updating...';
    }
    return wantToMake ? 'Want to Make' : 'Want to Make';
  };

  return (
    <button
      onClick={handleClick}
      disabled={isProcessing}
      title={wantToMake ? 'Remove from Want to Make' : 'Add to Want to Make'}
      className={`
        inline-flex items-center justify-center font-medium rounded-md
        transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
        ${iconOnly ? '' : 'space-x-1'}
        ${getSizeClasses()} ${getVariantClasses()}
      `}
    >
      {getIcon()}
      {!iconOnly && <span>{getButtonText()}</span>}
    </button>
  );
};

export { WantToMakeButton };
