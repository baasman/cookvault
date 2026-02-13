import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../test/utils'
import { LoginPage } from './LoginPage'

// Mock the auth context
const mockLogin = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    login: mockLogin,
    isAuthenticated: false,
    isLoading: false,
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Helper to get the password input (avoid matching "Show password" button)
const getPasswordInput = () => screen.getByPlaceholderText(/enter your password/i)
const getUsernameInput = () => screen.getByPlaceholderText(/enter your username or email/i)

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form', () => {
    render(<LoginPage />)

    expect(screen.getByText('Welcome Back')).toBeInTheDocument()
    expect(getUsernameInput()).toBeInTheDocument()
    expect(getPasswordInput()).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows link to registration page', () => {
    render(<LoginPage />)

    expect(screen.getByText(/don't have an account/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign up/i })).toHaveAttribute(
      'href',
      '/register'
    )
  })

  it('shows link to forgot password page', () => {
    render(<LoginPage />)

    expect(
      screen.getByRole('link', { name: /forgot username or password/i })
    ).toHaveAttribute('href', '/forgot-password')
  })

  it('allows user to enter credentials', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)

    const usernameInput = getUsernameInput()
    const passwordInput = getPasswordInput()

    await user.type(usernameInput, 'testuser')
    await user.type(passwordInput, 'password123')

    expect(usernameInput).toHaveValue('testuser')
    expect(passwordInput).toHaveValue('password123')
  })

  it('calls login on form submission', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValueOnce(undefined)

    render(<LoginPage />)

    await user.type(getUsernameInput(), 'testuser')
    await user.type(getPasswordInput(), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123')
    })
  })

  it('navigates to recipes on successful login', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValueOnce(undefined)

    render(<LoginPage />)

    await user.type(getUsernameInput(), 'testuser')
    await user.type(getPasswordInput(), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/recipes')
    })
  })

  it('displays error message on login failure', async () => {
    const user = userEvent.setup()
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'))

    render(<LoginPage />)

    await user.type(getUsernameInput(), 'testuser')
    await user.type(getPasswordInput(), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  it('disables submit button while submitting', async () => {
    const user = userEvent.setup()
    // Make login hang to test loading state
    mockLogin.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    )

    render(<LoginPage />)

    await user.type(getUsernameInput(), 'testuser')
    await user.type(getPasswordInput(), 'password123')

    const submitButton = screen.getByRole('button', { name: /sign in/i })
    await user.click(submitButton)

    // Button should show loading text
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
  })
})
