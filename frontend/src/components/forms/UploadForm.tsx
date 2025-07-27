import React, { useState, useRef } from 'react';
import { Button, Input } from '../ui';
import { CookbookSearch } from '../cookbook/CookbookSearch';
import { GoogleBooksSearch } from '../cookbook/GoogleBooksSearch';
import { cookbooksApi, type GoogleBook } from '../../services/cookbooksApi';
import type { UploadFormData, ImagePreview } from '../../types';

interface UploadFormProps {
  onSubmit: (data: UploadFormData) => void;
  isLoading?: boolean;
  error?: string;
}

const UploadForm: React.FC<UploadFormProps> = ({ onSubmit, isLoading = false, error }) => {
  const [formData, setFormData] = useState<UploadFormData>({
    image: null,
    images: [],
    isMultiImage: false,
    cookbook_id: undefined,
    page_number: undefined,
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
  });
  
  const [copyrightConsents, setCopyrightConsents] = useState({
    rightsToShare: false,
    understandsPublic: false,
    personalUseOnly: false,
    noCopyrightViolation: false
  });
  const [dragActive, setDragActive] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imagePreviews, setImagePreviews] = useState<ImagePreview[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const multiFileInputRef = useRef<HTMLInputElement>(null);

  const handleConsentChange = (key: keyof typeof copyrightConsents) => {
    setCopyrightConsents(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const allConsentsGiven = Object.values(copyrightConsents).every(Boolean);

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
          setImagePreviews(prev => [...prev, ...newPreviews]);
          setFormData(prev => ({ 
            ...prev, 
            images: [...prev.images, ...validFiles] 
          }));
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
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      if (formData.isMultiImage || e.dataTransfer.files.length > 1) {
        // Switch to multi-image mode if multiple files dropped
        if (!formData.isMultiImage) {
          setFormData(prev => ({ ...prev, isMultiImage: true, image: null }));
          setImagePreview(null);
        }
        handleMultipleFiles(e.dataTransfer.files);
      } else {
        handleFileSelect(e.dataTransfer.files[0]);
      }
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      if (formData.isMultiImage) {
        handleMultipleFiles(e.target.files);
      } else {
        handleFileSelect(e.target.files[0]);
      }
    }
  };

  const handleMultiFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleMultipleFiles(e.target.files);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
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

    // Validate new cookbook creation if selected
    if (formData.create_new_cookbook && (!formData.new_cookbook_title || formData.new_cookbook_title.trim() === '')) {
      alert('Please enter a cookbook title');
      return;
    }

    // Validate cookbook search selection if selected
    if (formData.search_existing_cookbook && !formData.selected_existing_cookbook_id) {
      alert('Please select a cookbook from the search results');
      return;
    }

    // Validate online database selection if selected
    if (formData.search_google_books && !formData.selected_google_book) {
      alert('Please select a cookbook from the online database or enter details manually');
      return;
    }

    // No validation needed for no_cookbook option - it's always valid

    // Validate copyright consent
    if (!allConsentsGiven) {
      alert('Please acknowledge all copyright consent requirements before uploading.');
      return;
    }

    onSubmit(formData);
  };

  const clearImage = () => {
    setFormData(prev => ({ ...prev, image: null }));
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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
        return { ...prev, images: filteredFiles };
      }
      return prev;
    });
  };

  const clearAllImages = () => {
    setImagePreviews([]);
    setFormData(prev => ({ ...prev, images: [] }));
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

  const toggleUploadMode = () => {
    const newIsMultiImage = !formData.isMultiImage;
    
    if (newIsMultiImage) {
      // Switching to multi-image mode
      if (formData.image) {
        // Convert single image to multi-image format
        const reader = new FileReader();
        reader.onload = (e) => {
          const preview: ImagePreview = {
            file: formData.image!,
            preview: e.target?.result as string,
            id: generateImageId(),
            order: 0
          };
          setImagePreviews([preview]);
        };
        reader.readAsDataURL(formData.image);
        setFormData(prev => ({ 
          ...prev, 
          isMultiImage: true, 
          images: [prev.image!], 
          image: null 
        }));
        setImagePreview(null);
      } else {
        setFormData(prev => ({ ...prev, isMultiImage: true }));
      }
    } else {
      // Switching to single-image mode
      if (imagePreviews.length > 0) {
        const firstImage = imagePreviews[0];
        setFormData(prev => ({ 
          ...prev, 
          isMultiImage: false, 
          image: firstImage.file, 
          images: [] 
        }));
        setImagePreview(firstImage.preview);
        setImagePreviews([]);
      } else {
        setFormData(prev => ({ ...prev, isMultiImage: false, images: [] }));
      }
    }
  };

  return (
    <div className="flex flex-col w-full max-w-[512px] mx-auto">
      <form onSubmit={handleSubmit} className="flex flex-col gap-6 px-4 py-3">
        {/* Image Upload Area */}
        <div className="flex flex-col">
          <div className="flex items-center justify-between pb-2">
            <label className="block text-base font-medium leading-normal" style={{color: '#1c120d'}}>
              Recipe Image{formData.isMultiImage ? 's' : ''} *
            </label>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={toggleUploadMode}
                className="text-sm px-3 py-1 rounded-full border transition-colors"
                style={{
                  borderColor: '#e8d7cf',
                  backgroundColor: formData.isMultiImage ? '#f15f1c' : '#fcf9f8',
                  color: formData.isMultiImage ? 'white' : '#1c120d'
                }}
              >
                {formData.isMultiImage ? 'Multi-page' : 'Single page'}
              </button>
            </div>
          </div>
          
          {formData.isMultiImage ? (
            // Multi-image upload interface
            <div className="space-y-4">
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
                onClick={() => multiFileInputRef.current?.click()}
              >
                <input
                  ref={multiFileInputRef}
                  type="file"
                  accept="image/png,image/jpg,image/jpeg,image/gif,image/bmp,image/tiff"
                  multiple
                  onChange={handleMultiFileInput}
                  className="hidden"
                />
                
                <div className="flex flex-col items-center">
                  <svg className="w-8 h-8 mb-3" style={{color: '#9b644b'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="text-sm font-medium mb-1" style={{color: '#1c120d'}}>
                    Drop multiple recipe images here
                  </p>
                  <p className="text-xs" style={{color: '#9b644b'}}>
                    or click to browse files
                  </p>
                  <p className="text-xs mt-1" style={{color: '#9b644b'}}>
                    PNG, JPG, JPEG, GIF, BMP, TIFF • Max 10 images • 50MB total
                  </p>
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
                    <button
                      type="button"
                      onClick={clearAllImages}
                      className="text-xs text-red-600 hover:text-red-800"
                    >
                      Clear All
                    </button>
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
              onClick={() => formData.isMultiImage ? multiFileInputRef.current?.click() : fileInputRef.current?.click()}
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
          )}
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
                    selected_google_book: null,
                    page_number: undefined 
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
                    selected_google_book: null,
                    page_number: undefined 
                  }))}
                  className="mr-2 text-accent"
                />
                <span className="text-sm font-medium" style={{color: '#1c120d'}}>Search Online Database</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="cookbook_mode"
                  checked={formData.search_existing_cookbook}
                  onChange={() => setFormData(prev => ({ 
                    ...prev, 
                    create_new_cookbook: false,
                    search_existing_cookbook: true,
                    search_google_books: false,
                    no_cookbook: false,
                    cookbook_id: undefined,
                    selected_existing_cookbook_id: undefined,
                    selected_google_book: null,
                    page_number: undefined 
                  }))}
                  className="mr-2 text-accent"
                />
                <span className="text-sm font-medium" style={{color: '#1c120d'}}>Search for existing cookbook</span>
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
                    selected_google_book: null,
                    page_number: undefined 
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
                      // Create cookbook from Google Books
                      const cookbook = await cookbooksApi.createCookbookFromGoogleBooks(book.google_books_id);
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
                
                {/* Page Number for online database selection */}
                {formData.selected_google_book && (
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
              </>
            ) : formData.search_existing_cookbook ? (
              /* Cookbook Search */
              <>
                <CookbookSearch
                  onSelect={(cookbook) => {
                    setFormData(prev => ({ 
                      ...prev, 
                      selected_existing_cookbook_id: cookbook.id,
                      cookbook_search_query: cookbook.title 
                    }));
                  }}
                  onCreateNew={() => {
                    setFormData(prev => ({ 
                      ...prev, 
                      create_new_cookbook: true,
                      search_existing_cookbook: false,
                      search_google_books: false,
                      selected_existing_cookbook_id: undefined,
                      selected_google_book: null 
                    }));
                  }}
                />
                
                {/* Show selected cookbook info */}
                {formData.selected_existing_cookbook_id && (
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm font-medium text-green-800 mb-1">Selected Cookbook:</p>
                    <p className="text-sm text-green-700">{formData.cookbook_search_query}</p>
                    <button
                      type="button"
                      onClick={() => setFormData(prev => ({ 
                        ...prev, 
                        selected_existing_cookbook_id: undefined,
                        cookbook_search_query: '' 
                      }))}
                      className="text-xs text-green-600 hover:text-green-800 mt-1"
                    >
                      Change selection
                    </button>
                  </div>
                )}
                
                {/* Page Number for selected cookbook */}
                {formData.selected_existing_cookbook_id && (
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
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Publication Date"
                    type="date"
                    value={formData.new_cookbook_publication_date || ''}
                    onChange={(value) => setFormData(prev => ({ ...prev, new_cookbook_publication_date: value }))}
                  />
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

        {/* Copyright Consent Section */}
        <div className="flex flex-col gap-4">
          <h3 className="text-lg font-medium" style={{color: '#1c120d'}}>
            Copyright Consent
          </h3>
          
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-semibold text-gray-900 mb-2">Important Copyright Notice</h4>
            <p className="text-sm text-gray-700">
              Recipe ingredients and basic cooking methods are generally not copyrightable. However, 
              detailed creative descriptions, personal stories, unique presentations, and substantial 
              portions of published cookbooks may be protected by copyright.
            </p>
          </div>

          <div className="space-y-3">
            <label className="flex items-start space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={copyrightConsents.rightsToShare}
                onChange={() => handleConsentChange('rightsToShare')}
                className="mt-1 w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
                disabled={isLoading}
              />
              <span className="text-sm text-gray-700">
                <strong>I have the right to share this recipe.</strong> I either created this recipe myself, 
                have permission to share it, or believe it contains only non-copyrightable factual cooking information.
              </span>
            </label>

            <label className="flex items-start space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={copyrightConsents.understandsPublic}
                onChange={() => handleConsentChange('understandsPublic')}
                className="mt-1 w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
                disabled={isLoading}
              />
              <span className="text-sm text-gray-700">
                <strong>I understand this recipe may be made public.</strong> I may choose to make this recipe 
                publicly visible later, allowing other users to view, search for, and access it.
              </span>
            </label>

            <label className="flex items-start space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={copyrightConsents.personalUseOnly}
                onChange={() => handleConsentChange('personalUseOnly')}
                className="mt-1 w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
                disabled={isLoading}
              />
              <span className="text-sm text-gray-700">
                <strong>I grant others permission for personal use.</strong> If I make this recipe public, 
                I allow other users to use it for their personal, non-commercial cooking and meal preparation.
              </span>
            </label>

            <label className="flex items-start space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={copyrightConsents.noCopyrightViolation}
                onChange={() => handleConsentChange('noCopyrightViolation')}
                className="mt-1 w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
                disabled={isLoading}
              />
              <span className="text-sm text-gray-700">
                <strong>I will not violate copyright.</strong> I have not copied substantial portions of copyrighted 
                cookbooks, magazine articles, or other protected content without permission.
              </span>
            </label>
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
            disabled={isLoading || 
              (formData.isMultiImage ? formData.images.length === 0 : !formData.image) || 
              !allConsentsGiven}
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