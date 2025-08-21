/**
 * Authentication debugging utilities for production troubleshooting
 */

import { getApiUrl } from './getApiUrl';

const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;

/**
 * Log authentication events (only in development or when explicitly enabled)
 */
export const debugAuth = (event: string, data?: any) => {
  // Always log in development
  if (isDevelopment) {
    console.log(`[AUTH DEBUG] ${event}`, data || '');
    return;
  }
  
  // In production, only log if localStorage flag is set
  if (isProduction && localStorage.getItem('debug_auth') === 'true') {
    console.log(`[PROD AUTH DEBUG] ${event}`, data || '');
  }
};

/**
 * Log session cookie information for debugging
 */
export const debugCookies = () => {
  const cookies = document.cookie
    .split(';')
    .map(c => c.trim())
    .filter(c => c.includes('session'))
    .join('; ');
  
  debugAuth('Session cookies', cookies || 'No session cookies found');
  
  // Also check if we're on the right domain
  debugAuth('Current domain', {
    domain: window.location.hostname,
    protocol: window.location.protocol,
    origin: window.location.origin
  });
};

/**
 * Test if we can reach the backend
 */
export const debugBackendConnection = async () => {
  const apiUrl = getApiUrl();
  
  try {
    debugAuth('Testing backend connection', `${apiUrl}/health`);
    
    const response = await fetch(`${apiUrl}/health`, {
      method: 'GET',
      credentials: 'include',
    });
    
    debugAuth('Backend connection result', {
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
    });
    
    if (response.ok) {
      const data = await response.text();
      debugAuth('Backend response', data);
    }
    
  } catch (error) {
    debugAuth('Backend connection error', error);
  }
};

/**
 * Enable production debugging (sets localStorage flag)
 */
export const enableProductionDebug = () => {
  localStorage.setItem('debug_auth', 'true');
  debugAuth('Production debugging enabled');
  debugCookies();
};

/**
 * Disable production debugging
 */
export const disableProductionDebug = () => {
  localStorage.removeItem('debug_auth');
  console.log('[AUTH DEBUG] Production debugging disabled');
};

/**
 * Get comprehensive auth state for debugging
 */
export const getAuthDebugInfo = () => {
  const info = {
    environment: isDevelopment ? 'development' : 'production',
    apiUrl: getApiUrl(),
    authToken: localStorage.getItem('auth_token') ? 'present' : 'missing',
    sessionStorage: Object.keys(sessionStorage).filter(k => k.includes('auth')),
    cookies: document.cookie.split(';').map(c => c.trim()),
    domain: window.location.hostname,
    origin: window.location.origin,
    userAgent: navigator.userAgent,
  };
  
  debugAuth('Auth debug info', info);
  return info;
};

// Export for global access in production debugging
if (typeof window !== 'undefined') {
  (window as any).authDebug = {
    enable: enableProductionDebug,
    disable: disableProductionDebug,
    info: getAuthDebugInfo,
    cookies: debugCookies,
    testBackend: debugBackendConnection,
  };
}