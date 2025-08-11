import React, { createContext, useContext, useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { setAuthContext, apiFetch, clearAuthErrors } from '../utils/apiInterceptor';
import { debugAuth, debugCookies } from '../utils/authDebug';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  isAdmin: boolean;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();

  // Register auth context with the API interceptor
  useEffect(() => {
    setAuthContext({ logout });
  }, []);

  useEffect(() => {
    // Check for existing session on mount
    const checkAuth = async () => {
      try {
        debugAuth('Starting auth check');
        debugCookies();
        
        const token = localStorage.getItem('auth_token');
        debugAuth('Auth token status', token ? 'present' : 'missing');
        
        if (token) {
          // Validate token with backend
          const apiUrl = import.meta.env.VITE_API_URL || '/api';
          const response = await apiFetch(`${apiUrl}/auth/me`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          if (response.ok) {
            const data = await response.json();
            debugAuth('Auth check successful', { userId: data.user.id, userRole: data.user.role });
            
            setUser({
              id: data.user.id.toString(),
              email: data.user.email,
              name: data.user.username,
              role: data.user.role,
              isAdmin: data.user.role === 'admin',
            });
            
            // Clear any authentication error tracking on successful auth
            clearAuthErrors();
          } else {
            debugAuth('Auth check failed - invalid token', { status: response.status });
            // Token is invalid, remove it
            localStorage.removeItem('auth_token');
          }
        }
      } catch (error) {
        debugAuth('Auth check error', error);
        console.error('Auth check failed:', error);
        // Remove invalid token
        localStorage.removeItem('auth_token');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (usernameOrEmail: string, password: string) => {
    setIsLoading(true);
    try {
      debugAuth('Login attempt', { login: usernameOrEmail });
      debugCookies();
      
      const apiUrl = import.meta.env.VITE_API_URL || '/api';
      const response = await apiFetch(`${apiUrl}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          login: usernameOrEmail,
          password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        debugAuth('Login failed', { status: response.status, error: data.error });
        // Don't modify auth state on login failures - just throw the error
        // The user remains unauthenticated but we don't trigger logout logic
        throw new Error(data.error || 'Invalid username/email or password');
      }

      debugAuth('Login successful', { userId: data.user.id, userRole: data.user.role });

      setUser({
        id: data.user.id.toString(),
        email: data.user.email,
        name: data.user.username,
        role: data.user.role,
        isAdmin: data.user.role === 'admin',
      });

      localStorage.setItem('auth_token', data.session_token);
      
      // Clear any authentication error tracking
      clearAuthErrors();
      
      // Invalidate all queries to ensure fresh data for the new user
      queryClient.invalidateQueries();
    } catch (error) {
      debugAuth('Login error caught', error);
      // Re-throw the error for the LoginPage to handle
      // Don't modify user state or trigger logout - just let the error bubble up
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: RegisterData) => {
    setIsLoading(true);
    try {
      console.log('Attempting registration with data:', { ...userData, password: '[REDACTED]' });
      
      const apiUrl = import.meta.env.VITE_API_URL || '/api';
      const fullUrl = `${apiUrl}/auth/register`;
      console.log('API URL from env:', import.meta.env.VITE_API_URL);
      console.log('Using API base URL:', apiUrl);
      console.log('Full registration URL:', fullUrl);
      
      const response = await apiFetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      console.log('Registration response status:', response.status);
      console.log('Registration response headers:', Object.fromEntries(response.headers.entries()));

      // Check if response has content before trying to parse JSON
      const contentType = response.headers.get('content-type');
      console.log('Response content-type:', contentType);
      
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.log('Non-JSON response:', text);
        throw new Error(`Server returned non-JSON response: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Registration response data:', { ...data, session_token: data.session_token ? '[PRESENT]' : '[ABSENT]' });

      if (!response.ok) {
        throw new Error(data.error || 'Registration failed');
      }

      setUser({
        id: data.user.id.toString(),
        email: data.user.email,
        name: data.user.username,
        role: data.user.role,
        isAdmin: data.user.role === 'admin',
      });

      localStorage.setItem('auth_token', data.session_token);
      
      // Clear any authentication error tracking
      clearAuthErrors();
      
      // Invalidate all queries to ensure fresh data for the new user
      queryClient.invalidateQueries();
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    debugAuth('Logout initiated');
    setUser(null);
    localStorage.removeItem('auth_token');
    // Clear all React Query cache to prevent data leakage between users
    queryClient.clear();
    // Redirect to login page using window.location for better compatibility
    window.location.href = '/login';
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isAdmin: user?.isAdmin || false,
    login,
    register,
    logout,
    isLoading
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};