import React from 'react';

interface VideoUploadModeProps {
  videoFile: File | null;
  youtubeUrl: string;
  videoPreview: { name: string; size: string } | null;
  isYoutubeLink: boolean;
  youtubeImportEnabled: boolean;
  dragActive: boolean;
  videoFileInputRef: React.RefObject<HTMLInputElement | null>;
  onSetYoutubeLink: (isYoutube: boolean) => void;
  onYoutubeUrlChange: (url: string) => void;
  onVideoFileInput: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onVideoDrop: (e: React.DragEvent) => void;
  onDrag: (e: React.DragEvent) => void;
  onClearVideo: () => void;
}

const VideoUploadMode: React.FC<VideoUploadModeProps> = ({
  youtubeUrl,
  videoPreview,
  isYoutubeLink,
  youtubeImportEnabled,
  dragActive,
  videoFileInputRef,
  onSetYoutubeLink,
  onYoutubeUrlChange,
  onVideoFileInput,
  onVideoDrop,
  onDrag,
  onClearVideo,
}) => {
  return (
    <div className="flex flex-col">
      <div className="pb-2">
        <label className="block text-base font-medium leading-normal" style={{color: '#1c120d'}}>
          Recipe Video *
        </label>
        <p className="text-sm mt-1" style={{color: '#9b644b'}}>
          Upload a cooking video or paste a YouTube link to extract the recipe.
        </p>
      </div>

      {/* Video source toggle: Upload File vs YouTube Link (only show toggle when YouTube is enabled) */}
      {youtubeImportEnabled ? (
        <div className="flex gap-2 mb-3">
          <button
            type="button"
            onClick={() => onSetYoutubeLink(false)}
            className={`flex-1 px-3 py-2 rounded-lg border-2 transition-all text-sm font-medium`}
            style={{
              borderColor: !isYoutubeLink ? '#8b5cf6' : '#e8d7cf',
              backgroundColor: !isYoutubeLink ? '#f5f3ff' : '#ffffff',
              color: !isYoutubeLink ? '#6d28d9' : '#9b644b',
            }}
          >
            📁 Upload File
          </button>
          <button
            type="button"
            onClick={() => onSetYoutubeLink(true)}
            className={`flex-1 px-3 py-2 rounded-lg border-2 transition-all text-sm font-medium`}
            style={{
              borderColor: isYoutubeLink ? '#8b5cf6' : '#e8d7cf',
              backgroundColor: isYoutubeLink ? '#f5f3ff' : '#ffffff',
              color: isYoutubeLink ? '#6d28d9' : '#9b644b',
            }}
          >
            ▶️ YouTube Link
          </button>
        </div>
      ) : null}

      {youtubeImportEnabled && isYoutubeLink ? (
        /* YouTube URL Input */
        <div>
          <input
            type="url"
            value={youtubeUrl}
            onChange={(e) => onYoutubeUrlChange(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/..."
            className="w-full px-4 py-3 rounded-xl border-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-purple-300"
            style={{
              borderColor: '#e8d7cf',
              backgroundColor: '#fcf9f8',
              color: '#1c120d',
            }}
          />
          <p className="text-xs mt-2" style={{ color: '#9b644b' }}>
            Paste any YouTube cooking video URL. We'll extract captions and parse the recipe automatically.
          </p>

          {/* YouTube info box */}
          <div className="mt-3 p-4 bg-purple-50 border border-purple-200 rounded-lg">
            <div className="flex items-start gap-2 mb-3">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium text-purple-800">How YouTube import works</span>
            </div>
            <p className="text-sm text-purple-700 mb-2">
              We use video captions when available (fast, ~10 seconds). If no captions exist, we'll download the audio and transcribe it (~30-60 seconds).
            </p>
            <div className="mt-2 pt-2 border-t border-purple-200">
              <p className="text-xs font-medium text-purple-800 mb-1">Requirements:</p>
              <ul className="text-xs text-purple-600 space-y-0.5">
                <li>• Maximum video duration: 20 minutes</li>
                <li>• Public or unlisted videos only</li>
                <li>• No live streams or playlists</li>
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <>
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
                  onClick={onClearVideo}
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
              onDragEnter={onDrag}
              onDragLeave={onDrag}
              onDragOver={onDrag}
              onDrop={onVideoDrop}
              onClick={() => videoFileInputRef.current?.click()}
            >
              <input
                ref={videoFileInputRef}
                type="file"
                accept="video/mp4,video/quicktime,video/webm,video/x-msvideo"
                onChange={onVideoFileInput}
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
        </>
      )}

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
  );
};

export { VideoUploadMode };
