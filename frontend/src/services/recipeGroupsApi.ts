import type { Recipe } from '../types';
import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';

export interface RecipeGroup {
  id: number;
  name: string;
  description?: string;
  cover_image_url?: string;
  user_id: number;
  is_private: boolean;
  created_at: string;
  updated_at: string;
  recipe_count: number;
}

export interface RecipeGroupsResponse {
  groups: RecipeGroup[];
  total: number;
}

export interface RecipeGroupDetailResponse {
  group: RecipeGroup;
  recipes: Recipe[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

interface CreateGroupParams {
  name: string;
  description?: string;
  is_private?: boolean;
}

interface UpdateGroupParams {
  name?: string;
  description?: string;
  is_private?: boolean;
}

interface GetGroupParams {
  page?: number;
  per_page?: number;
  search?: string;
}

class RecipeGroupsApi {
  private baseUrl = getApiUrl();

  async getRecipeGroups(): Promise<RecipeGroupsResponse> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipe-groups`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching recipe groups:', error);
      throw new Error('Failed to fetch recipe groups');
    }
  }

  async createRecipeGroup(params: CreateGroupParams): Promise<{ group: RecipeGroup; message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipe-groups`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error creating recipe group:', error);
      throw error;
    }
  }

  async getRecipeGroup(groupId: number, params: GetGroupParams = {}): Promise<RecipeGroupDetailResponse> {
    const { page = 1, per_page = 12, search } = params;
    
    const searchParams = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
    });

    if (search && search.trim()) {
      searchParams.append('search', search.trim());
    }

    try {
      const response = await apiFetch(`${this.baseUrl}/recipe-groups/${groupId}?${searchParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Recipe group not found');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching recipe group:', error);
      throw error;
    }
  }

  async updateRecipeGroup(groupId: number, params: UpdateGroupParams): Promise<{ group: RecipeGroup; message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipe-groups/${groupId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating recipe group:', error);
      throw error;
    }
  }

  async deleteRecipeGroup(groupId: number): Promise<{ message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipe-groups/${groupId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting recipe group:', error);
      throw error;
    }
  }

  async addRecipeToGroup(groupId: number, recipeId: number): Promise<{ message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipe-groups/${groupId}/recipes/${recipeId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error adding recipe to group:', error);
      throw error;
    }
  }

  async removeRecipeFromGroup(groupId: number, recipeId: number): Promise<{ message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipe-groups/${groupId}/recipes/${recipeId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error removing recipe from group:', error);
      throw error;
    }
  }
}

export const recipeGroupsApi = new RecipeGroupsApi();