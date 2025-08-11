/**
 * Utility functions for handling authenticated image loading
 */
import { apiFetch } from './apiInterceptor';

// Cache for blob URLs to avoid re-fetching images
const imageBlobCache = new Map<string, string>();

// Set to track which images are currently being loaded
const loadingImages = new Set<string>();

/**
 * Get the correct image URL for a given filename
 */
export function getImageUrl(filename: string): string {
  let apiUrl = import.meta.env.VITE_API_URL;
  
  // Auto-detect backend URL in production if VITE_API_URL is not set
  if (!apiUrl && import.meta.env.PROD) {
    const currentHost = window.location.hostname;
    if (currentHost.includes('cookvault-frontend')) {
      // Use your actual backend URL
      apiUrl = 'https://cookvault-exaq.onrender.com/api';
    } else if (currentHost.includes('onrender.com')) {
      // Generic fallback for other Render deployments
      const backendHost = currentHost.replace('frontend', 'backend');
      apiUrl = `https://${backendHost}/api`;
    } else {
      apiUrl = '/api'; // fallback to relative URL
    }
  } else if (!apiUrl) {
    apiUrl = '/api'; // development fallback
  }
  
  const imageUrl = `${apiUrl}/images/${filename}`;
  
  // Debug logging to help diagnose production issues
  console.log('Image URL Debug:', {
    filename,
    VITE_API_URL: import.meta.env.VITE_API_URL,
    hostname: window.location.hostname,
    apiUrl,
    imageUrl,
    isDev: import.meta.env.DEV,
    isProd: import.meta.env.PROD,
    mode: import.meta.env.MODE,
    allEnvVars: import.meta.env
  });
  
  return imageUrl;
}

/**
 * Load an authenticated image and return a blob URL
 */
export async function loadAuthenticatedImage(filename: string): Promise<string> {
  // Check cache first
  if (imageBlobCache.has(filename)) {
    return imageBlobCache.get(filename)!;
  }
  
  // Check if already loading
  if (loadingImages.has(filename)) {
    // Wait for the loading to complete
    return new Promise((resolve) => {
      const checkCache = () => {
        if (imageBlobCache.has(filename)) {
          resolve(imageBlobCache.get(filename)!);
        } else if (loadingImages.has(filename)) {
          setTimeout(checkCache, 100);
        } else {
          // Loading failed, return a default/error state
          resolve('');
        }
      };
      checkCache();
    });
  }
  
  try {
    loadingImages.add(filename);
    
    const imageUrl = getImageUrl(filename);
    const response = await apiFetch(imageUrl);
    
    if (!response.ok) {
      throw new Error(`Failed to load image: ${response.status} ${response.statusText}`);
    }
    
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    
    // Cache the blob URL
    imageBlobCache.set(filename, blobUrl);
    
    return blobUrl;
    
  } catch (error) {
    console.error('Failed to load authenticated image:', filename, error);
    return '';
  } finally {
    loadingImages.delete(filename);
  }
}

/**
 * Clear the image cache (useful for memory management)
 */
export function clearImageCache(): void {
  // Revoke all blob URLs to free memory
  imageBlobCache.forEach((blobUrl) => {
    URL.revokeObjectURL(blobUrl);
  });
  
  imageBlobCache.clear();
  loadingImages.clear();
}

/**
 * Remove a specific image from cache
 */
export function removeImageFromCache(filename: string): void {
  const blobUrl = imageBlobCache.get(filename);
  if (blobUrl) {
    URL.revokeObjectURL(blobUrl);
    imageBlobCache.delete(filename);
  }
}