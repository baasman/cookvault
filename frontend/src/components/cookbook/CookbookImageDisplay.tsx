import React, { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { cookbooksApi } from '../../services/cookbooksApi';
import type { Cookbook } from '../../types';

interface CookbookImageDisplayProps {
  cookbook: Cookbook;
  canEdit?: boolean;
}

const CookbookImageDisplay: React.FC<CookbookImageDisplayProps> = ({ cookbook, canEdit = false }) => {
  const [dragActive, setDragActive] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: (file: File) => cookbooksApi.uploadCookbookImage(cookbook.id, file),
    onSuccess: () => {
      // Invalidate and refetch the cookbook data
      queryClient.invalidateQueries({ queryKey: ['cookbook', cookbook.id] });
      setImagePreview(null);
    },
    onError: (error) => {
      console.error('Cookbook image upload failed:', error);
      setImagePreview(null);
    },
  });

  const handleFileSelect = (file: File) => {
    // Validate file type
    const allowedTypes = ['image/png', 'image/jpg', 'image/jpeg', 'image/gif'];
    if (!allowedTypes.includes(file.type)) {
      alert('Please select a valid image file (PNG, JPG, JPEG, GIF)');
      return;
    }

    // Validate file size (5MB limit)
    if (file.size > 5 * 1024 * 1024) {
      alert('File size must be less than 5MB');
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);

    // Upload the file
    uploadMutation.mutate(file);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleClick = () => {
    if (canEdit) {
      fileInputRef.current?.click();
    }
  };

  // Show existing image
  if (cookbook.cover_image_url && !uploadMutation.isPending && !imagePreview) {
    return (
      <div className="relative group">
        <div className="aspect-[3/4] bg-gradient-to-br from-background-secondary to-primary-200 rounded-xl overflow-hidden">
          <img
            src={cookbook.cover_image_url}
            alt={cookbook.title}
            className="w-full h-full object-cover"
            onError={(e) => {
              // Fallback to placeholder if image fails to load
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
              target.nextElementSibling?.classList.remove('hidden');
            }}
          />
          
          {/* Placeholder fallback */}
          <div className="hidden absolute inset-0 flex items-center justify-center">
            <div className="text-center px-4">
              <svg className="h-16 w-16 mx-auto text-primary-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={1} 
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" 
                />
              </svg>
              <p className="text-sm text-primary-400 font-medium leading-tight">{cookbook.title}</p>
            </div>
          </div>
        </div>

        {/* Edit overlay for cookbook owners */}
        {canEdit && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpg,image/jpeg,image/gif"
              onChange={handleFileInput}
              className="hidden"
            />
            <div
              onClick={handleClick}
              className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-all duration-200 rounded-xl cursor-pointer flex items-center justify-center opacity-0 group-hover:opacity-100"
            >
              <div className="text-white text-center">
                <svg className="h-8 w-8 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span className="text-sm font-medium">Change Cover</span>
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  // Show upload area (no image exists or uploading)
  if (canEdit) {
    return (
      <div className="aspect-[3/4]">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpg,image/jpeg,image/gif"
          onChange={handleFileInput}
          className="hidden"
        />
        
        <div
          className={`w-full h-full border-2 border-dashed rounded-xl cursor-pointer transition-colors ${
            dragActive 
              ? 'border-accent bg-accent/5' 
              : 'border-gray-300 hover:border-accent/50'
          } ${uploadMutation.isPending ? 'opacity-50 pointer-events-none' : ''}`}
          style={{
            borderColor: dragActive ? '#f15f1c' : undefined,
            backgroundColor: dragActive ? 'rgba(241, 95, 28, 0.05)' : undefined
          }}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={handleClick}
        >
          <div className="flex flex-col items-center justify-center h-full px-4 text-center">
            {uploadMutation.isPending || imagePreview ? (
              <>
                {imagePreview && (
                  <img
                    src={imagePreview}
                    alt="Preview"
                    className="w-full h-full object-cover rounded-lg mb-2"
                  />
                )}
                <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-80 rounded-xl">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 mx-auto mb-2" style={{borderColor: '#f15f1c'}}></div>
                    <p className="text-sm font-medium" style={{color: '#1c120d'}}>Uploading...</p>
                  </div>
                </div>
              </>
            ) : (
              <>
                <svg className="h-12 w-12 mb-3" style={{color: '#9b644b'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <p className="text-sm font-medium mb-1" style={{color: '#1c120d'}}>
                  Add Cover Image
                </p>
                <p className="text-xs" style={{color: '#9b644b'}}>
                  Drop your image here or click to browse
                </p>
                <p className="text-xs mt-1" style={{color: '#9b644b'}}>
                  PNG, JPG, JPEG, GIF up to 5MB
                </p>
              </>
            )}
          </div>
        </div>

        {uploadMutation.isError && (
          <p className="text-red-600 text-sm mt-2">
            Failed to upload image. Please try again.
          </p>
        )}
      </div>
    );
  }

  // Read-only placeholder (no edit permission)
  return (
    <div className="aspect-[3/4] bg-gradient-to-br from-background-secondary to-primary-200 rounded-xl flex items-center justify-center">
      <div className="text-center px-4">
        <svg className="h-16 w-16 mx-auto text-primary-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={1} 
            d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" 
          />
        </svg>
        <p className="text-sm text-primary-400 font-medium leading-tight">{cookbook.title}</p>
      </div>
    </div>
  );
};

export { CookbookImageDisplay };