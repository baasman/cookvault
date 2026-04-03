import React, { useState, useRef } from 'react';
import type { Instruction } from '../../types';
import { recipesUploadApi } from '../../services/recipesUploadApi';
import { FILE_LIMITS } from '../../utils/constants';
import toast from 'react-hot-toast';

interface InstructionImageUploadProps {
  recipeId: number;
  instruction: Instruction;
  onImageUpdate: (updatedInstruction: Instruction) => void;
  className?: string;
}

export const InstructionImageUpload: React.FC<InstructionImageUploadProps> = ({
  recipeId,
  instruction,
  onImageUpdate,
  className = '',
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (file: File) => {
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > FILE_LIMITS.IMAGE_MAX_SIZE) {
      toast.error('Image must be smaller than 10MB');
      return;
    }

    setIsUploading(true);

    try {
      const updatedInstruction = await recipesUploadApi.uploadInstructionImage(
        recipeId,
        instruction.id,
        file
      );
      onImageUpdate(updatedInstruction);
      toast.success('Step image uploaded successfully!');
    } catch (error) {
      console.error('Error uploading instruction image:', error);
      toast.error('Failed to upload image. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveImage = async () => {
    setIsUploading(true);

    try {
      const updatedInstruction = await recipesUploadApi.removeInstructionImage(
        recipeId,
        instruction.id
      );
      onImageUpdate(updatedInstruction);
      toast.success('Step image removed successfully!');
    } catch (error) {
      console.error('Error removing instruction image:', error);
      toast.error('Failed to remove image. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileChange(files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      handleFileChange(files[0]);
    }
  };

  const handleClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // If instruction has an image, show the image with remove option
  if (instruction.cloudinary_thumbnail_url || instruction.image_url) {
    const imageUrl = instruction.cloudinary_thumbnail_url || instruction.image_url;
    
    return (
      <div className={`relative inline-block ${className}`}>
        <img
          src={imageUrl || undefined}
          alt={`Step ${instruction.step_number} illustration`}
          className="max-w-full h-32 object-cover rounded-lg border border-gray-200"
        />
        {!isUploading && (
          <button
            onClick={handleRemoveImage}
            className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm hover:bg-red-600 transition-colors"
            title="Remove image"
          >
            ×
          </button>
        )}
        {isUploading && (
          <div className="absolute inset-0 bg-black bg-opacity-50 rounded-lg flex items-center justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
          </div>
        )}
      </div>
    );
  }

  // If no image, show upload area
  return (
    <div className={className}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileInputChange}
        className="hidden"
      />
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-lg p-4 cursor-pointer transition-colors
          ${dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        {isUploading ? (
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-500 mr-2"></div>
            <span className="text-sm text-gray-600">Uploading...</span>
          </div>
        ) : (
          <div className="flex items-center justify-center text-gray-500">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <span className="text-sm">Add step image</span>
          </div>
        )}
      </div>
    </div>
  );
};