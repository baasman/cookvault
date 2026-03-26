import { http, HttpResponse } from 'msw'

// Match both localhost and relative API URLs
// MSW uses path patterns that can match URLs
const API_BASE = '*/api'

// Mock data
export const mockUser = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  role: 'user',
  first_name: 'Test',
  last_name: 'User',
}

export const mockAdminUser = {
  id: 2,
  username: 'admin',
  email: 'admin@example.com',
  role: 'admin',
  first_name: 'Admin',
  last_name: 'User',
}

export const mockRecipe = {
  id: 1,
  title: 'Test Recipe',
  description: 'A delicious test recipe',
  prep_time: 15,
  cook_time: 30,
  servings: 4,
  difficulty: 'easy',
  is_public: false,
  is_featured: false,
  user_id: 1,
  ingredients: [
    { id: 1, name: 'flour', quantity: 2, unit: 'cups', optional: false, order: 1 },
    { id: 2, name: 'sugar', quantity: 1, unit: 'cup', optional: false, order: 2 },
  ],
  instructions: [
    { id: 1, step_number: 1, text: 'Mix the dry ingredients' },
    { id: 2, step_number: 2, text: 'Bake at 350F for 30 minutes' },
  ],
  tags: [{ id: 1, name: 'dessert' }, { id: 2, name: 'baking' }],
  images: [],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  user: mockUser,
}

export const mockCookbook = {
  id: 1,
  title: 'My Cookbook',
  description: 'A collection of family recipes',
  author: 'Test User',
  recipe_count: 5,
  user_id: 1,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

export const mockComment = {
  id: 1,
  recipe_id: 1,
  user_id: 1,
  content: 'Great recipe!',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  user: mockUser,
}

export const mockRating = {
  aggregate: {
    average_rating: 4.5,
    rating_count: 10,
    normalized_title: 'test-recipe',
    cookbook_id: null,
    canonical_source_url: null,
    matching_recipe_count: 1,
  },
  user_rating: {
    id: 1,
    user_id: 1,
    recipe_id: 1,
    rating: 5,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
}

export const mockProcessingJob = {
  id: 1,
  status: 'completed' as const,
  recipe_id: 1,
  created_at: '2024-01-01T00:00:00Z',
  completed_at: '2024-01-01T00:00:01Z',
}

// API handlers
export const handlers = [
  // Auth endpoints
  http.post(`${API_BASE}/auth/login`, async ({ request }) => {
    const body = await request.json() as { login: string; password: string }

    if (body.login === 'test@example.com' && body.password === 'password') {
      return HttpResponse.json({
        user: mockUser,
        access_token: 'mock-jwt-token',
        token_type: 'Bearer',
      })
    }

    return HttpResponse.json(
      { error: 'Invalid username/email or password' },
      { status: 401 }
    )
  }),

  http.post(`${API_BASE}/auth/register`, async ({ request }) => {
    const body = await request.json() as {
      username: string
      email: string
      password: string
      verification_method?: string
    }

    if (body.email === 'existing@example.com') {
      return HttpResponse.json(
        { error: 'Email already registered' },
        { status: 400 }
      )
    }

    if (body.username === 'existinguser') {
      return HttpResponse.json(
        { error: 'Username already taken' },
        { status: 400 }
      )
    }

    // Return verification required response
    if (body.verification_method === 'email') {
      return HttpResponse.json({
        message: 'Registration successful. Please check your email to verify your account.',
        requires_verification: true,
        verification_method: 'email',
        email: body.email,
      })
    }

    // Return immediate login response (legacy path)
    return HttpResponse.json({
      message: 'Registration successful',
      user: {
        id: 3,
        username: body.username,
        email: body.email,
        role: 'user',
      },
      access_token: 'mock-jwt-token',
      token_type: 'Bearer',
    })
  }),

  http.get(`${API_BASE}/auth/me`, ({ request }) => {
    const authHeader = request.headers.get('Authorization')

    if (authHeader === 'Bearer mock-jwt-token') {
      return HttpResponse.json({ user: mockUser })
    }

    return HttpResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    )
  }),

  http.post(`${API_BASE}/auth/logout`, () => {
    return HttpResponse.json({ message: 'Logged out successfully' })
  }),

  // Features endpoint
  http.get(`${API_BASE}/features`, () => {
    return HttpResponse.json({ youtube_import_enabled: false })
  }),

  // Recipes endpoints
  http.get(`${API_BASE}/recipes`, ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const perPage = parseInt(url.searchParams.get('per_page') || '12')

    return HttpResponse.json({
      recipes: [mockRecipe],
      total: 1,
      pages: 1,
      current_page: page,
    })
  }),

  http.get(`${API_BASE}/recipes/:id`, ({ params }) => {
    const id = params.id

    if (id === '999') {
      return HttpResponse.json(
        { error: 'Recipe not found' },
        { status: 404 }
      )
    }

    return HttpResponse.json({ ...mockRecipe, id: Number(id) })
  }),

  http.post(`${API_BASE}/recipes`, async ({ request }) => {
    const body = await request.json() as { title: string }

    return HttpResponse.json({
      message: 'Recipe created',
      recipe: { ...mockRecipe, title: body.title, id: 2 },
    })
  }),

  http.put(`${API_BASE}/recipes/:id`, async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>

    return HttpResponse.json({
      message: 'Recipe updated',
      recipe: { ...mockRecipe, ...body, id: Number(params.id) },
    })
  }),

  http.delete(`${API_BASE}/recipes/:id`, ({ params }) => {
    return HttpResponse.json({ message: 'Recipe deleted' })
  }),

  // Recipe upload endpoints
  http.post(`${API_BASE}/recipes/upload-multi`, async () => {
    return HttpResponse.json({
      multi_job_id: 1,
      total_images: 1,
      message: 'Upload started',
    })
  }),

  http.post(`${API_BASE}/recipes/upload-text`, async () => {
    return HttpResponse.json({
      job_id: 1,
      message: 'Processing started',
    })
  }),

  http.post(`${API_BASE}/recipes/upload-url`, async () => {
    return HttpResponse.json({
      job_id: 1,
      message: 'Processing started',
    })
  }),

  http.get(`${API_BASE}/recipes/job-status/:id`, ({ params }) => {
    return HttpResponse.json({
      ...mockProcessingJob,
      id: Number(params.id),
      recipe: mockRecipe,
    })
  }),

  http.get(`${API_BASE}/recipes/multi-job-status/:id`, ({ params }) => {
    return HttpResponse.json({
      id: Number(params.id),
      status: 'completed',
      total_images: 1,
      processed_images: 1,
      recipe_id: 1,
      recipe: mockRecipe,
    })
  }),

  // Comments endpoints
  http.get(`${API_BASE}/recipes/:id/comments`, () => {
    return HttpResponse.json({
      comments: [mockComment],
      total: 1,
      pages: 1,
      current_page: 1,
      per_page: 20,
      has_next: false,
      has_prev: false,
    })
  }),

  http.post(`${API_BASE}/recipes/:id/comments`, async ({ request }) => {
    const body = await request.json() as { content: string }

    return HttpResponse.json({
      comment: { ...mockComment, content: body.content, id: 2 },
    })
  }),

  // Rating endpoints
  http.get(`${API_BASE}/recipes/:id/rating`, () => {
    return HttpResponse.json(mockRating)
  }),

  http.post(`${API_BASE}/recipes/:id/rating`, async ({ request }) => {
    const body = await request.json() as { rating: number }

    return HttpResponse.json({
      ...mockRating,
      user_rating: { ...mockRating.user_rating, rating: body.rating },
    })
  }),

  // Cookbooks endpoints
  http.get(`${API_BASE}/cookbooks`, () => {
    return HttpResponse.json({
      cookbooks: [mockCookbook],
      total: 1,
      pages: 1,
      current_page: 1,
    })
  }),

  http.get(`${API_BASE}/cookbooks/:id`, ({ params }) => {
    return HttpResponse.json({ ...mockCookbook, id: Number(params.id) })
  }),

  // User profile endpoints
  http.get(`${API_BASE}/user/profile`, () => {
    return HttpResponse.json({
      user: mockUser,
      statistics: {
        total_recipes: 10,
        total_cookbooks: 2,
        difficulty_breakdown: { easy: 5, medium: 3, hard: 2, unspecified: 0 },
        avg_cook_time_minutes: 30,
        avg_recipes_per_cookbook: 5,
        cookbooks_with_recipes: 2,
        empty_cookbooks: 0,
      },
      recent_activity: [],
    })
  }),

  // Public endpoints
  http.get(`${API_BASE}/public/recipes`, ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')

    return HttpResponse.json({
      recipes: [{ ...mockRecipe, is_public: true }],
      pagination: {
        page,
        pages: 1,
        per_page: 12,
        total: 1,
        has_next: false,
        has_prev: false,
      },
    })
  }),

  http.get(`${API_BASE}/public/recipes/:id`, ({ params }) => {
    if (params.id === '999') {
      return HttpResponse.json(
        { error: 'Recipe not found' },
        { status: 404 }
      )
    }

    return HttpResponse.json({ ...mockRecipe, is_public: true, id: Number(params.id) })
  }),
]
