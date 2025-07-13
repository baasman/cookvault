import React, { useState, useRef } from 'react';
import { Button, Input } from '../ui';
import { CookbookSearch } from '../cookbook/CookbookSearch';
import { GoogleBooksSearch } from '../cookbook/GoogleBooksSearch';
import { cookbooksApi, type GoogleBook } from '../../services/cookbooksApi';
import type { UploadFormData } from '../../types';

interface UploadFormProps {
  onSubmit: (data: UploadFormData) => void;
  isLoading?: boolean;
  error?: string;
}

const UploadForm: React.FC<UploadFormProps> = ({ onSubmit, isLoading = false, error }) => {
  const [formData, setFormData] = useState<UploadFormData>({
    image: null,
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
  const [dragActive, setDragActive] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

    onSubmit(formData);
  };

  const clearImage = () => {
    setFormData(prev => ({ ...prev, image: null }));
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