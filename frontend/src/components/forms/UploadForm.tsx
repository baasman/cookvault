import React, { useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Input } from '../ui';
import { cookbooksApi } from '../../services/cookbooksApi';
import { useAuth } from '../../contexts/AuthContext';
import type { UploadFormData, Cookbook } from '../../types';

interface UploadFormProps {
  onSubmit: (data: UploadFormData) => void;
  isLoading?: boolean;
  error?: string;
}

const UploadForm: React.FC<UploadFormProps> = ({ onSubmit, isLoading = false, error }) => {
  const { isAuthenticated } = useAuth();
  const [formData, setFormData] = useState<UploadFormData>({
    image: null as File | null,
    cookbook_id: undefined,
    page_number: undefined,
  });
  const [dragActive, setDragActive] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch user's cookbooks for selection
  const { data: cookbooksData } = useQuery({
    queryKey: ['cookbooks', 'all'],
    queryFn: () => cookbooksApi.fetchCookbooks({ per_page: 100 }), // Get all cookbooks
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const handleFileSelect = (file: File) => {
    // Validate file type
    const allowedTypes = ['image/png', 'image/jpg', 'image/jpeg', 'image/gif', 'image/bmp', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
      alert('Please select a valid image file (PNG, JPG, JPEG, GIF, BMP, TIFF)');
      return;
    }

    // Validate file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
      alert('File size must be less than 10MB');
      return;
    }

    setFormData(prev => ({ ...prev, image: file }));
    
    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.image) {
      alert('Please select an image to upload');
      return;
    }

    onSubmit(formData);
  };

  const clearImage = () => {
    setFormData(prev => ({ ...prev, image: null as File | null }));
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex flex-col w-full max-w-[512px] mx-auto">
      <form onSubmit={handleSubmit} className="flex flex-col gap-6 px-4 py-3">
        {/* Image Upload Area */}
        <div className="flex flex-col">
          <label className="block text-base font-medium leading-normal pb-2" style={{color: '#1c120d'}}>
            Recipe Image *
          </label>
          
          <div
            className={`relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              dragActive 
                ? 'border-orange-400 bg-orange-50' 
                : 'border-gray-300 hover:border-gray-400'
            }`}
            style={{
              borderColor: dragActive ? '#f15f1c' : '#e8d7cf',
              backgroundColor: dragActive ? '#fcf9f8' : '#fcf9f8'
            }}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpg,image/jpeg,image/gif,image/bmp,image/tiff"
              onChange={handleFileInput}
              className="hidden"
            />
            
            {imagePreview ? (
              <div className="relative">
                <img
                  src={imagePreview}
                  alt="Recipe preview"
                  className="max-w-full max-h-64 mx-auto rounded-lg"
                />
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    clearImage();
                  }}
                  className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold"
                >
                  ×
                </button>
                <p className="mt-2 text-sm" style={{color: '#9b644b'}}>
                  Click to change image
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <svg className="w-8 h-8 mb-3" style={{color: '#9b644b'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="text-sm font-medium mb-1" style={{color: '#1c120d'}}>
                  Drop your recipe image here
                </p>
                <p className="text-xs" style={{color: '#9b644b'}}>
                  or click to browse files
                </p>
                <p className="text-xs mt-1" style={{color: '#9b644b'}}>
                  PNG, JPG, JPEG, GIF, BMP, TIFF up to 10MB
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Cookbook Information */}
        <div className="flex flex-col gap-4">
          <h3 className="text-lg font-medium" style={{color: '#1c120d'}}>
            Cookbook Information (Optional)
          </h3>
          
          <div className="flex flex-col gap-4">
            {/* Cookbook Selection */}
            <div>
              <label className="block text-sm font-medium mb-2" style={{color: '#1c120d'}}>
                Select Cookbook
              </label>
              <select
                value={formData.cookbook_id || ''}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  cookbook_id: e.target.value ? parseInt(e.target.value, 10) : undefined 
                }))}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
                style={{borderColor: '#e8d7cf'}}
              >
                <option value="">No cookbook (standalone recipe)</option>
                {cookbooksData?.cookbooks?.map((cookbook: Cookbook) => (
                  <option key={cookbook.id} value={cookbook.id}>
                    {cookbook.title}
                    {cookbook.author && ` by ${cookbook.author}`}
                    {` (${cookbook.recipe_count} recipe${cookbook.recipe_count !== 1 ? 's' : ''})`}
                  </option>
                ))}
              </select>
              {cookbooksData?.cookbooks?.length === 0 && (
                <p className="text-xs mt-1" style={{color: '#9b644b'}}>
                  No cookbooks found. <a href="/cookbooks" className="text-accent hover:underline">Create your first cookbook</a> to organize your recipes.
                </p>
              )}
            </div>
            
            {/* Page Number - only show when cookbook is selected */}
            {formData.cookbook_id && (
              <div className="w-full sm:w-48">
                <Input
                  label="Page Number"
                  type="number"
                  placeholder="Page number in cookbook"
                  value={formData.page_number?.toString() || ''}
                  onChange={(value) => setFormData(prev => ({ 
                    ...prev, 
                    page_number: value ? parseInt(value, 10) : undefined 
                  }))}
                />
              </div>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 rounded-xl" style={{backgroundColor: '#fee2e2', color: '#dc2626'}}>
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-center pt-4">
          <Button
            type="submit"
            variant="primary"
            size="lg"
            disabled={isLoading || !formData.image}
            className="min-w-[200px]"
          >
            {isLoading ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </div>
            ) : (
              'Upload Recipe'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
};

export { UploadForm };