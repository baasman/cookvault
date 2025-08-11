import { toast } from 'react-hot-toast';
import { debugAuth } from './authDebug';

interface AuthContext {
  logout: () => void;
}

let authContext: AuthContext | null = null;

// Track failed requests to avoid infinite retries
const failedRequests = new Set<string>();

export const setAuthContext = (context: AuthContext) => {
  authContext = context;
};

/**
 * Generate a unique key for tracking requests
 */
const generateRequestKey = (url: string, options: RequestInit): string => {
  return `${options.method || 'GET'}:${url}:${JSON.stringify(options.body || {})}`;
};

/**
 * Check if error is likely a network issue vs auth issue
 */
const isNetworkError = (error: any): boolean => {
  // Common network error patterns
  return (
    error.name === 'TypeError' ||
    error.message.includes('Failed to fetch') ||
    error.message.includes('Network request failed') ||
    error.message.includes('fetch') ||
    error.message.includes('NetworkError')
  );
};

/**
 * Smart retry logic for failed requests
 */
const shouldRetryRequest = (response: Response, requestKey: string, attempt: number): boolean => {
  // Don't retry more than once
  if (attempt > 1) return false;
  
  // Don't retry if we've already failed this exact request
  if (failedRequests.has(requestKey)) return false;
  
  // Only retry 401s, 500s, 502s, 503s, 504s
  return [401, 500, 502, 503, 504].includes(response.status);
};

/**
 * Enhanced fetch wrapper with smart authentication and retry handling
 */
export const authenticatedFetch = async (
  url: string,
  options: RequestInit = {},
  attempt: number = 1
): Promise<Response> => {
  const requestKey = generateRequestKey(url, options);
  
  try {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // Always include credentials for cross-origin
    });

    // Handle successful responses
    if (response.ok) {
      // Clear any previous failures for this request
      failedRequests.delete(requestKey);
      return response;
    }

    // Handle 401 Unauthorized
    if (response.status === 401) {
      debugAuth('401 Unauthorized received', { url, attempt, requestKey });
      
      // Skip logout logic for login endpoint failures - these are user input errors, not session expiry
      if (url.includes('/auth/login')) {
        debugAuth('Login endpoint failure - not triggering logout', { url });
        return response;
      }
      
      // If this is the first attempt, try once more
      if (shouldRetryRequest(response, requestKey, attempt)) {
        debugAuth('Retrying 401 request', { url, attempt });
        
        // Wait a bit before retry
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Mark this request as having failed once
        failedRequests.add(requestKey);
        
        // Retry the request
        return authenticatedFetch(url, options, attempt + 1);
      }
      
      // If retry didn't work or we've already retried, handle as auth failure
      debugAuth('Authentication failed after retry - handling logout', { url, attempt });
      
      // Show user-friendly message (but only once per session)
      const sessionKey = 'auth_error_shown';
      if (!sessionStorage.getItem(sessionKey)) {
        toast.error('Your session has expired. Please log in again.');
        sessionStorage.setItem(sessionKey, 'true');
      }
      
      // Clear any stored auth tokens
      localStorage.removeItem('auth_token');
      
      // Logout and redirect
      if (authContext) {
        authContext.logout();
      } else {
        window.location.href = '/login';
      }
      
      return response;
    }

    // Handle other server errors with retry
    if (shouldRetryRequest(response, requestKey, attempt)) {
      console.warn(`Server error ${response.status} for ${url}, retrying...`);
      
      // Exponential backoff
      const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
      await new Promise(resolve => setTimeout(resolve, delay));
      
      return authenticatedFetch(url, options, attempt + 1);
    }

    // Handle 403 Forbidden
    if (response.status === 403) {
      toast.error('Access denied');
    }

    return response;
    
  } catch (error: any) {
    console.error('Fetch error:', error);
    
    // Handle network errors
    if (isNetworkError(error)) {
      // Retry network errors once
      if (attempt === 1) {
        console.warn(`Network error for ${url}, retrying...`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        return authenticatedFetch(url, options, attempt + 1);
      } else {
        toast.error('Network connection failed. Please check your internet connection.');
      }
    }
    
    throw error;
  }
};

/**
 * Main API fetch function - use this instead of fetch()
 */
export const apiFetch = authenticatedFetch;

/**
 * Clear failed request tracking (call this on successful auth)
 */
export const clearAuthErrors = (): void => {
  failedRequests.clear();
  sessionStorage.removeItem('auth_error_shown');
};

/**
 * Higher-order function to wrap existing API functions with enhanced error handling
 */
export function withAuthHandling<T extends (...args: any[]) => Promise<any>>(
  apiFunction: T
): T {
  return (async (...args: any[]) => {
    try {
      return await apiFunction(...args);
    } catch (error) {
      // Handle errors that didn't go through our interceptor
      if (error instanceof Error) {
        // Check for authentication error patterns
        if (
          error.message.includes('401') ||
          error.message.includes('Authentication required') ||
          error.message.includes('Unauthorized')
        ) {
          console.warn('Authentication error detected in wrapped API function');
          
          // Don't show toast if we've already shown one
          const sessionKey = 'auth_error_shown';
          if (!sessionStorage.getItem(sessionKey)) {
            toast.error('Your session has expired. Please log in again.');
            sessionStorage.setItem(sessionKey, 'true');
          }
          
          localStorage.removeItem('auth_token');
          
          if (authContext) {
            authContext.logout();
          } else {
            window.location.href = '/login';
          }
        } else if (isNetworkError(error)) {
          toast.error('Network connection failed. Please check your internet connection.');
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
 * Handle authentication error from a response (legacy support)
 */
export const handleAuthError = (response: Response): void => {
  if (isAuthError(response)) {
    console.warn('Legacy auth error handler called');
    
    const sessionKey = 'auth_error_shown';
    if (!sessionStorage.getItem(sessionKey)) {
      toast.error('Your session has expired. Please log in again.');
      sessionStorage.setItem(sessionKey, 'true');
    }
    
    localStorage.removeItem('auth_token');
    
    if (authContext) {
      authContext.logout();
    } else {
      window.location.href = '/login';
    }
  }
};