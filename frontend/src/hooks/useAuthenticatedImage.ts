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

  useEffect(() => {
    if (!filename) {
      setSrc(null);
      setLoading(false);
      setError(false);
      return;
    }

    // Avoid reloading the same image
    if (currentFilename.current === filename && src) {
      return;
    }

    currentFilename.current = filename;
    setLoading(true);
    setError(false);
    setSrc(null);

    loadAuthenticatedImage(filename)
      .then((blobUrl) => {
        if (currentFilename.current === filename) {
          if (blobUrl) {
            setSrc(blobUrl);
            setError(false);
          } else {
            setError(true);
          }
        }
      })
      .catch((err) => {
        console.error('Failed to load authenticated image:', err);
        if (currentFilename.current === filename) {
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
  }, [filename, src]);

  return { src, loading, error };
}