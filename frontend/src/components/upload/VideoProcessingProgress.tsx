import React, { useState, useEffect } from 'react';
import { recipesApi } from '../../services/recipesApi';
import type { VideoProcessingStatus } from '../../types';

interface VideoProcessingProgressProps {
  videoJobId: number;
  onComplete: (recipeId: number) => void;
  onError: (error: string) => void;
}

interface VideoJobStatus {
  status: VideoProcessingStatus;
  progress_message?: string;
  progress_percentage: number;
  error_message?: string;
  recipe_id?: number;
}

const STATUS_DETAILS: Record<VideoProcessingStatus, { label: string; icon: string }> = {
  pending: { label: 'Preparing video', icon: '⏳' },
  uploading: { label: 'Uploading video', icon: '📤' },
  extracting_audio: { label: 'Extracting audio', icon: '🎵' },
  transcribing: { label: 'Transcribing speech', icon: '📝' },
  extracting_frames: { label: 'Extracting video frames', icon: '🎬' },
  analyzing_frames: { label: 'Analyzing visual content', icon: '👁️' },
  parsing_recipe: { label: 'Creating recipe', icon: '📖' },
  completed: { label: 'Recipe ready!', icon: '✅' },
  failed: { label: 'Processing failed', icon: '❌' },
};

export const VideoProcessingProgress: React.FC<VideoProcessingProgressProps> = ({
  videoJobId,
  onComplete,
  onError,
}) => {
  const [jobStatus, setJobStatus] = useState<VideoJobStatus>({
    status: 'pending',
    progress_percentage: 0,
  });
  const [isPolling, setIsPolling] = useState(true);

  useEffect(() => {
    if (!isPolling) return;

    const pollJobStatus = async () => {
      try {
        const status = await recipesApi.getVideoJobStatus(videoJobId);
        setJobStatus({
          status: status.status,
          progress_message: status.progress_message,
          progress_percentage: status.progress_percentage,
          error_message: status.error_message,
          recipe_id: status.recipe_id,
        });

        if (status.status === 'completed') {
          setIsPolling(false);
          if (status.recipe_id) {
            setTimeout(() => onComplete(status.recipe_id!), 1000);
          }
        } else if (status.status === 'failed') {
          setIsPolling(false);
          onError(status.error_message || 'Video processing failed unexpectedly');
        }
      } catch (error) {
        console.error('Error polling video job status:', error);
        setIsPolling(false);
        onError(`Unable to check processing status: ${error instanceof Error ? error.message : 'Unknown error'}. Please refresh the page.`);
      }
    };

    // Poll immediately, then every 3 seconds (video processing takes longer)
    pollJobStatus();
    const interval = setInterval(pollJobStatus, 3000);

    return () => clearInterval(interval);
  }, [videoJobId, isPolling, onComplete, onError]);

  // Stop polling after 10 minutes (video processing can take longer)
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (isPolling) {
        setIsPolling(false);
        onError('Processing is taking longer than expected. Please check back later or contact support.');
      }
    }, 600000); // 10 minutes

    return () => clearTimeout(timeout);
  }, [isPolling, onError]);

  const getProgressBarColor = () => {
    switch (jobStatus.status) {
      case 'failed':
        return '#dc2626'; // red-600
      case 'completed':
        return '#10b981'; // green-500
      default:
        return '#8b5cf6'; // purple-500 for video
    }
  };

  const statusDetail = STATUS_DETAILS[jobStatus.status] || STATUS_DETAILS.pending;

  return (
    <div className="p-6 rounded-xl" style={{ backgroundColor: '#f5f3ff', borderColor: '#c4b5fd', border: '1px solid' }}>
      <div className="text-center">
        {/* Processing Icon */}
        <div className="mb-4">
          {jobStatus.status === 'completed' ? (
            <svg className="mx-auto h-12 w-12" style={{ color: '#10b981' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : jobStatus.status === 'failed' ? (
            <svg className="mx-auto h-12 w-12" style={{ color: '#dc2626' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <div className="mx-auto h-12 w-12 flex items-center justify-center">
              <div
                className="animate-spin rounded-full h-8 w-8 border-b-2"
                style={{ borderColor: '#8b5cf6' }}
              />
            </div>
          )}
        </div>

        {/* Status Title */}
        <h3 className="text-lg font-bold mb-2" style={{ color: jobStatus.status === 'failed' ? '#dc2626' : '#1c120d' }}>
          {jobStatus.status === 'completed' ? 'Recipe Extracted!' :
           jobStatus.status === 'failed' ? 'Processing Failed' :
           'Extracting Recipe from Video...'}
        </h3>

        {/* Current Stage */}
        <div className="mb-4 flex items-center justify-center gap-2">
          <span className="text-xl">{statusDetail.icon}</span>
          <span style={{ color: jobStatus.status === 'failed' ? '#dc2626' : '#7c3aed' }} className="font-medium">
            {jobStatus.progress_message || statusDetail.label}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="mb-4 mx-auto max-w-md">
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="h-3 rounded-full transition-all duration-500 ease-out"
              style={{
                backgroundColor: getProgressBarColor(),
                width: `${Math.max(5, jobStatus.progress_percentage)}%`,
              }}
            />
          </div>
          <p className="mt-2 text-sm font-medium" style={{ color: '#7c3aed' }}>
            {jobStatus.progress_percentage}%
          </p>
        </div>

        {/* Stage indicators */}
        {jobStatus.status !== 'completed' && jobStatus.status !== 'failed' && (
          <div className="flex justify-center gap-2 flex-wrap mt-4">
            {(['extracting_audio', 'transcribing', 'extracting_frames', 'analyzing_frames', 'parsing_recipe'] as VideoProcessingStatus[]).map((stage) => {
              const stageIndex = ['pending', 'uploading', 'extracting_audio', 'transcribing', 'extracting_frames', 'analyzing_frames', 'parsing_recipe', 'completed'].indexOf(stage);
              const currentIndex = ['pending', 'uploading', 'extracting_audio', 'transcribing', 'extracting_frames', 'analyzing_frames', 'parsing_recipe', 'completed'].indexOf(jobStatus.status);
              const isActive = currentIndex === stageIndex;
              const isComplete = currentIndex > stageIndex;

              return (
                <div
                  key={stage}
                  className={`px-2 py-1 rounded-full text-xs ${
                    isActive ? 'bg-purple-500 text-white' :
                    isComplete ? 'bg-purple-200 text-purple-700' :
                    'bg-gray-100 text-gray-400'
                  }`}
                >
                  {STATUS_DETAILS[stage].label}
                </div>
              );
            })}
          </div>
        )}

        {/* Time estimate */}
        {jobStatus.status !== 'completed' && jobStatus.status !== 'failed' && (
          <p className="mt-4 text-sm" style={{ color: '#9b644b' }}>
            Video processing usually takes 30-90 seconds
          </p>
        )}

        {/* Error message */}
        {jobStatus.status === 'failed' && jobStatus.error_message && (
          <p className="mt-4 text-sm" style={{ color: '#dc2626' }}>
            {jobStatus.error_message}
          </p>
        )}
      </div>
    </div>
  );
};
