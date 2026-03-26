import type { ReactElement, ReactNode } from 'react'
import React from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
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

// Render with MemoryRouter for testing specific routes
interface MemoryRouterRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[]
}

const renderWithMemoryRouter = (
  ui: ReactElement,
  { initialEntries = ['/'], ...options }: MemoryRouterRenderOptions = {}
) => {
  const queryClient = createTestQueryClient()

  const Wrapper = ({ children }: WrapperProps) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  )

  return render(ui, { wrapper: Wrapper, ...options })
}

// Re-export everything from testing-library
export * from '@testing-library/react'
export { customRender as render, renderWithMemoryRouter }

// Mock API responses
export const mockApiResponse = (data: unknown, status = 200) => {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    headers: new Headers({ 'content-type': 'application/json' }),
  })
}

// ============================================
// Mock User Data
// ============================================

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

export const mockUserInfo = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  bio: 'A test user',
  avatar_url: null,
  role: 'user',
  status: 'active',
  is_verified: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  last_login: '2024-01-01T12:00:00Z',
}

// ============================================
// Mock Recipe Data
// ============================================

export const mockIngredient = {
  id: 1,
  name: 'flour',
  quantity: 2,
  unit: 'cups',
  preparation: 'sifted',
  optional: false,
  order: 1,
}

export const mockInstruction = {
  id: 1,
  step_number: 1,
  text: 'Mix ingredients',
  original_text: null,
  image_filename: null,
  image_url: null,
}

export const mockTag = {
  id: 1,
  name: 'dessert',
}

export const mockRecipeImage = {
  id: 1,
  filename: 'recipe-1.jpg',
  original_filename: 'my-recipe.jpg',
  file_size: 1024000,
  content_type: 'image/jpeg',
  uploaded_at: '2024-01-01T00:00:00Z',
  image_order: 1,
  display_url: 'https://example.com/images/recipe-1.jpg',
}

export const mockRecipe = {
  id: 1,
  title: 'Test Recipe',
  description: 'A test recipe description',
  prep_time: 15,
  cook_time: 30,
  servings: 4,
  difficulty: 'easy',
  course_type: 'Main Course',
  source: null,
  user_id: 1,
  is_public: false,
  is_featured: false,
  ingredients: [
    { id: 1, name: 'flour', quantity: 2, unit: 'cups', optional: false, order: 1 },
    { id: 2, name: 'sugar', quantity: 1, unit: 'cup', optional: false, order: 2 },
  ],
  instructions: [
    { id: 1, step_number: 1, text: 'Mix ingredients' },
    { id: 2, step_number: 2, text: 'Bake for 30 minutes' },
  ],
  tags: [{ id: 1, name: 'dessert' }, { id: 2, name: 'baking' }],
  images: [],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  user: {
    id: 1,
    username: 'testuser',
    first_name: 'Test',
    last_name: 'User',
  },
}

export const mockPublicRecipe = {
  ...mockRecipe,
  is_public: true,
  published_at: '2024-01-02T00:00:00Z',
}

export const mockFeaturedRecipe = {
  ...mockPublicRecipe,
  is_featured: true,
  featured_at: '2024-01-03T00:00:00Z',
}

// ============================================
// Mock Cookbook Data
// ============================================

export const mockCookbook = {
  id: 1,
  title: 'My Cookbook',
  description: 'A collection of recipes',
  author: 'Test Author',
  publisher: 'Test Publisher',
  isbn: '978-3-16-148410-0',
  publication_date: '2024-01-01',
  cover_image_url: null,
  recipe_count: 5,
  user_id: 1,
  is_public: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  user: {
    id: 1,
    username: 'testuser',
    first_name: 'Test',
    last_name: 'User',
  },
  recipes: [],
}

export const mockPurchasableCookbook = {
  ...mockCookbook,
  id: 2,
  title: 'Premium Cookbook',
  is_purchasable: true,
  price: 9.99,
  purchase_count: 100,
  has_purchased: false,
  is_available_for_purchase: true,
}

// ============================================
// Mock Processing Job Data
// ============================================

export const mockProcessingJob = {
  id: 1,
  status: 'completed' as const,
  error_message: undefined,
  recipe_id: 1,
  created_at: '2024-01-01T00:00:00Z',
  completed_at: '2024-01-01T00:00:01Z',
  is_multi_image: false,
  multi_job_id: undefined,
  image_order: 1,
  ocr_text: 'Recipe text extracted from image',
  ocr_confidence: 0.95,
  ocr_method: 'tesseract',
}

export const mockPendingJob = {
  ...mockProcessingJob,
  id: 2,
  status: 'pending' as const,
  completed_at: undefined,
  recipe_id: undefined,
}

export const mockFailedJob = {
  ...mockProcessingJob,
  id: 3,
  status: 'failed' as const,
  error_message: 'Failed to process image',
  recipe_id: undefined,
}

export const mockMultiRecipeJob = {
  id: 1,
  user_id: 1,
  status: 'completed' as const,
  total_images: 3,
  processed_images: 3,
  recipe_id: 1,
  combined_ocr_text: 'Combined text from all images',
  error_message: undefined,
  created_at: '2024-01-01T00:00:00Z',
  completed_at: '2024-01-01T00:00:05Z',
  processing_jobs: [mockProcessingJob],
}

// ============================================
// Mock Comment & Rating Data
// ============================================

export const mockComment = {
  id: 1,
  recipe_id: 1,
  user_id: 1,
  content: 'Great recipe! Made it for dinner.',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  user: {
    id: 1,
    username: 'testuser',
    first_name: 'Test',
    last_name: 'User',
  },
}

export const mockRating = {
  id: 1,
  user_id: 1,
  recipe_id: 1,
  rating: 5,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockAggregateRating = {
  average_rating: 4.5,
  rating_count: 10,
  normalized_title: 'test-recipe',
  cookbook_id: null,
  canonical_source_url: null,
  matching_recipe_count: 1,
}

export const mockRatingResponse = {
  aggregate: mockAggregateRating,
  user_rating: mockRating,
}

// ============================================
// Mock Note Data
// ============================================

export const mockRecipeNote = {
  id: 1,
  user_id: 1,
  recipe_id: 1,
  content: 'My personal notes about this recipe',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

// ============================================
// Mock Subscription/Payment Data
// ============================================

export const mockSubscription = {
  id: 'sub_123',
  status: 'active' as const,
  plan: 'premium',
  current_period_start: '2024-01-01T00:00:00Z',
  current_period_end: '2024-02-01T00:00:00Z',
  cancel_at_period_end: false,
}

export const mockPaymentMethod = {
  id: 'pm_123',
  type: 'card',
  card: {
    brand: 'visa',
    last4: '4242',
    exp_month: 12,
    exp_year: 2025,
  },
}

// ============================================
// Mock User Profile Data
// ============================================

export const mockUserStatistics = {
  total_recipes: 10,
  total_cookbooks: 2,
  difficulty_breakdown: {
    easy: 5,
    medium: 3,
    hard: 2,
    unspecified: 0,
  },
  avg_cook_time_minutes: 30,
  avg_recipes_per_cookbook: 5,
  most_popular_cookbook: {
    id: 1,
    title: 'My Cookbook',
    recipe_count: 5,
  },
  cookbooks_with_recipes: 2,
  empty_cookbooks: 0,
}

export const mockUserProfile = {
  user: mockUserInfo,
  statistics: mockUserStatistics,
  recent_activity: [
    {
      type: 'recipe' as const,
      id: 1,
      title: 'Test Recipe',
      created_at: '2024-01-01T00:00:00Z',
      cookbook_title: 'My Cookbook',
    },
  ],
}

// ============================================
// Mock Video Processing Data
// ============================================

export const mockVideoProcessingJob = {
  id: 1,
  user_id: 1,
  video_filename: 'video-123.mp4',
  video_original_filename: 'cooking-video.mp4',
  video_size_bytes: 50000000,
  video_duration_seconds: 300,
  youtube_url: undefined,
  youtube_video_id: undefined,
  extraction_method: 'transcription',
  status: 'completed' as const,
  progress_message: 'Processing complete',
  progress_percentage: 100,
  recipe_id: 1,
  error_message: undefined,
  cookbook_id: undefined,
  created_at: '2024-01-01T00:00:00Z',
  started_at: '2024-01-01T00:00:01Z',
  completed_at: '2024-01-01T00:05:00Z',
}

export const mockYouTubeProcessingJob = {
  ...mockVideoProcessingJob,
  id: 2,
  video_filename: '',
  video_original_filename: '',
  video_size_bytes: 0,
  youtube_url: 'https://www.youtube.com/watch?v=abc123',
  youtube_video_id: 'abc123',
  extraction_method: 'captions',
}

// ============================================
// Mock Source Data
// ============================================

export const mockSource = {
  id: 1,
  domain: 'example.com',
  name: 'Example Recipes',
  display_name: 'Example Recipes',
  favicon_url: 'https://example.com/favicon.ico',
  recipe_count: 5,
  user_id: 1,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

// ============================================
// Auth Context Testing Helpers
// ============================================

interface MockAuthContextValue {
  user: typeof mockUser | null
  isAuthenticated: boolean
  isAdmin: boolean
  login: (usernameOrEmail: string, password: string) => Promise<void>
  register: (userData: any) => Promise<any>
  logout: () => Promise<void>
  isLoading: boolean
}

export const createMockAuthContext = (
  overrides: Partial<MockAuthContextValue> = {}
): MockAuthContextValue => ({
  user: mockUser,
  isAuthenticated: true,
  isAdmin: false,
  login: async () => {},
  register: async () => ({ message: 'Registered' }),
  logout: async () => {},
  isLoading: false,
  ...overrides,
})

export const createUnauthenticatedAuthContext = (): MockAuthContextValue =>
  createMockAuthContext({
    user: null,
    isAuthenticated: false,
  })

export const createAdminAuthContext = (): MockAuthContextValue =>
  createMockAuthContext({
    user: mockAdminUser,
    isAdmin: true,
  })

export const createLoadingAuthContext = (): MockAuthContextValue =>
  createMockAuthContext({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  })

// ============================================
// API Response Helpers
// ============================================

export const createRecipesResponse = (recipes = [mockRecipe], total = 1) => ({
  recipes,
  total,
  pages: Math.ceil(total / 12),
  current_page: 1,
})

export const createCookbooksResponse = (cookbooks = [mockCookbook], total = 1) => ({
  cookbooks,
  total,
  pages: Math.ceil(total / 12),
  current_page: 1,
})

export const createCommentsResponse = (comments = [mockComment], total = 1) => ({
  comments,
  total,
  pages: 1,
  current_page: 1,
  per_page: 20,
  has_next: false,
  has_prev: false,
})

// ============================================
// Form Data Helpers
// ============================================

export const createMockUploadFormData = (overrides = {}) => ({
  image: null,
  images: [],
  isMultiImage: false,
  isTextMode: false,
  recipeText: '',
  isUrlMode: false,
  recipeUrl: '',
  isVideoMode: false,
  videoFile: null,
  isYoutubeLink: false,
  youtubeUrl: '',
  cookbook_id: undefined,
  no_cookbook: true,
  create_new_cookbook: false,
  new_cookbook_title: '',
  search_existing_cookbook: false,
  selected_existing_cookbook_id: undefined,
  is_original_recipe: true,
  translate_to_english: false,
  ...overrides,
})

// ============================================
// Test File Creation Helper
// ============================================

export const createMockFile = (
  name = 'test.jpg',
  type = 'image/jpeg',
  size = 1024
): File => {
  const content = new Array(size).fill('a').join('')
  const blob = new Blob([content], { type })
  return new File([blob], name, { type })
}

export const createMockImageFile = (name = 'recipe.jpg'): File =>
  createMockFile(name, 'image/jpeg', 1024000)

export const createMockVideoFile = (name = 'recipe.mp4'): File =>
  createMockFile(name, 'video/mp4', 50000000)
