/**
 * React hook for loading authenticated images
 */
import { useState, useEffect, useRef } from 'react';
import { loadAuthenticatedImage } from '../utils/imageUtils';

interface UseAuthenticatedImageResult {
  src: string | null;
  loading: boolean;
  error: boolean;
}

/**
 * Hook to load an authenticated image with loading states
 */
export function useAuthenticatedImage(filename: string | null): UseAuthenticatedImageResult {
  const [src, setSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const currentFilename = useRef<string | null>(null);
  const prevSrc = useRef<string | null>(null);

  useEffect(() => {
    if (!filename) {
      setSrc(null);
      setLoading(false);
      setError(false);
      prevSrc.current = null;
      return;
    }

    // Avoid reloading the same image
    if (currentFilename.current === filename && src) {
      return;
    }

    currentFilename.current = filename;
    setLoading(true);
    setError(false);
    // Don't clear src immediately - keep showing old image while loading new one
    // This prevents the flicker

    loadAuthenticatedImage(filename)
      .then((blobUrl) => {
        if (currentFilename.current === filename) {
          if (blobUrl) {
            // Revoke the previous blob URL to free memory
            if (prevSrc.current && prevSrc.current !== blobUrl) {
              URL.revokeObjectURL(prevSrc.current);
            }
            setSrc(blobUrl);
            prevSrc.current = blobUrl;
            setError(false);
          } else {
            setSrc(null);
            setError(true);
          }
        }
      })
      .catch((err) => {
        console.error('Failed to load authenticated image:', err);
        if (currentFilename.current === filename) {
          setSrc(null);
          setError(true);
        }
      })
      .finally(() => {
        if (currentFilename.current === filename) {
          setLoading(false);
        }
      });

    // Cleanup function to handle component unmount or filename change
    return () => {
      if (currentFilename.current === filename) {
        currentFilename.current = null;
      }
    };
  }, [filename]); // Remove 'src' from dependencies to prevent re-fetching

  return { src, loading, error };
}