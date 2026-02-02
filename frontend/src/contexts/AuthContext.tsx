import React, { createContext, useContext, useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { setAuthContext, apiFetch, clearAuthErrors } from '../utils/apiInterceptor';
import { debugAuth, debugCookies } from '../utils/authDebug';
import { getAuthToken, setAuthToken, removeAuthToken } from '../services/storageService';
import { getApiUrl } from '../utils/getApiUrl';

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
  register: (userData: RegisterData) => Promise<RegisterResponse>;
  logout: () => Promise<void>;
  isLoading: boolean;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  verification_method?: 'email' | 'sms';
  phone?: string;
}

export interface RegisterResponse {
  message?: string;
  error?: string;
  requires_verification?: boolean;
  verification_method?: string;
  email?: string;
  phone?: string;
  user?: {
    id: number;
    username: string;
    email: string;
    role: string;
  };
  access_token?: string;
  token_type?: string;
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

        const token = await getAuthToken();
        debugAuth('Auth token status', token ? 'present' : 'missing');

        if (token) {
          // Validate token with backend
          const apiUrl = getApiUrl();
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
            await removeAuthToken();
          }
        }
      } catch (error) {
        debugAuth('Auth check error', error);
        console.error('Auth check failed:', error);
        // Remove invalid token
        await removeAuthToken();
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

      const apiUrl = getApiUrl();
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

      // Store JWT token instead of session token
      await setAuthToken(data.access_token);
      debugAuth('JWT token stored', { tokenType: data.token_type });
      
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

  const register = async (userData: RegisterData): Promise<RegisterResponse> => {
    setIsLoading(true);
    try {
      const apiUrl = getApiUrl();
      const fullUrl = `${apiUrl}/auth/register`;

      const response = await apiFetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      // Check if response has content before trying to parse JSON
      const contentType = response.headers.get('content-type');

      if (!contentType || !contentType.includes('application/json')) {
        throw new Error(`Server returned non-JSON response: ${response.status} ${response.statusText}`);
      }

      const data: RegisterResponse = await response.json();

      if (!response.ok) {
        // Backend returns errors in 'error' field, not 'message'
        throw new Error(data.error || data.message || 'Registration failed');
      }

      // Check if verification is required
      if (data.requires_verification) {
        // Don't set user or token - user needs to verify first
        return data;
      }

      // Legacy path: immediate login (no verification required)
      if (data.access_token && data.user) {
        setUser({
          id: data.user.id.toString(),
          email: data.user.email,
          name: data.user.username,
          role: data.user.role,
          isAdmin: data.user.role === 'admin',
        });

        // Store JWT token from registration response
        await setAuthToken(data.access_token);

        // Clear any authentication error tracking
        clearAuthErrors();

        // Invalidate all queries to ensure fresh data for the new user
        queryClient.invalidateQueries();
      }

      return data;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    debugAuth('Logout initiated');
    setUser(null);
    await removeAuthToken();
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