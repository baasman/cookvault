import React, { useState, useEffect } from 'react';
import { recipesApi } from '../../services/recipesApi';
import type { MultiJobStatusResponse } from '../../types';

interface MultiProcessingProgressProps {
  multiJobId: number;
  onComplete: (recipeId: number) => void;
  onError: (error: string) => void;
}

export const MultiProcessingProgress: React.FC<MultiProcessingProgressProps> = ({
  multiJobId,
  onComplete,
  onError,
}) => {
  const [status, setStatus] = useState<MultiJobStatusResponse | null>(null);
  const [statusText, setStatusText] = useState('Preparing to process your recipe images...');
  const [isPolling, setIsPolling] = useState(true);

  useEffect(() => {
    if (!isPolling) return;

    const pollMultiJobStatus = async () => {
      try {
        console.log('Polling multi-job status for job ID:', multiJobId);
        const jobStatus = await recipesApi.getMultiJobStatus(multiJobId);
        console.log('Multi-job status response:', jobStatus);
        setStatus(jobStatus);

        // Update status text based on job state
        const processed = jobStatus.processed_images || 0;
        const total = jobStatus.total_images || 0;
        
        switch (jobStatus.status) {
          case 'pending':
            setStatusText('Preparing to process your recipe images...');
            break;
          case 'processing':
            setStatusText(`Processing images: ${processed} of ${total} completed`);
            break;
          case 'completed':
            setStatusText('All images processed successfully! Creating your recipe...');
            setIsPolling(false);
            if (jobStatus.recipe_id) {
              setTimeout(() => onComplete(jobStatus.recipe_id!), 1000);
            } else {
              onError('Recipe was processed but no recipe ID was returned');
            }
            break;
          case 'failed':
            setStatusText('Processing failed. Please try again.');
            setIsPolling(false);
            onError(jobStatus.error_message || 'Multi-image processing failed unexpectedly');
            break;
        }
      } catch (error) {
        console.error('Error polling multi-job status:', error);
        setIsPolling(false);
        onError(`Unable to check processing status: ${error instanceof Error ? error.message : 'Unknown error'}. Please refresh the page.`);
      }
    };

    // Poll immediately, then every 3 seconds (slightly longer than single image)
    pollMultiJobStatus();
    const interval = setInterval(pollMultiJobStatus, 3000);

    // Cleanup interval on unmount or when polling stops
    return () => clearInterval(interval);
  }, [multiJobId, isPolling, onComplete, onError]);

  // Stop polling after 10 minutes to prevent infinite polling (longer for multi-image)
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (isPolling) {
        setIsPolling(false);
        onError('Processing is taking longer than expected. Please check back later or contact support.');
      }
    }, 600000); // 10 minutes

    return () => clearTimeout(timeout);
  }, [isPolling, onError]);

  const getProgressBarWidth = () => {
    if (!status) return '10%';
    
    const processed = status.processed_images || 0;
    const total = status.total_images || 1;
    
    switch (status.status) {
      case 'pending':
        return '10%';
      case 'processing':
        // Calculate based on processed images
        const processingProgress = Math.min((processed / total) * 80 + 10, 90);
        return `${processingProgress}%`;
      case 'completed':
        return '100%';
      case 'failed':
        return '100%';
      default:
        return '10%';
    }
  };

  const getProgressBarColor = () => {
    if (!status) return '#f15f1c'; // accent color
    
    switch (status.status) {
      case 'failed':
        return '#dc2626'; // red-600
      case 'completed':
        return '#10b981'; // green-500
      default:
        return '#f15f1c'; // accent color
    }
  };

  const getProgressDetails = () => {
    if (!status) return null;
    
    const processed = status.processed_images || 0;
    const total = status.total_images || 0;
    
    return (
      <div className="text-sm mt-2" style={{ color: '#9b644b' }}>
        <p>Images processed: {processed} of {total}</p>
        {status.status === 'processing' && (
          <p className="mt-1">This usually takes 1-3 minutes for multiple images</p>
        )}
      </div>
    );
  };

  return (
    <div className="p-6 rounded-xl" style={{ backgroundColor: '#f8fafc', borderColor: '#e8d7cf', border: '1px solid' }}>
      <div className="text-center">
        {/* Processing Icon */}
        <div className="mb-4">
          {status?.status === 'completed' ? (
            <svg className="mx-auto h-12 w-12" style={{ color: '#10b981' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : status?.status === 'failed' ? (
            <svg className="mx-auto h-12 w-12" style={{ color: '#dc2626' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <div className="mx-auto h-12 w-12 flex items-center justify-center">
              <div
                className="animate-spin rounded-full h-8 w-8 border-b-2"
                style={{ borderColor: '#f15f1c' }}
              />
            </div>
          )}
        </div>

        {/* Status Title */}
        <h3 className="text-lg font-bold mb-2" style={{ color: status?.status === 'failed' ? '#dc2626' : '#1c120d' }}>
          {status?.status === 'completed' ? 'Processing Complete!' : 
           status?.status === 'failed' ? 'Processing Failed' : 
           'Processing Your Recipe Images...'}
        </h3>

        {/* Status Text */}
        <p className="mb-4" style={{ color: status?.status === 'failed' ? '#dc2626' : '#9b644b' }}>
          {statusText}
        </p>

        {/* Progress Bar */}
        <div className="mb-6 mx-auto max-w-md">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="h-2 rounded-full transition-all duration-500 ease-out"
              style={{
                backgroundColor: getProgressBarColor(),
                width: getProgressBarWidth(),
              }}
            />
          </div>
        </div>

        {/* Progress Details */}
        {getProgressDetails()}
      </div>
    </div>
  );
};