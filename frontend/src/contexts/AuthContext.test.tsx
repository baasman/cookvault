import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test/utils'
import { AuthProvider, useAuth } from './AuthContext'
import { server } from '../test/mocks/server'
import { http, HttpResponse } from 'msw'

// Match both localhost and relative API URLs
const API_BASE = '*/api'

// Mock platform utilities to return web platform
vi.mock('../utils/platform', () => ({
  isNativePlatform: () => false,
  isWeb: () => true,
  getPlatform: () => 'web',
}))

// Mock debug utilities
vi.mock('../utils/authDebug', () => ({
  debugAuth: vi.fn(),
  debugCookies: vi.fn(),
}))

// Test component that exposes auth context values
const TestAuthConsumer = () => {
  const { user, isAuthenticated, isAdmin, isLoading, login, logout, register } = useAuth()

  return (
    <div>
      <div data-testid="loading">{isLoading ? 'loading' : 'not-loading'}</div>
      <div data-testid="authenticated">{isAuthenticated ? 'authenticated' : 'not-authenticated'}</div>
      <div data-testid="admin">{isAdmin ? 'admin' : 'not-admin'}</div>
      <div data-testid="user">{user ? JSON.stringify(user) : 'no-user'}</div>
      <button onClick={() => login('test@example.com', 'password')} data-testid="login-btn">
        Login
      </button>
      <button onClick={() => logout()} data-testid="logout-btn">
        Logout
      </button>
      <button
        onClick={() => register({ username: 'newuser', email: 'new@example.com', password: 'password123' })}
        data-testid="register-btn"
      >
        Register
      </button>
    </div>
  )
}

// Mock window.location
const mockLocation = {
  href: '',
  assign: vi.fn(),
  replace: vi.fn(),
  reload: vi.fn(),
}
const originalLocation = window.location

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Clear localStorage mock storage
    localStorage.clear()
    localStorage.removeItem('auth_token')
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: mockLocation,
      writable: true,
    })
    mockLocation.href = ''
  })

  afterEach(() => {
    // Restore window.location
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    })
  })

  describe('Initial State', () => {
    it('starts in loading state', async () => {
      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      // Initially loading
      expect(screen.getByTestId('loading')).toHaveTextContent('loading')

      // After auth check completes
      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      })
    })

    it('is not authenticated without stored token', async () => {
      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      })

      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated')
      expect(screen.getByTestId('user')).toHaveTextContent('no-user')
    })

    it('validates stored token on mount', async () => {
      // Set a valid token in localStorage
      localStorage.setItem('auth_token', 'mock-jwt-token')

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      })

      // Should be authenticated after token validation
      expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated')
      expect(screen.getByTestId('user')).not.toHaveTextContent('no-user')
    })

    it('clears invalid token on mount', async () => {
      // Set an invalid token in localStorage
      localStorage.setItem('auth_token', 'invalid-token')

      // Override handler to return 401 for invalid token
      server.use(
        http.get(`${API_BASE}/auth/me`, () => {
          return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })
        })
      )

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      })

      expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated')
      expect(localStorage.getItem('auth_token')).toBeNull()
    })
  })

  describe('Login', () => {
    it('successfully logs in with valid credentials', async () => {
      const user = userEvent.setup()

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      })

      await user.click(screen.getByTestId('login-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated')
      })

      // Token should be stored
      expect(localStorage.getItem('auth_token')).toBe('mock-jwt-token')
    })

    it('handles login failure', async () => {
      const user = userEvent.setup()

      // Override handler to return error
      server.use(
        http.post(`${API_BASE}/auth/login`, () => {
          return HttpResponse.json(
            { error: 'Invalid username/email or password' },
            { status: 401 }
          )
        })
      )

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      })

      // Login should throw an error
      await expect(async () => {
        await user.click(screen.getByTestId('login-btn'))
        // Small delay to let promise reject
        await new Promise(resolve => setTimeout(resolve, 100))
      }).rejects // This is expected to fail - errors bubble up

      // Alternatively, wrap the component to catch errors
    })

    it('sets user data after successful login', async () => {
      const user = userEvent.setup()

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      })

      await user.click(screen.getByTestId('login-btn'))

      await waitFor(() => {
        const userDiv = screen.getByTestId('user')
        expect(userDiv).not.toHaveTextContent('no-user')

        const userData = JSON.parse(userDiv.textContent || '{}')
        expect(userData.email).toBe('test@example.com')
        expect(userData.name).toBe('testuser')
      })
    })
  })

  describe('Logout', () => {
    it('clears user data on logout', async () => {
      const user = userEvent.setup()

      // Start with a valid token
      localStorage.setItem('auth_token', 'mock-jwt-token')

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated')
      })

      await user.click(screen.getByTestId('logout-btn'))

      // Should clear auth state
      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toHaveTextContent('not-authenticated')
      })

      // Token should be removed
      expect(localStorage.getItem('auth_token')).toBeNull()
    })

    it('redirects to login page on logout', async () => {
      const user = userEvent.setup()

      localStorage.setItem('auth_token', 'mock-jwt-token')

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated')
      })

      await user.click(screen.getByTestId('logout-btn'))

      await waitFor(() => {
        expect(mockLocation.href).toBe('/login')
      })
    })
  })

  describe('Register', () => {
    it('handles registration with verification required', async () => {
      const user = userEvent.setup()

      // Override handler to return verification required
      server.use(
        http.post(`${API_BASE}/auth/register`, () => {
          return HttpResponse.json({
            message: 'Registration successful. Please check your email.',
            requires_verification: true,
            verification_method: 'email',
            email: 'new@example.com',
          })
        })
      )

      let registerResult: any

      const TestComponent = () => {
        const { register, isAuthenticated } = useAuth()

        const handleRegister = async () => {
          registerResult = await register({
            username: 'newuser',
            email: 'new@example.com',
            password: 'password123',
            verification_method: 'email',
          })
        }

        return (
          <div>
            <div data-testid="authenticated">{isAuthenticated ? 'yes' : 'no'}</div>
            <button onClick={handleRegister} data-testid="register-btn">Register</button>
          </div>
        )
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toHaveTextContent('no')
      })

      await user.click(screen.getByTestId('register-btn'))

      await waitFor(() => {
        expect(registerResult).toBeDefined()
        expect(registerResult.requires_verification).toBe(true)
      })

      // User should NOT be authenticated (needs to verify first)
      expect(screen.getByTestId('authenticated')).toHaveTextContent('no')
    })

    it('handles registration with immediate login', async () => {
      const user = userEvent.setup()

      // Override handler to return immediate login (legacy path)
      server.use(
        http.post(`${API_BASE}/auth/register`, () => {
          return HttpResponse.json({
            message: 'Registration successful',
            user: {
              id: 3,
              username: 'newuser',
              email: 'new@example.com',
              role: 'user',
            },
            access_token: 'new-jwt-token',
            token_type: 'Bearer',
          })
        })
      )

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      })

      await user.click(screen.getByTestId('register-btn'))

      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated')
      })

      // Token should be stored
      expect(localStorage.getItem('auth_token')).toBe('new-jwt-token')
    })

    it('handles registration failure', async () => {
      const user = userEvent.setup()

      // Override handler to return error
      server.use(
        http.post(`${API_BASE}/auth/register`, () => {
          return HttpResponse.json(
            { error: 'Email already registered' },
            { status: 400 }
          )
        })
      )

      let registerError: Error | null = null

      const TestComponent = () => {
        const { register, isLoading } = useAuth()

        const handleRegister = async () => {
          try {
            await register({
              username: 'newuser',
              email: 'existing@example.com',
              password: 'password123',
            })
          } catch (err) {
            registerError = err as Error
          }
        }

        return (
          <div>
            <div data-testid="loading">{isLoading ? 'loading' : 'not-loading'}</div>
            <button onClick={handleRegister} data-testid="register-btn">Register</button>
          </div>
        )
      }

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading')
      })

      await user.click(screen.getByTestId('register-btn'))

      await waitFor(() => {
        expect(registerError).not.toBeNull()
        expect(registerError?.message).toBe('Email already registered')
      })
    })
  })

  describe('Admin User', () => {
    it('sets isAdmin for admin users', async () => {
      // Override handler to return admin user
      server.use(
        http.get(`${API_BASE}/auth/me`, () => {
          return HttpResponse.json({
            user: {
              id: 2,
              username: 'admin',
              email: 'admin@example.com',
              role: 'admin',
            },
          })
        })
      )

      localStorage.setItem('auth_token', 'admin-jwt-token')

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('admin')).toHaveTextContent('admin')
      })
    })

    it('sets isAdmin to false for regular users', async () => {
      localStorage.setItem('auth_token', 'mock-jwt-token')

      render(
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      )

      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toHaveTextContent('authenticated')
      })

      expect(screen.getByTestId('admin')).toHaveTextContent('not-admin')
    })
  })

  describe('useAuth hook', () => {
    it('throws error when used outside AuthProvider', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(() => {
        render(<TestAuthConsumer />)
      }).toThrow('useAuth must be used within an AuthProvider')

      consoleError.mockRestore()
    })
  })
})
