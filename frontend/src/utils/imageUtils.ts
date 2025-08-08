/**
 * Utility functions for handling image URLs
 */

/**
 * Get the correct image URL for a given filename
 */
export function getImageUrl(filename: string): string {
  const apiUrl = import.meta.env.VITE_API_URL || '/api';
  return `${apiUrl}/images/${filename}`;
}