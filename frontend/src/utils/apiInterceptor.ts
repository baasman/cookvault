import { toast } from 'react-hot-toast';

interface AuthContext {
  logout: () => void;
}

let authContext: AuthContext | null = null;

export const setAuthContext = (context: AuthContext) => {
  authContext = context;
};

/**
 * Custom fetch wrapper that handles authentication errors globally
 */
export const authenticatedFetch = async (
  url: string,
  options: RequestInit = {}
): Promise<Response> => {
  const response = await fetch(url, {
    ...options,
    credentials: 'include', // Always include credentials
  });

  // Check if response indicates authentication failure
  if (response.status === 401) {
    console.warn('Authentication failed - redirecting to login');
    
    // Show user-friendly message
    toast.error('Your session has expired. Please log in again.');
    
    // Clear any stored auth tokens
    localStorage.removeItem('auth_token');
    
    // If auth context is available, use logout to clear state and redirect
    if (authContext) {
      authContext.logout();
    } else {
      // Fallback: redirect directly to login page
      window.location.href = '/login';
    }
    
    // Return the response so the calling code can still handle it if needed
    return response;
  }

  // For other auth-related errors (403, etc.)
  if (response.status === 403) {
    toast.error('Access denied');
  }

  return response;
};

/**
 * Wrapper for fetch with authentication error handling
 * Use this instead of fetch() for all API calls
 */
export const apiFetch = authenticatedFetch;

/**
 * Higher-order function to wrap existing API functions with authentication handling
 */
export function withAuthHandling<T extends (...args: any[]) => Promise<any>>(
  apiFunction: T
): T {
  return (async (...args: any[]) => {
    try {
      return await apiFunction(...args);
    } catch (error) {
      // If it's a fetch error that didn't go through our interceptor,
      // check if it's an authentication error
      if (error instanceof Error) {
        // Check for common authentication error patterns
        if (
          error.message.includes('401') ||
          error.message.includes('Authentication required') ||
          error.message.includes('Unauthorized')
        ) {
          console.warn('Authentication error detected in API function');
          
          toast.error('Your session has expired. Please log in again.');
          localStorage.removeItem('auth_token');
          
          if (authContext) {
            authContext.logout();
          } else {
            window.location.href = '/login';
          }
        }
      }
      throw error;
    }
  }) as T;
}

/**
 * Check if a response indicates an authentication error
 */
export const isAuthError = (response: Response): boolean => {
  return response.status === 401;
};

/**
 * Handle authentication error from a response
 */
export const handleAuthError = (response: Response): void => {
  if (isAuthError(response)) {
    console.warn('Handling authentication error from response');
    
    toast.error('Your session has expired. Please log in again.');
    localStorage.removeItem('auth_token');
    
    if (authContext) {
      authContext.logout();
    } else {
      window.location.href = '/login';
    }
  }
};