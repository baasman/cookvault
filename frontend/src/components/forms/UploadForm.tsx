import React, { useState, useRef, useEffect } from 'react';
import { Button, Input } from '../ui';
import { GoogleBooksSearch } from '../cookbook/GoogleBooksSearch';
import { cookbooksApi, type GoogleBook } from '../../services/cookbooksApi';
import { captureRecipePhoto } from '../../services/cameraService';
import { isNativePlatform } from '../../utils/platform';
import type { UploadFormData, ImagePreview } from '../../types';

interface UploadFormProps {
  onSubmit: (data: UploadFormData) => void;
  isLoading?: boolean;
  error?: string;
  initialCookbookData?: { cookbookId?: number, cookbookTitle?: string } | null;
  initialMode?: 'image' | 'text' | 'url' | 'video';
}

const UploadForm: React.FC<UploadFormProps> = ({ onSubmit, isLoading = false, error, initialCookbookData, initialMode = 'image' }) => {
  const [formData, setFormData] = useState<UploadFormData>({
    image: null,
    images: [],
    isMultiImage: false,
    isTextMode: false, // Start in image mode by default
    recipeText: '',
    isUrlMode: false, // URL import mode
    recipeUrl: '', // URL for recipe import
    isVideoMode: false, // Video import mode
    videoFile: null, // Video file for import
    cookbook_id: undefined,
    create_new_cookbook: false,
    new_cookbook_title: '',
    new_cookbook_author: '',
    new_cookbook_description: '',
    new_cookbook_publisher: '',
    new_cookbook_isbn: '',
    new_cookbook_publication_date: '',
    search_existing_cookbook: false,
    selected_existing_cookbook_id: undefined,
    cookbook_search_query: '',
    search_google_books: false,
    selected_google_book: null,
    no_cookbook: true, // Default to no cookbook
    is_original_recipe: true, // Default to "my own recipe" (publishable)
    translate_to_english: false, // Default to no translation
  });

  const [dragActive, setDragActive] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imagePreviews, setImagePreviews] = useState<ImagePreview[]>([]);
  const [videoPreview, setVideoPreview] = useState<{ name: string; size: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const multiFileInputRef = useRef<HTMLInputElement>(null);
  const videoFileInputRef = useRef<HTMLInputElement>(null);

  // Check if a Google Books cookbook is selected (restricts recipe source choice)
  const isGoogleBooksCookbook = formData.search_google_books && formData.selected_google_book;

  const generateImageId = () => Math.random().toString(36).substr(2, 9);

  const validateFile = (file: File): boolean => {
    // Validate file type
    const allowedTypes = ['image/png', 'image/jpg', 'image/jpeg', 'image/gif', 'image/bmp', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
      alert('Please select valid image files (PNG, JPG, JPEG, GIF, BMP, TIFF)');
      return false;
    }

    // Validate file size (10MB limit per file)
    if (file.size > 10 * 1024 * 1024) {
      alert(`File "${file.name}" is too large. Each file must be less than 10MB`);
      return false;
    }

    return true;
  };

  const handleMultipleFiles = (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const validFiles = fileArray.filter(validateFile);
    
    if (validFiles.length === 0) return;

    // Check total file count (max 10 images)
    const totalFiles = imagePreviews.length + validFiles.length;
    if (totalFiles > 10) {
      alert(`Maximum 10 images allowed per recipe. You can add ${10 - imagePreviews.length} more images.`);
      return;
    }

    // Check total size (50MB limit)
    const currentSize = imagePreviews.reduce((sum, preview) => sum + preview.file.size, 0);
    const newFilesSize = validFiles.reduce((sum, file) => sum + file.size, 0);
    const totalSize = currentSize + newFilesSize;
    
    if (totalSize > 50 * 1024 * 1024) {
      alert('Total file size exceeds 50MB limit');
      return;
    }

    // Create previews for new files
    const newPreviews: ImagePreview[] = [];
    let processedCount = 0;

    validFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const preview: ImagePreview = {
          file,
          preview: e.target?.result as string,
          id: generateImageId(),
          order: imagePreviews.length + newPreviews.length
        };
        newPreviews.push(preview);
        processedCount++;

        if (processedCount === validFiles.length) {
          // All files processed, update state
          const newTotalFiles = [...imagePreviews, ...newPreviews];
          const newTotalFileList = [...formData.images, ...validFiles];
          
          setImagePreviews(newTotalFiles);
          setFormData(prev => ({ 
            ...prev, 
            images: newTotalFileList,
            image: null // Clear single image when we have multiple
          }));
          
          // Automatically set mode based on total file count
          setAutomaticMode(newTotalFileList.length);
          
          // Clear single image preview if we're now in multi mode
          if (newTotalFileList.length > 1) {
            setImagePreview(null);
          }
        }
      };
      reader.readAsDataURL(file);
    });
  };

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

    // Clear any existing multi-image data and set single image mode
    setFormData(prev => ({ 
      ...prev, 
      image: file,
      images: [], // Clear multi-image array
      isMultiImage: false // Single file = single image mode
    }));
    
    // Clear multi-image previews
    setImagePreviews([]);
    
    // Create single image preview
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
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      if (e.dataTransfer.files.length === 1) {
        // Single file dropped - use single image mode
        handleFileSelect(e.dataTransfer.files[0]);
      } else {
        // Multiple files dropped - use multi-image mode
        handleMultipleFiles(e.dataTransfer.files);
      }
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      if (e.target.files.length === 1) {
        // Single file selected - use single image mode
        handleFileSelect(e.target.files[0]);
      } else {
        // Multiple files selected - use multi-image mode
        handleMultipleFiles(e.target.files);
      }
    }
  };

  const validateVideoFile = (file: File): boolean => {
    // Validate file type
    const allowedTypes = ['video/mp4', 'video/quicktime', 'video/webm', 'video/x-msvideo'];
    if (!allowedTypes.includes(file.type)) {
      alert('Please select a valid video file (MP4, MOV, WebM, AVI)');
      return false;
    }

    // Validate file size (100MB limit)
    if (file.size > 100 * 1024 * 1024) {
      alert('Video file size must be less than 100MB');
      return false;
    }

    return true;
  };

  const handleVideoFileSelect = (file: File) => {
    if (!validateVideoFile(file)) return;

    setFormData(prev => ({
      ...prev,
      videoFile: file,
      // Clear image data when selecting video
      image: null,
      images: [],
      isMultiImage: false
    }));

    // Clear image previews
    setImagePreview(null);
    setImagePreviews([]);

    // Set video preview info
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
    setVideoPreview({
      name: file.name,
      size: `${sizeInMB} MB`
    });
  };

  const handleVideoFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleVideoFileSelect(e.target.files[0]);
    }
  };

  const handleVideoDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleVideoFileSelect(e.dataTransfer.files[0]);
    }
  };

  const clearVideo = () => {
    setFormData(prev => ({
      ...prev,
      videoFile: null
    }));
    setVideoPreview(null);
    if (videoFileInputRef.current) {
      videoFileInputRef.current.value = '';
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate based on mode
    if (formData.isUrlMode) {
      // Validate URL input
      if (!formData.recipeUrl || formData.recipeUrl.trim() === '') {
        alert('Please enter a URL');
        return;
      }
      // Basic URL validation
      try {
        const url = formData.recipeUrl.trim();
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
          // Try adding https
          new URL('https://' + url);
        } else {
          new URL(url);
        }
      } catch {
        alert('Please enter a valid URL');
        return;
      }
    } else if (formData.isTextMode) {
      // Validate text input
      if (!formData.recipeText || formData.recipeText.trim() === '') {
        alert('Please enter recipe text');
        return;
      }
      if (formData.recipeText.length > 50000) {
        alert('Recipe text exceeds maximum length of 50,000 characters');
        return;
      }
    } else if (formData.isVideoMode) {
      // Validate video input
      if (!formData.videoFile) {
        alert('Please select a video file to upload');
        return;
      }
    } else {
      // Validate images
      if (formData.isMultiImage) {
        if (formData.images.length === 0) {
          alert('Please select at least one image to upload');
          return;
        }
      } else {
        if (!formData.image) {
          alert('Please select an image to upload');
          return;
        }
      }
    }

    // Validate new cookbook creation if selected
    if (formData.create_new_cookbook && (!formData.new_cookbook_title || formData.new_cookbook_title.trim() === '')) {
      alert('Please enter a cookbook title');
      return;
    }

    // Validate cookbook selection if selected
    if (formData.search_google_books && !formData.selected_google_book) {
      alert('Please select a cookbook or enter details manually');
      return;
    }

    // Validate recipe source selection (skip for URL mode - always external)
    if (!formData.isUrlMode) {
      if (formData.is_original_recipe === undefined) {
        alert('Please indicate whether this is your own recipe or from another source.');
        return;
      }

      // If recipe is from a cookbook/source, require linking to a cookbook
      if (formData.is_original_recipe === false) {
        const hasCookbook = formData.create_new_cookbook ||
                            formData.search_google_books ||
                            formData.cookbook_id;
        if (!hasCookbook || formData.no_cookbook) {
          alert('Please link this recipe to a cookbook. Since this recipe is from a cookbook or other source, you must specify which cookbook it belongs to.');
          return;
        }
      }
    }

    onSubmit(formData);
  };

  const clearImage = () => {
    setFormData(prev => ({
      ...prev,
      image: null,
      isMultiImage: false
    }));
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle image selection - use Capacitor Camera on native, file input on web
  const handleImageSelect = async () => {
    if (isNativePlatform()) {
      try {
        const result = await captureRecipePhoto();
        if (result?.file) {
          // Use the file from camera service (already compressed and resized)
          handleFileSelect(result.file);
        }
      } catch (error) {
        console.error('Failed to capture photo:', error);
        // Fall back to file input if camera fails
        fileInputRef.current?.click();
      }
    } else {
      // On web, use standard file input
      fileInputRef.current?.click();
    }
  };

  // Handle adding more photos on native (doesn't replace existing)
  const handleAddMorePhotos = async () => {
    if (isNativePlatform()) {
      try {
        const result = await captureRecipePhoto();
        if (result?.file) {
          // Add to existing images instead of replacing
          handleMultipleFiles([result.file]);
        }
      } catch (error) {
        console.error('Failed to capture photo:', error);
        // Fall back to file input if camera fails
        multiFileInputRef.current?.click();
      }
    } else {
      // On web, use standard file input
      multiFileInputRef.current?.click();
    }
  };

  // Convert single image to multi-image mode AND capture another photo
  const addMoreToSingleImage = async () => {
    if (!formData.image || !imagePreview) return;

    // Store the current single image data before any state changes
    const existingFile = formData.image;
    const existingPreviewUrl = imagePreview;

    if (isNativePlatform()) {
      try {
        const result = await captureRecipePhoto();
        if (result?.file) {
          const newFile = result.file;
          // Create preview for the existing image
          const existingImagePreview: ImagePreview = {
            file: existingFile,
            preview: existingPreviewUrl,
            id: generateImageId(),
            order: 0
          };

          // Create preview for the new image
          const reader = new FileReader();
          reader.onload = (e) => {
            const newImagePreview: ImagePreview = {
              file: newFile,
              preview: e.target?.result as string,
              id: generateImageId(),
              order: 1
            };

            // Update all state at once with both images
            setImagePreviews([existingImagePreview, newImagePreview]);
            setFormData(prev => ({
              ...prev,
              images: [existingFile, newFile],
              image: null,
              isMultiImage: true
            }));
            setImagePreview(null);
          };
          reader.readAsDataURL(newFile);
        }
      } catch (error) {
        console.error('Failed to capture photo:', error);
      }
    } else {
      // On web, convert to multi-image mode and open file picker
      const existingImagePreview: ImagePreview = {
        file: existingFile,
        preview: existingPreviewUrl,
        id: generateImageId(),
        order: 0
      };
      setImagePreviews([existingImagePreview]);
      setFormData(prev => ({
        ...prev,
        images: [existingFile],
        image: null,
        isMultiImage: true
      }));
      setImagePreview(null);
      // Small delay to let state update, then open file picker
      setTimeout(() => multiFileInputRef.current?.click(), 50);
    }
  };

  const removeImage = (imageId: string) => {
    setImagePreviews(prev => {
      const filtered = prev.filter(img => img.id !== imageId);
      // Reorder remaining images
      return filtered.map((img, index) => ({ ...img, order: index }));
    });
    setFormData(prev => {
      const imageToRemove = imagePreviews.find(img => img.id === imageId);
      if (imageToRemove) {
        const filteredFiles = prev.images.filter(file => file !== imageToRemove.file);
        
        // Automatically adjust mode based on remaining file count
        if (filteredFiles.length === 1) {
          // Switch to single image mode
          const remainingFile = filteredFiles[0];
          const reader = new FileReader();
          reader.onload = (e) => {
            setImagePreview(e.target?.result as string);
          };
          reader.readAsDataURL(remainingFile);
          
          return { 
            ...prev, 
            images: [], 
            image: remainingFile,
            isMultiImage: false 
          };
        } else if (filteredFiles.length === 0) {
          // No files left - reset both modes
          setImagePreview(null);
          return { 
            ...prev, 
            images: [], 
            image: null,
            isMultiImage: false 
          };
        } else {
          // Still multiple files - stay in multi mode
          return { ...prev, images: filteredFiles };
        }
      }
      return prev;
    });
  };

  const clearAllImages = () => {
    setImagePreviews([]);
    setFormData(prev => ({ 
      ...prev, 
      images: [],
      isMultiImage: false 
    }));
    if (multiFileInputRef.current) {
      multiFileInputRef.current.value = '';
    }
  };

  const moveImage = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return;
    
    setImagePreviews(prev => {
      const newPreviews = [...prev];
      const [moved] = newPreviews.splice(fromIndex, 1);
      newPreviews.splice(toIndex, 0, moved);
      
      // Update order values
      return newPreviews.map((img, index) => ({ ...img, order: index }));
    });
    
    setFormData(prev => {
      const newFiles = [...prev.images];
      const [moved] = newFiles.splice(fromIndex, 1);
      newFiles.splice(toIndex, 0, moved);
      return { ...prev, images: newFiles };
    });
  };

  const setAutomaticMode = (fileCount: number) => {
    const shouldBeMultiImage = fileCount > 1;
    setFormData(prev => ({ ...prev, isMultiImage: shouldBeMultiImage }));
  };

  // Initialize form with cookbook data if provided (e.g., adding recipe from cookbook page)
  useEffect(() => {
    if (initialCookbookData?.cookbookId) {
      setFormData(prev => ({
        ...prev,
        no_cookbook: false,
        create_new_cookbook: false,
        search_google_books: false,
        search_existing_cookbook: false,
        cookbook_id: initialCookbookData.cookbookId,
        cookbook_search_query: initialCookbookData.cookbookTitle || `Cookbook ID: ${initialCookbookData.cookbookId}`
      }));
    }
  }, [initialCookbookData]);

  // Auto-set is_original_recipe to false when Google Books cookbook is selected
  useEffect(() => {
    if (formData.search_google_books && formData.selected_google_book) {
      setFormData(prev => ({
        ...prev,
        is_original_recipe: false // Recipes from published cookbooks cannot be made public
      }));
    }
  }, [formData.search_google_books, formData.selected_google_book]);

  // Set initial mode based on prop (e.g., from URL query parameter)
  useEffect(() => {
    if (initialMode === 'url') {
      setFormData(prev => ({
        ...prev,
        isTextMode: false,
        isUrlMode: true,
        isVideoMode: false,
        isMultiImage: false,
        is_original_recipe: false // URL imports are always from external source
      }));
    } else if (initialMode === 'text') {
      setFormData(prev => ({
        ...prev,
        isTextMode: true,
        isUrlMode: false,
        isVideoMode: false,
        isMultiImage: false
      }));
    } else if (initialMode === 'video') {
      setFormData(prev => ({
        ...prev,
        isTextMode: false,
        isUrlMode: false,
        isVideoMode: true,
        isMultiImage: false,
        is_original_recipe: false // Video imports are typically from external source
      }));
    }
    // 'image' is the default, no need to set it explicitly
  }, [initialMode]);


  return (
    <div className="flex flex-col w-full max-w-[512px] mx-auto">
      <form onSubmit={handleSubmit} className="flex flex-col gap-6 px-4 py-3">
        {/* Upload Mode Selector */}
        <div className="flex flex-col">
          <label className="block text-base font-medium leading-normal mb-2" style={{color: '#1c120d'}}>
            Upload Mode
          </label>
          <div className="flex gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => setFormData(prev => ({ ...prev, isTextMode: false, isUrlMode: false, isVideoMode: false }))}
              className={`flex-1 min-w-[70px] px-3 py-2 rounded-lg border-2 transition-all text-sm ${
                !formData.isTextMode && !formData.isUrlMode && !formData.isVideoMode
                  ? 'border-orange-400 bg-orange-50 text-orange-900'
                  : 'border-gray-300 bg-white text-gray-600 hover:border-gray-400'
              }`}
              style={{
                borderColor: !formData.isTextMode && !formData.isUrlMode && !formData.isVideoMode ? '#f15f1c' : '#e8d7cf',
                backgroundColor: !formData.isTextMode && !formData.isUrlMode && !formData.isVideoMode ? '#fcf9f8' : '#ffffff'
              }}
            >
              📷 Image
            </button>
            <button
              type="button"
              onClick={() => setFormData(prev => ({ ...prev, isTextMode: true, isUrlMode: false, isVideoMode: false, isMultiImage: false }))}
              className={`flex-1 min-w-[70px] px-3 py-2 rounded-lg border-2 transition-all text-sm ${
                formData.isTextMode
                  ? 'border-orange-400 bg-orange-50 text-orange-900'
                  : 'border-gray-300 bg-white text-gray-600 hover:border-gray-400'
              }`}
              style={{
                borderColor: formData.isTextMode ? '#f15f1c' : '#e8d7cf',
                backgroundColor: formData.isTextMode ? '#fcf9f8' : '#ffffff'
              }}
            >
              📝 Text
            </button>
            <button
              type="button"
              onClick={() => setFormData(prev => ({
                ...prev,
                isTextMode: false,
                isUrlMode: true,
                isVideoMode: false,
                isMultiImage: false,
                is_original_recipe: false // URL imports are always from external source
              }))}
              className={`flex-1 min-w-[70px] px-3 py-2 rounded-lg border-2 transition-all text-sm ${
                formData.isUrlMode
                  ? 'border-orange-400 bg-orange-50 text-orange-900'
                  : 'border-gray-300 bg-white text-gray-600 hover:border-gray-400'
              }`}
              style={{
                borderColor: formData.isUrlMode ? '#f15f1c' : '#e8d7cf',
                backgroundColor: formData.isUrlMode ? '#fcf9f8' : '#ffffff'
              }}
            >
              🔗 URL
            </button>
            <button
              type="button"
              onClick={() => setFormData(prev => ({
                ...prev,
                isTextMode: false,
                isUrlMode: false,
                isVideoMode: true,
                isMultiImage: false,
                is_original_recipe: false // Video imports are typically from external source (TikTok, etc.)
              }))}
              className={`flex-1 min-w-[70px] px-3 py-2 rounded-lg border-2 transition-all text-sm ${
                formData.isVideoMode
                  ? 'border-orange-400 bg-orange-50 text-orange-900'
                  : 'border-gray-300 bg-white text-gray-600 hover:border-gray-400'
              }`}
              style={{
                borderColor: formData.isVideoMode ? '#f15f1c' : '#e8d7cf',
                backgroundColor: formData.isVideoMode ? '#fcf9f8' : '#ffffff'
              }}
            >
              🎬 Video
            </button>
          </div>
        </div>

        {/* URL Input Area (shown when in URL mode) */}
        {formData.isUrlMode ? (
          <div className="flex flex-col">
            <div className="pb-2">
              <label className="block text-base font-medium leading-normal" style={{color: '#1c120d'}}>
                Recipe URL *
              </label>
              <p className="text-sm mt-1" style={{color: '#9b644b'}}>
                Paste the URL of a recipe page. Works best with popular recipe sites.
              </p>
            </div>
            <input
              type="url"
              value={formData.recipeUrl || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, recipeUrl: e.target.value }))}
              placeholder="https://example.com/delicious-recipe"
              className="w-full px-4 py-3 border rounded-lg text-base"
              style={{
                borderColor: '#e8d7cf',
                backgroundColor: '#fcf9f8',
              }}
              required
            />
            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-700 flex items-start gap-2">
                <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Recipes imported from URLs are for personal use only and cannot be shared publicly.</span>
              </p>
            </div>
          </div>
        ) : formData.isVideoMode ? (
          /* Video Upload Area (shown when in video mode) */
          <div className="flex flex-col">
            <div className="pb-2">
              <label className="block text-base font-medium leading-normal" style={{color: '#1c120d'}}>
                Recipe Video *
              </label>
              <p className="text-sm mt-1" style={{color: '#9b644b'}}>
                Upload a cooking video (TikTok, Instagram Reel, etc.) to extract the recipe.
              </p>
            </div>

            {videoPreview ? (
              /* Video Selected Preview */
              <div className="border-2 rounded-xl p-4" style={{ borderColor: '#e8d7cf', backgroundColor: '#fcf9f8' }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg flex items-center justify-center" style={{ backgroundColor: '#f15f1c' }}>
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium text-sm" style={{ color: '#1c120d' }}>{videoPreview.name}</p>
                      <p className="text-xs" style={{ color: '#9b644b' }}>{videoPreview.size}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={clearVideo}
                    className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                  >
                    <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            ) : (
              /* Video Drop Zone */
              <div
                className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                  dragActive
                    ? 'border-orange-400 bg-orange-50'
                    : 'border-gray-300 hover:border-gray-400'
                } cursor-pointer`}
                style={{
                  borderColor: dragActive ? '#f15f1c' : '#e8d7cf',
                  backgroundColor: dragActive ? '#fcf9f8' : '#fcf9f8'
                }}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleVideoDrop}
                onClick={() => videoFileInputRef.current?.click()}
              >
                <input
                  ref={videoFileInputRef}
                  type="file"
                  accept="video/mp4,video/quicktime,video/webm,video/x-msvideo"
                  onChange={handleVideoFileInput}
                  className="hidden"
                />

                <div className="flex flex-col items-center">
                  <svg className="w-10 h-10 mb-3" style={{ color: '#9b644b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <p className="text-sm font-medium mb-1" style={{ color: '#1c120d' }}>
                    Drop a video file here or click to browse
                  </p>
                  <p className="text-xs" style={{ color: '#9b644b' }}>
                    MP4, MOV, WebM, AVI (max 100MB, max 3 minutes)
                  </p>
                </div>
              </div>
            )}

            {/* How it works info box */}
            <div className="mt-3 p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <div className="flex items-start gap-2 mb-3">
                <svg className="w-5 h-5 flex-shrink-0 mt-0.5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-medium text-purple-800">How video import works</span>
              </div>
              <p className="text-sm text-purple-700 mb-3">
                We'll extract the recipe by analyzing the audio (speech) and video frames. Processing takes 30-90 seconds.
              </p>

              <div className="text-sm text-purple-700 space-y-2">
                <p className="font-medium">To save a TikTok video:</p>
                <ol className="list-decimal list-inside space-y-1 ml-2 text-purple-600">
                  <li>Open the TikTok video</li>
                  <li>Tap the Share button (arrow icon)</li>
                  <li>Select "Save video" to download to your device</li>
                  <li>Upload the saved video here</li>
                </ol>
              </div>

              <div className="mt-3 pt-3 border-t border-purple-200">
                <p className="text-xs font-medium text-purple-800 mb-1">Requirements:</p>
                <ul className="text-xs text-purple-600 space-y-0.5">
                  <li>• Maximum file size: 100MB</li>
                  <li>• Maximum duration: 3 minutes</li>
                  <li>• Supported formats: MP4, MOV, WebM, AVI</li>
                  <li>• Works best with videos that have clear audio</li>
                </ul>
              </div>
            </div>

            {/* Privacy notice */}
            <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-700 flex items-start gap-2">
                <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span>Recipes imported from videos are for personal use only and cannot be shared publicly.</span>
              </p>
            </div>
          </div>
        ) : formData.isTextMode ? (
          /* Text Upload Area (shown when in text mode) */
          <div className="flex flex-col">
            <div className="pb-2">
              <label className="block text-base font-medium leading-normal" style={{color: '#1c120d'}}>
                Recipe Text *
              </label>
              <p className="text-sm mt-1" style={{color: '#9b644b'}}>
                Paste or type your recipe below. Include title, ingredients, and instructions.
              </p>
            </div>
            <textarea
              value={formData.recipeText || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, recipeText: e.target.value }))}
              placeholder="Example:\n\nChocolate Chip Cookies\n\nIngredients:\n- 2 cups flour\n- 1 cup butter\n- 1 cup sugar\n...\n\nInstructions:\n1. Preheat oven to 350°F\n2. Mix dry ingredients\n..."
              className="w-full px-4 py-3 border rounded-lg resize-y font-mono text-sm"
              style={{
                borderColor: '#e8d7cf',
                backgroundColor: '#fcf9f8',
                minHeight: '300px',
                maxHeight: '600px'
              }}
              required
            />
            <div className="flex justify-between mt-2">
              <span className="text-xs" style={{color: '#9b644b'}}>
                {(formData.recipeText || '').length} / 50,000 characters
              </span>
              {(formData.recipeText || '').length > 45000 && (
                <span className="text-xs text-orange-600">
                  Approaching character limit
                </span>
              )}
            </div>
          </div>
        ) : (
        /* Image Upload Area (shown when not in text mode) */
        <div className="flex flex-col">
          <div className="pb-2">
            <label className="block text-base font-medium leading-normal" style={{color: '#1c120d'}}>
              Recipe Image{formData.isMultiImage ? 's' : ''} *
            </label>
            {formData.isMultiImage && formData.images.length > 0 && (
              <p className="text-sm mt-1" style={{color: '#9b644b'}}>
                Multi-page mode: {formData.images.length} page{formData.images.length > 1 ? 's' : ''} selected
              </p>
            )}
          </div>
          
          {formData.isMultiImage ? (
            // Multi-image upload interface
            <div className="space-y-4">
              <div
                className={`relative border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
                  dragActive
                    ? 'border-orange-400 bg-orange-50'
                    : 'border-gray-300 hover:border-gray-400'
                } ${!isNativePlatform() ? 'cursor-pointer' : ''}`}
                style={{
                  borderColor: dragActive ? '#f15f1c' : '#e8d7cf',
                  backgroundColor: dragActive ? '#fcf9f8' : '#fcf9f8'
                }}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => !isNativePlatform() && multiFileInputRef.current?.click()}
              >
                <input
                  ref={multiFileInputRef}
                  type="file"
                  accept="image/png,image/jpg,image/jpeg,image/gif,image/bmp,image/tiff"
                  multiple
                  onChange={handleFileInput}
                  className="hidden"
                />

                <div className="flex flex-col items-center">
                  <svg className="w-8 h-8 mb-3" style={{color: '#9b644b'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>

                  {isNativePlatform() ? (
                    // Native platform: Show camera button
                    <>
                      <p className="text-sm font-medium mb-3" style={{color: '#1c120d'}}>
                        Add recipe page photos
                      </p>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAddMorePhotos();
                        }}
                        className="px-6 py-3 rounded-lg font-medium text-white transition-colors"
                        style={{ backgroundColor: '#f15f1c' }}
                      >
                        <span className="flex items-center gap-2">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                          Take Photo
                        </span>
                      </button>
                      <p className="text-xs mt-3" style={{color: '#9b644b'}}>
                        Max 10 images • 50MB total
                      </p>
                    </>
                  ) : (
                    // Web: Show drag and drop instructions
                    <>
                      <p className="text-sm font-medium mb-1" style={{color: '#1c120d'}}>
                        Drop your recipe images here
                      </p>
                      <p className="text-xs" style={{color: '#9b644b'}}>
                        or click to browse files
                      </p>
                      <p className="text-xs mt-1" style={{color: '#9b644b'}}>
                        PNG, JPG, JPEG, GIF, BMP, TIFF • Max 10 images • 50MB total
                      </p>
                    </>
                  )}

                  {imagePreviews.length > 0 && (
                    <p className="text-xs mt-2 font-medium" style={{color: '#f15f1c'}}>
                      {imagePreviews.length} image{imagePreviews.length > 1 ? 's' : ''} selected
                    </p>
                  )}
                </div>
              </div>

              {/* Image Previews Gallery */}
              {imagePreviews.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium" style={{color: '#1c120d'}}>
                      Recipe Pages ({imagePreviews.length})
                    </h4>
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={handleAddMorePhotos}
                        className="text-xs font-medium hover:underline"
                        style={{ color: '#f15f1c' }}
                      >
                        + Add More
                      </button>
                      <button
                        type="button"
                        onClick={clearAllImages}
                        className="text-xs text-red-600 hover:text-red-800"
                      >
                        Clear All
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    {imagePreviews.map((imagePreview, index) => (
                      <div key={imagePreview.id} className="relative group">
                        <div className="relative border rounded-lg overflow-hidden" style={{borderColor: '#e8d7cf'}}>
                          <img
                            src={imagePreview.preview}
                            alt={`Recipe page ${index + 1}`}
                            className="w-full h-32 object-cover"
                          />
                          <div className="absolute top-2 left-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
                            Page {index + 1}
                          </div>
                          <button
                            type="button"
                            onClick={() => removeImage(imagePreview.id)}
                            className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            ×
                          </button>
                        </div>
                        
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-xs text-gray-600 truncate" title={imagePreview.file.name}>
                            {imagePreview.file.name}
                          </span>
                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              onClick={() => moveImage(index, index - 1)}
                              disabled={index === 0}
                              className="text-xs p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Move up"
                            >
                              ↑
                            </button>
                            <button
                              type="button"
                              onClick={() => moveImage(index, index + 1)}
                              disabled={index === imagePreviews.length - 1}
                              className="text-xs p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Move down"
                            >
                              ↓
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            // Single image upload interface
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
              onClick={handleImageSelect}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpg,image/jpeg,image/gif,image/bmp,image/tiff"
                multiple
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
                {/* Add more photos button - especially useful on mobile */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    addMoreToSingleImage();
                  }}
                  className="mt-3 w-full py-2 px-4 border-2 border-dashed rounded-lg text-sm font-medium transition-colors hover:border-accent hover:bg-accent/5"
                  style={{ borderColor: '#e8d7cf', color: '#9b644b' }}
                >
                  + Add more pages (multi-page recipe)
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <svg className="w-8 h-8 mb-3" style={{color: '#9b644b'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="text-sm font-medium mb-1" style={{color: '#1c120d'}}>
                  Drop your recipe image(s) here
                </p>
                <p className="text-xs" style={{color: '#9b644b'}}>
                  or click to browse files (multiple files will switch to multi-page automatically)
                </p>
                <p className="text-xs mt-1" style={{color: '#9b644b'}}>
                  PNG, JPG, JPEG, GIF, BMP, TIFF up to 10MB each
                </p>
              </div>
            )}
            </div>
          )}
        </div>
        )}

        {/* Translation Option */}
        <div className="flex flex-col gap-2">
          <label className="flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors hover:bg-gray-50"
            style={{ borderColor: formData.translate_to_english ? '#f15f1c' : '#e8d7cf', backgroundColor: formData.translate_to_english ? '#fcf9f8' : 'transparent' }}>
            <input
              type="checkbox"
              checked={formData.translate_to_english || false}
              onChange={(e) => setFormData(prev => ({ ...prev, translate_to_english: e.target.checked }))}
              className="mt-1 w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
              disabled={isLoading}
            />
            <div>
              <span className="font-medium text-gray-900 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
                Translate to English
              </span>
              <p className="text-sm text-gray-500">
                If the recipe is in another language, automatically translate it to English. The original text will be preserved.
              </p>
            </div>
          </label>
        </div>

        {/* Cookbook Information */}
        <div className="flex flex-col gap-4">
          <h3 className="text-lg font-medium" style={{color: '#1c120d'}}>
            Cookbook Information (Optional)
          </h3>
          
          {/* Cookbook Mode Selection */}
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="cookbook_mode"
                  checked={formData.no_cookbook}
                  onChange={() => setFormData(prev => ({ 
                    ...prev, 
                    create_new_cookbook: false,
                    search_existing_cookbook: false,
                    search_google_books: false,
                    no_cookbook: true,
                    cookbook_id: undefined,
                    selected_existing_cookbook_id: undefined,
                    selected_google_book: null
                  }))}
                  className="mr-2 text-accent"
                />
                <span className="text-sm font-medium" style={{color: '#1c120d'}}>No cookbook (standalone recipe)</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="cookbook_mode"
                  checked={formData.search_google_books}
                  onChange={() => setFormData(prev => ({
                    ...prev,
                    create_new_cookbook: false,
                    search_existing_cookbook: false,
                    search_google_books: true,
                    no_cookbook: false,
                    cookbook_id: undefined,
                    selected_existing_cookbook_id: undefined,
                    selected_google_book: null
                  }))}
                  className="mr-2 text-accent"
                />
                <span className="text-sm font-medium" style={{color: '#1c120d'}}>Search for cookbook</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="cookbook_mode"
                  checked={formData.create_new_cookbook}
                  onChange={() => setFormData(prev => ({
                    ...prev,
                    create_new_cookbook: true,
                    search_existing_cookbook: false,
                    search_google_books: false,
                    no_cookbook: false,
                    cookbook_id: undefined,
                    selected_existing_cookbook_id: undefined,
                    selected_google_book: null
                  }))}
                  className="mr-2 text-accent"
                />
                <span className="text-sm font-medium" style={{color: '#1c120d'}}>Create new cookbook</span>
              </label>
            </div>
          </div>
          
          <div className="flex flex-col gap-4">
            {formData.no_cookbook ? (
              /* No Cookbook - show nothing additional */
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  Your recipe will be uploaded as a standalone recipe without being linked to any cookbook.
                </p>
              </div>
            ) : formData.search_google_books ? (
              /* Online Database Search */
              <>
                <GoogleBooksSearch
                  onBookSelect={async (book: GoogleBook) => {
                    try {
                      // Create or get existing cookbook from Google Books
                      const { cookbook } = await cookbooksApi.createCookbookFromGoogleBooks(book.google_books_id);
                      setFormData(prev => ({
                        ...prev,
                        selected_google_book: book,
                        cookbook_id: cookbook.id,
                        new_cookbook_title: cookbook.title,
                        new_cookbook_author: cookbook.author || '',
                        new_cookbook_description: cookbook.description || '',
                        new_cookbook_publisher: cookbook.publisher || '',
                        new_cookbook_isbn: cookbook.isbn || '',
                        new_cookbook_publication_date: cookbook.publication_date
                          ? new Date(cookbook.publication_date).toISOString().split('T')[0]
                          : ''
                      }));
                    } catch (error) {
                      console.error('Error creating cookbook from Google Books:', error);
                      alert('Failed to create cookbook from online database. Please try again.');
                    }
                  }}
                  onManualEntry={() => {
                    setFormData(prev => ({ 
                      ...prev, 
                      create_new_cookbook: true,
                      search_google_books: false,
                      selected_google_book: null 
                    }));
                  }}
                  isLoading={isLoading}
                />
                
                {/* Show selected online book info */}
                {formData.selected_google_book && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm font-medium text-green-800 mb-2">Selected from online database:</p>
                    <div className="flex items-start space-x-3">
                      {formData.selected_google_book.thumbnail_url && (
                        <img
                          src={formData.selected_google_book.thumbnail_url}
                          alt={formData.selected_google_book.title}
                          className="w-12 h-16 object-cover rounded"
                        />
                      )}
                      <div className="flex-1">
                        <p className="text-sm font-medium text-green-800">{formData.selected_google_book.title}</p>
                        {formData.selected_google_book.author && (
                          <p className="text-xs text-green-700">by {formData.selected_google_book.author}</p>
                        )}
                        {formData.selected_google_book.publisher && (
                          <p className="text-xs text-green-600">{formData.selected_google_book.publisher}</p>
                        )}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setFormData(prev => ({ 
                        ...prev, 
                        selected_google_book: null,
                        cookbook_id: undefined,
                        new_cookbook_title: '',
                        new_cookbook_author: '',
                        new_cookbook_description: '',
                        new_cookbook_publisher: '',
                        new_cookbook_isbn: '',
                        new_cookbook_publication_date: ''
                      }))}
                      className="text-xs text-green-600 hover:text-green-800 mt-2"
                    >
                      Choose different book
                    </button>
                  </div>
                )}
                
              </>
            ) : (
              /* New Cookbook Creation Form */
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Cookbook Title *"
                    placeholder="Enter cookbook title"
                    value={formData.new_cookbook_title || ''}
                    onChange={(value) => setFormData(prev => ({ ...prev, new_cookbook_title: value }))}
                    required
                  />
                  <Input
                    label="Author"
                    placeholder="Enter author name"
                    value={formData.new_cookbook_author || ''}
                    onChange={(value) => setFormData(prev => ({ ...prev, new_cookbook_author: value }))}
                  />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Publisher"
                    placeholder="Enter publisher name"
                    value={formData.new_cookbook_publisher || ''}
                    onChange={(value) => setFormData(prev => ({ ...prev, new_cookbook_publisher: value }))}
                  />
                  <Input
                    label="ISBN"
                    placeholder="Enter ISBN"
                    value={formData.new_cookbook_isbn || ''}
                    onChange={(value) => setFormData(prev => ({ ...prev, new_cookbook_isbn: value }))}
                  />
                </div>
                
                <div className="w-full sm:w-48">
                  <Input
                    label="Publication Date"
                    type="date"
                    value={formData.new_cookbook_publication_date || ''}
                    onChange={(value) => setFormData(prev => ({ ...prev, new_cookbook_publication_date: value }))}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2" style={{color: '#1c120d'}}>
                    Description
                  </label>
                  <textarea
                    placeholder="Enter cookbook description (optional)"
                    value={formData.new_cookbook_description || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, new_cookbook_description: e.target.value }))}
                    rows={3}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent resize-none"
                    style={{borderColor: '#e8d7cf'}}
                  />
                </div>
              </>
            )}
          </div>
        </div>

        {/* Recipe Source Section - Hidden for URL mode since it's always external */}
        {!formData.isUrlMode && (
        <div className="flex flex-col gap-4">
          <h3 className="text-lg font-medium" style={{color: '#1c120d'}}>
            Recipe Source
          </h3>
          <p className="text-sm text-gray-600">
            This helps us understand what can be shared publicly.
          </p>

          <div className="space-y-3">
            <label className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
              formData.is_original_recipe === true ? 'border-orange-500 bg-orange-50' : 'border-gray-200 hover:bg-gray-50'
            } ${isGoogleBooksCookbook ? 'opacity-50 cursor-not-allowed' : ''}`}>
              <input
                type="radio"
                name="recipe_source"
                checked={formData.is_original_recipe === true}
                onChange={() => setFormData({...formData, is_original_recipe: true})}
                className="mt-1 w-4 h-4 text-orange-600 border-gray-300 focus:ring-orange-500"
                disabled={isLoading || isGoogleBooksCookbook}
              />
              <div>
                <span className="font-medium text-gray-900">This is my own recipe</span>
                <p className="text-sm text-gray-500">
                  I created this recipe myself or it's a family recipe. I can choose to share it publicly later.
                </p>
              </div>
            </label>

            <label className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
              formData.is_original_recipe === false ? 'border-orange-500 bg-orange-50' : 'border-gray-200 hover:bg-gray-50'
            }`}>
              <input
                type="radio"
                name="recipe_source"
                checked={formData.is_original_recipe === false}
                onChange={() => setFormData({...formData, is_original_recipe: false})}
                className="mt-1 w-4 h-4 text-orange-600 border-gray-300 focus:ring-orange-500"
                disabled={isLoading}
              />
              <div>
                <span className="font-medium text-gray-900">This is from a cookbook or other source</span>
                <p className="text-sm text-gray-500">
                  I'm saving this for personal use only. It will remain private and cannot be shared publicly.
                </p>
              </div>
            </label>
          </div>

          {isGoogleBooksCookbook && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-700">
                Since you're adding this recipe from a published cookbook, it will be saved for personal use only and cannot be made public.
              </p>
            </div>
          )}

          {/* Warning when "from cookbook" is selected but no cookbook is linked */}
          {formData.is_original_recipe === false && formData.no_cookbook && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
              <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p className="text-sm text-amber-700">
                Please select a cookbook option above. Since this recipe is from a cookbook or other source, you must link it to a cookbook.
              </p>
            </div>
          )}
        </div>
        )}

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
            disabled={isLoading ||
              (formData.isUrlMode
                ? !formData.recipeUrl || formData.recipeUrl.trim() === ''
                : formData.isVideoMode
                  ? !formData.videoFile
                  : formData.isTextMode
                    ? !formData.recipeText || formData.recipeText.trim() === ''
                    : (formData.isMultiImage ? formData.images.length === 0 : !formData.image)
              ) ||
              (!formData.isUrlMode && !formData.isVideoMode && formData.is_original_recipe === undefined) ||
              (!formData.isUrlMode && !formData.isVideoMode && formData.is_original_recipe === false && formData.no_cookbook)}
            className="min-w-[200px]"
          >
            {isLoading ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Converting...
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