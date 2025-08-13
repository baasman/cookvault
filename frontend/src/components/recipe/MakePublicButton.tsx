import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { recipesApi } from '../../services/recipesApi';
import { CopyrightConsentModal } from '../ui/CopyrightConsentModal';
import type { Recipe } from '../../types';

interface MakePublicButtonProps {
  recipe: Recipe;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary';
  onSuccess?: () => void;
}

const MakePublicButton: React.FC<MakePublicButtonProps> = ({
  recipe,
  size = 'md',
  variant = 'secondary',
  onSuccess
}) => {
  const queryClient = useQueryClient();
  const [showCopyrightModal, setShowCopyrightModal] = useState(false);

  const togglePrivacyMutation = useMutation({
    mutationFn: (params: { isPublic: boolean; consents?: Record<string, boolean> }) => 
      recipesApi.toggleRecipePrivacy(recipe.id, params.isPublic, params.consents),
    onSuccess: (updatedRecipe: Recipe) => {
      // Invalidate relevant queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['discover-recipes'] });
      
      // Show success toast
      const message = updatedRecipe.is_public ? 'Recipe made public!' : 'Recipe made private!';
      toast.success(message);
      
      onSuccess?.();
    },
    onError: (error) => {
      console.error('Error updating recipe privacy:', error);
      toast.error(error.message || 'Failed to update recipe privacy');
    },
  });

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (togglePrivacyMutation.isPending) return;

    // MakePublicButton clicked - debug info removed for production

    // If making public, show copyright modal first
    if (!recipe.is_public) {
      setShowCopyrightModal(true);
    } else {
      // Making private - no consent needed
      togglePrivacyMutation.mutate({ isPublic: false });
    }
  };

  const handleCopyrightConsent = (consents: Record<string, boolean>) => {
    setShowCopyrightModal(false);
    togglePrivacyMutation.mutate({ isPublic: true, consents });
  };

  const handleCopyrightCancel = () => {
    setShowCopyrightModal(false);
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
    if (recipe.is_public) {
      return 'bg-green-100 text-green-800 border border-green-200 hover:bg-green-200';
    }
    
    switch (variant) {
      case 'primary':
        return 'bg-blue-600 text-white hover:bg-blue-700';
      case 'secondary':
      default:
        return 'bg-gray-100 text-gray-900 border border-gray-300 hover:bg-gray-200';
    }
  };

  const getIcon = () => {
    if (togglePrivacyMutation.isPending) {
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

    if (recipe.is_public) {
      return (
        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd"/>
        </svg>
      );
    }

    return (
      <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
        <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd"/>
      </svg>
    );
  };

  const getButtonText = () => {
    if (togglePrivacyMutation.isPending) {
      return recipe.is_public ? 'Making Private...' : 'Making Public...';
    }
    return recipe.is_public ? 'Make Private' : 'Make Public';
  };

  return (
    <>
      <button
        onClick={handleClick}
        disabled={togglePrivacyMutation.isPending}
        className={`
          inline-flex items-center justify-center space-x-1 font-medium rounded-md
          transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
          ${getSizeClasses()} ${getVariantClasses()}
        `}
      >
        {getIcon()}
        <span>{getButtonText()}</span>
      </button>

      {/* Copyright Consent Modal */}
      <CopyrightConsentModal
        isOpen={showCopyrightModal}
        onClose={handleCopyrightCancel}
        onConfirm={handleCopyrightConsent}
        recipeName={recipe.title}
        isLoading={togglePrivacyMutation.isPending}
      />
    </>
  );
};

export { MakePublicButton };