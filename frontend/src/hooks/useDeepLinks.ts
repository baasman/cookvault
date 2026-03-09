import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { App } from '@capacitor/app';
import type { URLOpenListenerEvent } from '@capacitor/app';
import { isNativePlatform } from '../utils/platform';

/**
 * Parse a deep link URL and return the corresponding app route.
 *
 * Supports:
 * - Custom scheme: cookle://recipe/123 -> /recipes/123
 * - Universal links: https://cookvault-frontend.onrender.com/recipes/123 -> /recipes/123
 * - Universal links: https://cookle.app/recipes/123 -> /recipes/123
 */
function parseDeepLink(url: string): string | null {
  try {
    const urlObj = new URL(url);

    // Handle custom URL scheme (cookle://)
    if (urlObj.protocol === 'cookle:') {
      const path = urlObj.pathname || urlObj.hostname;

      // cookle://recipe/123 -> /recipes/123
      if (path.startsWith('recipe/') || path.startsWith('/recipe/')) {
        const id = path.replace(/^\/?recipe\//, '');
        return `/recipes/${id}`;
      }

      // cookle://cookbook/123 -> /cookbooks/123
      if (path.startsWith('cookbook/') || path.startsWith('/cookbook/')) {
        const id = path.replace(/^\/?cookbook\//, '');
        return `/cookbooks/${id}`;
      }

      // cookle://upload -> /upload
      if (path === 'upload' || path === '/upload') {
        return '/upload';
      }

      // cookle://user/123 -> /users/123
      if (path.startsWith('user/') || path.startsWith('/user/')) {
        const id = path.replace(/^\/?user\//, '');
        return `/users/${id}`;
      }

      // cookle://recipes -> /recipes
      if (path === 'recipes' || path === '/recipes') {
        return '/recipes';
      }

      // cookle://cookbooks -> /cookbooks
      if (path === 'cookbooks' || path === '/cookbooks') {
        return '/cookbooks';
      }

      // Default: try to use the path directly
      return path.startsWith('/') ? path : `/${path}`;
    }

    // Handle Universal Links (https://)
    if (urlObj.protocol === 'https:' || urlObj.protocol === 'http:') {
      // Check if it's our domain
      const validDomains = [
        'cookvault-frontend.onrender.com',
        'cookle.app',
        'www.cookle.app',
      ];

      if (validDomains.includes(urlObj.hostname)) {
        // Return the pathname as the route
        return urlObj.pathname + urlObj.search;
      }
    }

    return null;
  } catch (error) {
    console.error('Error parsing deep link:', error);
    return null;
  }
}

/**
 * Hook to handle deep links in the app.
 * Must be used within a Router context.
 */
export function useDeepLinks(): void {
  const navigate = useNavigate();

  useEffect(() => {
    // Only set up deep link handling on native platforms
    if (!isNativePlatform()) {
      return;
    }

    // Handle URLs that open the app
    const handleUrlOpen = (event: URLOpenListenerEvent) => {
      console.log('Deep link received:', event.url);

      const route = parseDeepLink(event.url);
      if (route) {
        console.log('Navigating to:', route);
        navigate(route);
      }
    };

    // Listen for app URL open events
    const listener = App.addListener('appUrlOpen', handleUrlOpen);

    // Check if app was opened with a URL (cold start)
    App.getLaunchUrl().then((result) => {
      if (result?.url) {
        console.log('App launched with URL:', result.url);
        const route = parseDeepLink(result.url);
        if (route) {
          console.log('Navigating to launch URL route:', route);
          navigate(route);
        }
      }
    });

    return () => {
      listener.then((l) => l.remove());
    };
  }, [navigate]);
}

/**
 * Generate a deep link URL for sharing.
 */
export function generateDeepLink(type: 'recipe' | 'cookbook' | 'user', id: string | number): string {
  // For sharing, use the web URL (Universal Link format)
  // This works whether the recipient has the app installed or not
  const baseUrl = 'https://cookvault-frontend.onrender.com';

  switch (type) {
    case 'recipe':
      return `${baseUrl}/recipes/${id}`;
    case 'cookbook':
      return `${baseUrl}/cookbooks/${id}`;
    case 'user':
      return `${baseUrl}/users/${id}`;
    default:
      return baseUrl;
  }
}

/**
 * Generate a custom scheme deep link (for app-to-app communication).
 */
export function generateAppLink(type: 'recipe' | 'cookbook' | 'user' | 'upload', id?: string | number): string {
  switch (type) {
    case 'recipe':
      return `cookle://recipe/${id}`;
    case 'cookbook':
      return `cookle://cookbook/${id}`;
    case 'user':
      return `cookle://user/${id}`;
    case 'upload':
      return 'cookle://upload';
    default:
      return 'cookle://';
  }
}
