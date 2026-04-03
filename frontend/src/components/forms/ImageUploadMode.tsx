import React from 'react';
import { isNativePlatform } from '../../utils/platform';
import type { ImagePreview } from '../../types';

interface ImageUploadModeProps {
  isMultiImage: boolean;
  image: File | null;
  images: File[];
  imagePreview: string | null;
  imagePreviews: ImagePreview[];
  dragActive: boolean;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  multiFileInputRef: React.RefObject<HTMLInputElement | null>;
  onDrag: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onFileInput: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onImageSelect: () => void;
  onAddMorePhotos: () => void;
  onAddMoreToSingleImage: () => void;
  onRemoveImage: (imageId: string) => void;
  onClearImage: () => void;
  onClearAllImages: () => void;
  onMoveImage: (fromIndex: number, toIndex: number) => void;
}

const ImageUploadMode: React.FC<ImageUploadModeProps> = ({
  isMultiImage,
  imagePreviews,
  dragActive,
  fileInputRef,
  multiFileInputRef,
  onDrag,
  onDrop,
  onFileInput,
  onImageSelect,
  onAddMorePhotos,
  onAddMoreToSingleImage,
  onRemoveImage,
  onClearImage,
  onClearAllImages,
  onMoveImage,
  imagePreview,
  images,
}) => {
  return (
    <div className="flex flex-col">
      <div className="pb-2">
        <label className="block text-base font-medium leading-normal" style={{color: '#1c120d'}}>
          Recipe Image{isMultiImage ? 's' : ''} *
        </label>
        {isMultiImage && images.length > 0 && (
          <p className="text-sm mt-1" style={{color: '#9b644b'}}>
            Multi-page mode: {images.length} page{images.length > 1 ? 's' : ''} selected
          </p>
        )}
      </div>

      {isMultiImage ? (
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
            onDragEnter={onDrag}
            onDragLeave={onDrag}
            onDragOver={onDrag}
            onDrop={onDrop}
            onClick={() => !isNativePlatform() && multiFileInputRef.current?.click()}
          >
            <input
              ref={multiFileInputRef}
              type="file"
              accept="image/png,image/jpg,image/jpeg,image/gif,image/bmp,image/tiff"
              multiple
              onChange={onFileInput}
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
                      onAddMorePhotos();
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
                    onClick={onAddMorePhotos}
                    className="text-xs font-medium hover:underline"
                    style={{ color: '#f15f1c' }}
                  >
                    + Add More
                  </button>
                  <button
                    type="button"
                    onClick={onClearAllImages}
                    className="text-xs text-red-600 hover:text-red-800"
                  >
                    Clear All
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {imagePreviews.map((imgPreview, index) => (
                  <div key={imgPreview.id} className="relative group">
                    <div className="relative border rounded-lg overflow-hidden" style={{borderColor: '#e8d7cf'}}>
                      <img
                        src={imgPreview.preview}
                        alt={`Recipe page ${index + 1}`}
                        className="w-full h-32 object-cover"
                      />
                      <div className="absolute top-2 left-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
                        Page {index + 1}
                      </div>
                      <button
                        type="button"
                        onClick={() => onRemoveImage(imgPreview.id)}
                        className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        ×
                      </button>
                    </div>

                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-gray-600 truncate" title={imgPreview.file.name}>
                        {imgPreview.file.name}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => onMoveImage(index, index - 1)}
                          disabled={index === 0}
                          className="text-xs p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Move up"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => onMoveImage(index, index + 1)}
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
          onDragEnter={onDrag}
          onDragLeave={onDrag}
          onDragOver={onDrag}
          onDrop={onDrop}
          onClick={onImageSelect}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpg,image/jpeg,image/gif,image/bmp,image/tiff"
            multiple
            onChange={onFileInput}
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
                onClearImage();
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
                onAddMoreToSingleImage();
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
  );
};

export { ImageUploadMode };
