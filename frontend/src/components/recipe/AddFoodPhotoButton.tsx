import React, { useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { recipesUploadApi } from '../../services/recipesUploadApi';
import { captureRecipePhoto } from '../../services/cameraService';
import { isNativePlatform } from '../../utils/platform';
import type { Recipe } from '../../types';

interface AddFoodPhotoButtonProps {
  recipe: Recipe;
  onSuccess?: () => void;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'];

const AddFoodPhotoButton: React.FC<AddFoodPhotoButtonProps> = ({
  recipe,
  onSuccess
}) => {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isCapturing, setIsCapturing] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: (imageFile: File) => recipesUploadApi.uploadPrimaryRecipeImage(recipe.id, imageFile),
    onSuccess: () => {
      // Invalidate recipe queries to refresh with new image
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      queryClient.invalidateQueries({ queryKey: ['recipes'] });

      toast.success('Food photo added successfully!');
      onSuccess?.();
    },
    onError: (error: Error) => {
      console.error('Error uploading food photo:', error);
      toast.error(error.message || 'Failed to upload photo');
    },
  });

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'Please select a valid image file (JPEG, PNG, WebP, or HEIC)';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File is too large. Maximum size is 5MB';
    }
    return null;
  };

  const handleFileSelect = (file: File) => {
    const error = validateFile(file);
    if (error) {
      toast.error(error);
      return;
    }
    uploadMutation.mutate(file);
  };

  const handleClick = async () => {
    if (uploadMutation.isPending || isCapturing) return;

    if (isNativePlatform()) {
      // On native platforms, use camera/gallery picker
      try {
        setIsCapturing(true);
        const result = await captureRecipePhoto();
        if (result?.file) {
          handleFileSelect(result.file);
        }
      } catch (error) {
        console.error('Camera capture failed:', error);
        // If camera fails, fall back to file picker
        fileInputRef.current?.click();
      } finally {
        setIsCapturing(false);
      }
    } else {
      // On web, use file input
      fileInputRef.current?.click();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
    // Reset input so the same file can be selected again
    e.target.value = '';
  };

  const isProcessing = uploadMutation.isPending || isCapturing;

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
        onChange={handleInputChange}
        className="hidden"
        aria-hidden="true"
      />
      <button
        onClick={handleClick}
        disabled={isProcessing}
        className="mt-3 w-full flex items-center justify-center space-x-2 px-4 py-2 text-white text-sm font-medium rounded-lg transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
        style={{ backgroundColor: '#f15f1c' }}
        aria-label="Add food photo"
      >
        {isProcessing ? (
          <>
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
            <span>Uploading...</span>
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span>Add Food Photo</span>
          </>
        )}
      </button>
    </>
  );
};

export { AddFoodPhotoButton };
