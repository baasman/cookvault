/**
 * Get the correct API URL based on the current environment and domain
 */
export function getApiUrl(): string {
  // First check if VITE_API_URL is explicitly set
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // In production, determine API URL based on domain
  if (import.meta.env.PROD) {
    const currentHost = window.location.hostname;
    
    // Check for custom domain first
    if (currentHost === 'cookle.food' || currentHost === 'www.cookle.food') {
      // Use the backend's custom domain
      return 'https://api.cookle.food/api';
    } else if (currentHost.includes('cookle-frontend')) {
      // Fallback to direct Render URL if using cookle-frontend subdomain
      return 'https://cookle-backend.onrender.com/api';
    } else if (currentHost.includes('cookvault-frontend')) {
      // Handle old cookvault domain
      return 'https://cookvault-exaq.onrender.com/api';
    } else if (currentHost.includes('onrender.com')) {
      // Generic fallback for other Render deployments
      const backendHost = currentHost.replace('frontend', 'backend');
      return `https://${backendHost}/api`;
    }
  }

  // Default to relative URL for development or unknown environments
  return '/api';
}