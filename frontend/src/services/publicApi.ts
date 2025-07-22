import axios from 'axios';
import type { PublicRecipesResponse, UserPublicRecipesResponse, Recipe, PublicStatsResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Create axios instance for public API (no auth required)
const publicApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// Response interceptor for error handling
publicApi.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Public API Error:', error);
    return Promise.reject(error);
  }
);

export const publicRecipesApi = {
  // Get all public recipes with pagination and filtering
  getPublicRecipes: async (params?: {
    page?: number;
    per_page?: number;
    search?: string;
    difficulty?: string;
  }): Promise<PublicRecipesResponse> => {
    const response = await publicApi.get('/public/recipes', { params });
    return response.data;
  },

  // Get a specific public recipe by ID
  getPublicRecipe: async (recipeId: number): Promise<Recipe> => {
    const response = await publicApi.get(`/public/recipes/${recipeId}`);
    return response.data;
  },

  // Get all public recipes by a specific user
  getUserPublicRecipes: async (
    userId: number,
    params?: {
      page?: number;
      per_page?: number;
    }
  ): Promise<UserPublicRecipesResponse> => {
    const response = await publicApi.get(`/public/users/${userId}/recipes`, { params });
    return response.data;
  },

  // Get featured public recipes (most recently published)
  getFeaturedRecipes: async (limit?: number): Promise<{ recipes: Recipe[] }> => {
    const response = await publicApi.get('/public/recipes/featured', { 
      params: { limit } 
    });
    return response.data;
  },

  // Get public statistics about the platform
  getPublicStats: async (): Promise<PublicStatsResponse> => {
    const response = await publicApi.get('/public/stats');
    return response.data;
  },
};

export default publicRecipesApi;