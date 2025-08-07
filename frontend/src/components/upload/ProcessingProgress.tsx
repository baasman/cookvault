import React, { useState, useEffect } from 'react';
import { recipesApi } from '../../services/recipesApi';

interface ProcessingProgressProps {
  jobId: number;
  onComplete: (recipeId: number) => void;
  onError: (error: string) => void;
}

interface JobStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  recipe_id?: number;
  progress_percentage?: number;
}

export const ProcessingProgress: React.FC<ProcessingProgressProps> = ({
  jobId,
  onComplete,
  onError,
}) => {
  const [status, setStatus] = useState<JobStatus>({ status: 'pending' });
  const [statusText, setStatusText] = useState('Preparing to process your recipe...');
  const [isPolling, setIsPolling] = useState(true);

  useEffect(() => {
    if (!isPolling) return;

    const pollJobStatus = async () => {
      try {
        console.log('Polling job status for job ID:', jobId);
        const jobStatus = await recipesApi.getJobStatus(jobId);
        console.log('Job status response:', jobStatus);
        setStatus(jobStatus);

        // Update status text based on job state
        switch (jobStatus.status) {
          case 'pending':
            setStatusText('Preparing to process your recipe...');
            break;
          case 'processing':
            setStatusText('Extracting text and converting to structured recipe...');
            break;
          case 'completed':
            setStatusText('Recipe processing complete!');
            setIsPolling(false);
            if (jobStatus.recipe_id) {
              setTimeout(() => onComplete(jobStatus.recipe_id!), 1000);
            }
            break;
          case 'failed':
            setStatusText('Processing failed. Please try again.');
            setIsPolling(false);
            onError(jobStatus.error_message || 'Processing failed unexpectedly');
            break;
        }
      } catch (error) {
        console.error('Error polling job status:', error);
        console.error('Error details:', error);
        setIsPolling(false);
        onError(`Unable to check processing status: ${error instanceof Error ? error.message : 'Unknown error'}. Please refresh the page.`);
      }
    };

    // Poll immediately, then every 2 seconds
    pollJobStatus();
    const interval = setInterval(pollJobStatus, 2000);

    // Cleanup interval on unmount or when polling stops
    return () => clearInterval(interval);
  }, [jobId, isPolling, onComplete, onError]);

  // Stop polling after 5 minutes to prevent infinite polling
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (isPolling) {
        setIsPolling(false);
        onError('Processing is taking longer than expected. Please check back later or contact support.');
      }
    }, 300000); // 5 minutes

    return () => clearTimeout(timeout);
  }, [isPolling, onError]);

  const getProgressBarWidth = () => {
    switch (status.status) {
      case 'pending':
        return '20%';
      case 'processing':
        return '70%';
      case 'completed':
        return '100%';
      case 'failed':
        return '100%';
      default:
        return '20%';
    }
  };

  const getProgressBarColor = () => {
    switch (status.status) {
      case 'failed':
        return '#dc2626'; // red-600
      case 'completed':
        return '#10b981'; // green-500
      default:
        return '#f15f1c'; // accent color
    }
  };

  return (
    <div className="p-6 rounded-xl" style={{ backgroundColor: '#f8fafc', borderColor: '#e8d7cf', border: '1px solid' }}>
      <div className="text-center">
        {/* Processing Icon */}
        <div className="mb-4">
          {status.status === 'completed' ? (
            <svg className="mx-auto h-12 w-12" style={{ color: '#10b981' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : status.status === 'failed' ? (
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
        <h3 className="text-lg font-bold mb-2" style={{ color: status.status === 'failed' ? '#dc2626' : '#1c120d' }}>
          {status.status === 'completed' ? 'Processing Complete!' : 
           status.status === 'failed' ? 'Processing Failed' : 
           'Processing Your Recipe...'}
        </h3>

        {/* Status Text */}
        <p className="mb-4" style={{ color: status.status === 'failed' ? '#dc2626' : '#9b644b' }}>
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

        {/* Job Details */}
        <div className="text-sm" style={{ color: '#9b644b' }}>
          {status.status === 'processing' && (
            <p>This usually takes 30-60 seconds</p>
          )}
        </div>
      </div>
    </div>
  );
};