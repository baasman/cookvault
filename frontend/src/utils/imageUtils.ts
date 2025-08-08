/**
 * Utility functions for handling image URLs
 */

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