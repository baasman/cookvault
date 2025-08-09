import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { UploadForm } from '../components/forms';
import { ProcessingProgress } from '../components/upload/ProcessingProgress';
import { MultiProcessingProgress } from '../components/upload/MultiProcessingProgress';
import { recipesApi } from '../services/recipesApi';
import type { UploadFormData, UploadResponse, MultiUploadResponse } from '../types';

const UploadPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<UploadResponse | MultiUploadResponse | null>(null);
  const [multiJobId, setMultiJobId] = useState<number | null>(null);
  const [processingJobId, setProcessingJobId] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isMultiProcessing, setIsMultiProcessing] = useState(false);

  const handleUpload = async (formData: UploadFormData) => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);
    setMultiJobId(null);
    setIsProcessing(false);
    setIsMultiProcessing(false);

    try {
      if (formData.isMultiImage && formData.images.length > 0) {
        // Handle multi-image upload
        let cookbook_id: number | undefined;
        
        // Determine cookbook ID based on form selection
        if (formData.create_new_cookbook) {
          // For now, we'll need to handle cookbook creation in the backend
          // The backend API should be enhanced to handle cookbook creation for multi-image uploads
          cookbook_id = undefined; // Will be handled by backend
        } else if (formData.search_existing_cookbook && formData.selected_existing_cookbook_id) {
          cookbook_id = formData.selected_existing_cookbook_id;
        } else if (formData.cookbook_id) {
          cookbook_id = formData.cookbook_id;
        }

        const result = await recipesApi.uploadMultipleImages(
          formData.images,
          cookbook_id,
          formData.page_number
        );
        
        setMultiJobId(result.multi_job_id);
        setIsMultiProcessing(true);
        
      } else if (!formData.isMultiImage && formData.image) {
        // Handle single image upload (existing logic)
        const uploadData = new FormData();
        uploadData.append('image', formData.image);
        
        if (formData.create_new_cookbook) {
          uploadData.append('create_new_cookbook', 'true');
          uploadData.append('new_cookbook_title', formData.new_cookbook_title || '');
          
          if (formData.new_cookbook_author) {
            uploadData.append('new_cookbook_author', formData.new_cookbook_author);
          }
          if (formData.new_cookbook_description) {
            uploadData.append('new_cookbook_description', formData.new_cookbook_description);
          }
          if (formData.new_cookbook_publisher) {
            uploadData.append('new_cookbook_publisher', formData.new_cookbook_publisher);
          }
          if (formData.new_cookbook_isbn) {
            uploadData.append('new_cookbook_isbn', formData.new_cookbook_isbn);
          }
          if (formData.new_cookbook_publication_date) {
            uploadData.append('new_cookbook_publication_date', formData.new_cookbook_publication_date);
          }
        } else if (formData.search_existing_cookbook && formData.selected_existing_cookbook_id) {
          uploadData.append('cookbook_id', formData.selected_existing_cookbook_id.toString());
        } else if (formData.cookbook_id) {
          uploadData.append('cookbook_id', formData.cookbook_id.toString());
        }
        
        if (formData.page_number) {
          uploadData.append('page_number', formData.page_number.toString());
        }

        const apiUrl = import.meta.env.VITE_API_URL || '/api';
        const response = await fetch(`${apiUrl}/recipes/upload`, {
          method: 'POST',
          body: uploadData,
          credentials: 'include',
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Upload failed');
        }

        const result: UploadResponse = await response.json();
        
        // Start processing monitoring for single image upload
        if (result.job_id) {
          setProcessingJobId(result.job_id);
          setIsProcessing(true);
        } else {
          // Fallback to old success display if no job_id
          setSuccess(result);
        }
      } else {
        throw new Error('Please select at least one image to upload');
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during upload');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewUpload = () => {
    setSuccess(null);
    setError(null);
    setMultiJobId(null);
    setProcessingJobId(null);
    setIsProcessing(false);
  };

  const isMultiUpload = (result: UploadResponse | MultiUploadResponse): result is MultiUploadResponse => {
    return 'multi_job_id' in result;
  };

  const handleProcessingComplete = (recipeId: number) => {
    setIsProcessing(false);
    setProcessingJobId(null);
    // Set success state with recipe ID for showing success banner
    const completionResponse: UploadResponse = { 
      message: 'Recipe processed successfully!', 
      job_id: processingJobId || 0, 
      recipe_id: recipeId 
    };
    setSuccess(completionResponse);
  };

  const handleMultiProcessingComplete = (recipeId: number) => {
    setIsMultiProcessing(false);
    setMultiJobId(null);
    // Set success state with recipe ID for showing success banner
    const completionResponse: UploadResponse = { 
      message: 'Multi-image recipe processed successfully!', 
      job_id: 0, // Not applicable for multi-image
      recipe_id: recipeId 
    };
    setSuccess(completionResponse);
  };

  const handleProcessingError = (errorMessage: string) => {
    setIsProcessing(false);
    setProcessingJobId(null);
    setError(errorMessage);
  };

  const handleMultiProcessingError = (errorMessage: string) => {
    setIsMultiProcessing(false);
    setMultiJobId(null);
    setError(errorMessage);
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Page Header */}
      <div className="text-center mb-8">
        <h1 className="text-page-title font-bold mb-4" style={{color: '#1c120d'}}>
          Upload Recipe
        </h1>
        <p className="text-lg" style={{color: '#9b644b'}}>
          Upload an image of your recipe and we'll convert it to digital format for you
        </p>
      </div>

      {/* Processing Progress */}
      {isProcessing && processingJobId && (
        <div className="mb-8">
          <ProcessingProgress
            jobId={processingJobId}
            onComplete={handleProcessingComplete}
            onError={handleProcessingError}
          />
        </div>
      )}

      {/* Multi-Image Processing Progress */}
      {isMultiProcessing && multiJobId && (
        <div className="mb-8">
          <MultiProcessingProgress
            multiJobId={multiJobId}
            onComplete={handleMultiProcessingComplete}
            onError={handleMultiProcessingError}
          />
        </div>
      )}

      {/* Success Message */}
      {success && !isProcessing && !isMultiProcessing && (
        <div className="mb-8 p-6 rounded-xl" style={{backgroundColor: '#d1fae5', borderColor: '#10b981'}}>
          <div className="text-center">
            <div className="mb-4">
              <svg className="mx-auto h-12 w-12" style={{color: '#10b981'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold" style={{color: '#065f46'}}>
              Upload Successful!
            </h3>
            <p className="mt-2" style={{color: '#047857'}}>
              {success.message}
            </p>
            <div className="mt-4 text-sm" style={{color: '#047857'}}>
              {!isMultiUpload(success) ? (
                <>
                  {'cookbook' in success && success.cookbook && (
                    <p>Added to cookbook: {success.cookbook.title}</p>
                  )}
                  {'page_number' in success && success.page_number && (
                    <p>Page: {success.page_number}</p>
                  )}
                  {success.recipe_id && (
                    <p className="mt-2">
                      <Link 
                        to={`/recipes/${success.recipe_id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View your recipe →
                      </Link>
                    </p>
                  )}
                </>
              ) : (
                <>
                  {/* For multi-image uploads that haven't completed processing yet */}
                  {(!('recipe_id' in success) || !success.recipe_id) && (
                    <p>Images uploaded successfully. Processing will begin shortly...</p>
                  )}
                  {/* For completed multi-image uploads */}
                  {'recipe_id' in success && success.recipe_id && (
                    <p className="mt-2">
                      <Link 
                        to={`/recipes/${success.recipe_id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View your recipe →
                      </Link>
                    </p>
                  )}
                </>
              )}
            </div>
            <div className="mt-6 flex justify-center gap-4">
              <button
                onClick={handleNewUpload}
                className="px-6 py-2 rounded-full font-bold transition-colors"
                style={{backgroundColor: '#10b981', color: 'white'}}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#059669'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#10b981'}
              >
                Upload Another Recipe
              </button>
              <a
                href="/recipes"
                className="px-6 py-2 rounded-full font-bold transition-colors inline-block"
                style={{backgroundColor: '#f1ece9', color: '#1c120d'}}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#e8d7cf'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#f1ece9'}
              >
                View All Recipes
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && !isProcessing && (
        <div className="mb-8 p-6 rounded-xl" style={{backgroundColor: '#fee2e2', borderColor: '#dc2626', border: '1px solid'}}>
          <div className="text-center">
            <div className="mb-4">
              <svg className="mx-auto h-12 w-12" style={{color: '#dc2626'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold mb-2" style={{color: '#dc2626'}}>
              Processing Failed
            </h3>
            <p className="mb-4" style={{color: '#dc2626'}}>
              {error}
            </p>
            <button
              onClick={handleNewUpload}
              className="px-6 py-2 rounded-full font-bold transition-colors"
              style={{backgroundColor: '#dc2626', color: 'white'}}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#b91c1c'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#dc2626'}
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Upload Form */}
      {!success && !isProcessing && !error && (
        <div className="flex justify-center">
          <UploadForm
            onSubmit={handleUpload}
            isLoading={isLoading}
            error={undefined}
          />
        </div>
      )}

      {/* Instructions */}
      <div className="mt-12 text-center">
        <h2 className="text-section-title font-bold mb-4" style={{color: '#1c120d'}}>
          How it works
        </h2>
        <div className="flex flex-col md:flex-row justify-center items-center gap-8 mt-6 max-w-2xl mx-auto" style={{padding: '0 3rem'}}>
          <div className="text-center max-w-32">
            <div className="w-6 h-6 mx-auto mb-1 rounded-full flex items-center justify-center" style={{backgroundColor: '#f1ece9'}}>
              <svg className="w-3 h-3" style={{color: '#f15f1c'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <h3 className="text-xs font-bold mb-1" style={{color: '#1c120d'}}>
              1. Upload
            </h3>
            <p className="text-xs leading-tight" style={{color: '#9b644b'}}>
              Upload recipe image
            </p>
          </div>
          
          <div className="text-center max-w-32">
            <div className="w-6 h-6 mx-auto mb-1 rounded-full flex items-center justify-center" style={{backgroundColor: '#f1ece9'}}>
              <svg className="w-3 h-3" style={{color: '#f15f1c'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 className="text-xs font-bold mb-1" style={{color: '#1c120d'}}>
              2. Process
            </h3>
            <p className="text-xs leading-tight" style={{color: '#9b644b'}}>
              System converts text
            </p>
          </div>
          
          <div className="text-center max-w-32">
            <div className="w-6 h-6 mx-auto mb-1 rounded-full flex items-center justify-center" style={{backgroundColor: '#f1ece9'}}>
              <svg className="w-3 h-3" style={{color: '#f15f1c'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-xs font-bold mb-1" style={{color: '#1c120d'}}>
              3. Organize
            </h3>
            <p className="text-xs leading-tight" style={{color: '#9b644b'}}>
              Digital recipe ready
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export { UploadPage };