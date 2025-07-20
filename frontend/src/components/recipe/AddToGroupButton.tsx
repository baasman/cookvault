import React, { useState } from 'react';
import { AddToGroupModal } from './AddToGroupModal';
import { Button } from '../ui';
import type { Recipe } from '../../types';

interface AddToGroupButtonProps {
  recipe: Recipe;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary';
  onSuccess?: () => void;
  className?: string;
}

const AddToGroupButton: React.FC<AddToGroupButtonProps> = ({
  recipe,
  size = 'md',
  variant = 'secondary',
  onSuccess,
  className = ''
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleSuccess = () => {
    setIsModalOpen(false);
    onSuccess?.();
  };

  return (
    <>
      <Button
        onClick={() => setIsModalOpen(true)}
        variant={variant}
        size={size}
        className={className}
      >
        <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        Add to Group
      </Button>

      <AddToGroupModal
        recipe={recipe}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleSuccess}
      />
    </>
  );
};

export { AddToGroupButton };