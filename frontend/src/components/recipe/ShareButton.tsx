import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { shareRecipe } from '../../services/shareService';
import { Button } from '../ui';
import type { Recipe } from '../../types';

interface ShareButtonProps {
  recipe: Recipe;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary';
}

const ShareButton: React.FC<ShareButtonProps> = ({
  recipe,
  size = 'sm',
  variant = 'secondary'
}) => {
  const [isSharing, setIsSharing] = useState(false);

  const handleShare = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (isSharing) return;

    setIsSharing(true);
    try {
      const result = await shareRecipe(recipe);

      if (result?.activityType === 'clipboard') {
        toast.success('Link copied to clipboard!');
      } else if (result) {
        toast.success('Recipe shared!');
      }
    } catch (error) {
      console.error('Share failed:', error);
      toast.error('Failed to share recipe');
    } finally {
      setIsSharing(false);
    }
  };

  return (
    <Button
      onClick={handleShare}
      disabled={isSharing}
      variant={variant}
      size={size}
    >
      {isSharing ? (
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
      ) : (
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
          />
        </svg>
      )}
      <span>Share</span>
    </Button>
  );
};

export { ShareButton };
