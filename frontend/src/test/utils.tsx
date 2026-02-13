import type { ReactElement, ReactNode } from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Create a fresh QueryClient for each test
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })

interface WrapperProps {
  children: ReactNode
}

// Wrapper with all providers
const AllTheProviders = ({ children }: WrapperProps) => {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

// Custom render that includes providers
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options })

// Re-export everything from testing-library
export * from '@testing-library/react'
export { customRender as render }

// Mock API responses
export const mockApiResponse = (data: unknown, status = 200) => {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    headers: new Headers({ 'content-type': 'application/json' }),
  })
}

// Mock user data
export const mockUser = {
  id: '1',
  email: 'test@example.com',
  name: 'testuser',
  role: 'user',
  isAdmin: false,
}

export const mockAdminUser = {
  id: '2',
  email: 'admin@example.com',
  name: 'admin',
  role: 'admin',
  isAdmin: true,
}

// Mock recipe data
export const mockRecipe = {
  id: 1,
  title: 'Test Recipe',
  description: 'A test recipe description',
  prep_time: 15,
  cook_time: 30,
  servings: 4,
  difficulty: 'easy',
  ingredients: [
    { id: 1, name: 'flour', quantity: 2, unit: 'cups' },
    { id: 2, name: 'sugar', quantity: 1, unit: 'cup' },
  ],
  instructions: [
    { id: 1, step_number: 1, text: 'Mix ingredients' },
    { id: 2, step_number: 2, text: 'Bake for 30 minutes' },
  ],
  tags: ['dessert', 'baking'],
  is_public: false,
  user_id: 1,
}

// Mock cookbook data
export const mockCookbook = {
  id: 1,
  title: 'My Cookbook',
  description: 'A collection of recipes',
  author: 'Test Author',
  is_public: false,
  user_id: 1,
  recipes: [],
}
