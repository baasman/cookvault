import type { Recipe, RecipesResponse } from '../types';
import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';
import { getAuthToken } from './storageService';

interface FetchRecipesParams {
  page?: number;
  per_page?: number;
  search?: string;
  filter?: 'collection' | 'discover' | 'mine';
  ingredients?: string[];
  ingredientMatch?: 'any' | 'all';
  courseType?: string;
}

interface IngredientSuggestion {
  id: number;
  name: string;
}

interface UpdateRecipeParams {
  title?: string;
  description?: string;
  prep_time?: number;
  cook_time?: number;
  servings?: number;
  difficulty?: string;
}

type EditableIngredient = {
  name: string;
  quantity?: number;
  unit?: string;
  preparation?: string;
  optional: boolean;
};

interface UpdateIngredientsParams {
  ingredients: EditableIngredient[];
}

interface UpdateInstructionsParams {
  instructions: string[];
}

interface UpdateTagsParams {
  tags: string[];
}

interface FeaturesResponse {
  youtube_import_enabled: boolean;
}

class RecipesApi {
  private baseUrl = getApiUrl();

  async getFeatures(): Promise<FeaturesResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/features`, {
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
      console.error('Error fetching features:', error);
      // Default to disabled if fetch fails
      return { youtube_import_enabled: false };
    }
  }

  async createEmptyRecipe(title: string, cookbook_id?: number): Promise<Recipe> {
    try {
      const requestBody: { title: string; cookbook_id?: number } = { title };
      if (cookbook_id) {
        requestBody.cookbook_id = cookbook_id;
      }

      const response = await apiFetch(`${this.baseUrl}/recipes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error creating empty recipe:', error);
      throw error;
    }
  }

  async fetchRecipes(params: FetchRecipesParams = {}): Promise<RecipesResponse> {
    const { page = 1, per_page = 12, filter = 'collection' } = params;

    const searchParams = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
      filter: filter,
    });

    // Add search parameter to the request
    if (params.search && params.search.trim()) {
      searchParams.append('search', params.search.trim());
    }

    // Add ingredient filter parameters
    if (params.ingredients && params.ingredients.length > 0) {
      searchParams.append('ingredients', params.ingredients.join(','));
      if (params.ingredientMatch) {
        searchParams.append('ingredient_match', params.ingredientMatch);
      }
    }

    // Add course type filter
    if (params.courseType) {
      searchParams.append('course_type', params.courseType);
    }

    try {
      const response = await apiFetch(`${this.baseUrl}/recipes?${searchParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching recipes:', error);
      throw new Error('Failed to fetch recipes');
    }
  }

  async fetchRecipesByCookbook(cookbookId: number): Promise<RecipesResponse> {
    try {
      const response = await apiFetch(`${this.baseUrl}/cookbooks/${cookbookId}/recipes`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching cookbook recipes:', error);
      throw new Error('Failed to fetch cookbook recipes');
    }
  }

  async fetchRecipe(id: number): Promise<Recipe> {
    try {
      // Check if user is authenticated by looking for auth token (works on web and native)
      const authToken = await getAuthToken();

      let response: Response;

      if (authToken) {
        // If authenticated, try private API first, fallback to public if needed
        response = await apiFetch(`${this.baseUrl}/recipes/${id}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        // If private API fails with 401, try public API
        if (!response.ok && response.status === 401) {
          response = await apiFetch(`${this.baseUrl}/public/recipes/${id}`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          });
        }
      } else {
        // If not authenticated, go directly to public API
        response = await apiFetch(`${this.baseUrl}/public/recipes/${id}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
      }

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Recipe not found');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching recipe:', error);
      throw error;
    }
  }

  async updateRecipe(recipeId: number, params: UpdateRecipeParams): Promise<Recipe> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}`, {
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

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error updating recipe:', error);
      throw error;
    }
  }

  async linkRecipeToCookbook(recipeId: number, cookbookId: number | null): Promise<Recipe> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/cookbook`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cookbook_id: cookbookId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error linking recipe to cookbook:', error);
      throw error;
    }
  }

  async updateRecipeIngredients(recipeId: number, params: UpdateIngredientsParams): Promise<Recipe> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/ingredients`, {
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

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error updating recipe ingredients:', error);
      throw error;
    }
  }

  async updateRecipeInstructions(recipeId: number, params: UpdateInstructionsParams): Promise<Recipe> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/instructions`, {
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

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error updating recipe instructions:', error);
      throw error;
    }
  }

  async updateRecipeTags(recipeId: number, params: UpdateTagsParams): Promise<Recipe> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/tags`, {
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

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error updating recipe tags:', error);
      throw error;
    }
  }

  async toggleRecipePrivacy(recipeId: number, isPublic: boolean, copyrightConsent?: Record<string, boolean>): Promise<Recipe> {
    try {
      const requestBody: { is_public: boolean; copyright_consent?: Record<string, boolean> } = {
        is_public: isPublic
      };

      if (isPublic && copyrightConsent) {
        requestBody.copyright_consent = copyrightConsent;
      }

      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/privacy`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error toggling recipe privacy:', error);
      throw error;
    }
  }

  async publishRecipe(recipeId: number): Promise<Recipe> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/publish`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error publishing recipe:', error);
      throw error;
    }
  }

  async unpublishRecipe(recipeId: number): Promise<Recipe> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/unpublish`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error unpublishing recipe:', error);
      throw error;
    }
  }

  async fetchDiscoverRecipes(params: { page?: number; per_page?: number; search?: string; ingredients?: string[]; ingredientMatch?: 'any' | 'all'; courseType?: string } = {}): Promise<RecipesResponse> {
    const { page = 1, per_page = 12, search } = params;

    const searchParams = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
    });

    if (search && search.trim()) {
      searchParams.append('search', search.trim());
    }

    // Add ingredient filter parameters
    if (params.ingredients && params.ingredients.length > 0) {
      searchParams.append('ingredients', params.ingredients.join(','));
      if (params.ingredientMatch) {
        searchParams.append('ingredient_match', params.ingredientMatch);
      }
    }

    // Add course type filter
    if (params.courseType) {
      searchParams.append('course_type', params.courseType);
    }

    try {
      // Use public endpoint for unauthenticated access
      const response = await fetch(`${this.baseUrl}/public/recipes?${searchParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      // Transform the response to match expected RecipesResponse format
      return {
        recipes: data.recipes,
        total: data.pagination.total,
        pages: data.pagination.pages,
        current_page: data.pagination.page,
      };
    } catch (error) {
      console.error('Error fetching discover recipes:', error);
      throw new Error('Failed to fetch discover recipes');
    }
  }

  async searchIngredients(query: string, limit = 10): Promise<{ ingredients: IngredientSuggestion[] }> {
    try {
      const response = await fetch(
        `${this.baseUrl}/ingredients/search?q=${encodeURIComponent(query)}&limit=${limit}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error searching ingredients:', error);
      return { ingredients: [] };
    }
  }

  async deleteRecipe(recipeId: number): Promise<{ message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}`, {
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
      console.error('Error deleting recipe:', error);
      throw error;
    }
  }

  // Featured recipes admin methods
  async featureRecipe(recipeId: number): Promise<Recipe> {
    try {
      const response = await apiFetch(`${this.baseUrl}/admin/recipes/${recipeId}/feature`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error featuring recipe:', error);
      throw error;
    }
  }

  // Bulk operations
  async bulkDelete(recipeIds: number[]): Promise<{ deleted: number[]; errors: Array<{ id: number; reason: string }> }> {
    const response = await apiFetch(`${this.baseUrl}/recipes/bulk/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipe_ids: recipeIds }),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Bulk delete failed');
    }
    return response.json();
  }

  async bulkAddToGroup(recipeIds: number[], groupId: number): Promise<{ added: number[]; already_in_group: number[]; errors: Array<{ id: number; reason: string }> }> {
    const response = await apiFetch(`${this.baseUrl}/recipes/bulk/add-to-group`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipe_ids: recipeIds, group_id: groupId }),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Bulk add to group failed');
    }
    return response.json();
  }

  async bulkRemoveFromGroup(recipeIds: number[], groupId: number): Promise<{ removed: number }> {
    const response = await apiFetch(`${this.baseUrl}/recipes/bulk/remove-from-group`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipe_ids: recipeIds, group_id: groupId }),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Bulk remove from group failed');
    }
    return response.json();
  }

  async bulkTogglePrivacy(recipeIds: number[], isPublic: boolean, copyrightConsent?: Record<string, boolean>): Promise<{ updated: number[]; errors: Array<{ id: number; reason: string }> }> {
    const response = await apiFetch(`${this.baseUrl}/recipes/bulk/privacy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipe_ids: recipeIds, is_public: isPublic, copyright_consent: copyrightConsent }),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Bulk privacy update failed');
    }
    return response.json();
  }

  async bulkUpdateTags(recipeIds: number[], tags: string[], action: 'add' | 'remove' | 'set'): Promise<{ updated: number[]; errors: Array<{ id: number; reason: string }> }> {
    const response = await apiFetch(`${this.baseUrl}/recipes/bulk/tags`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipe_ids: recipeIds, tags, action }),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Bulk tags update failed');
    }
    return response.json();
  }

  async unfeatureRecipe(recipeId: number): Promise<Recipe> {
    try {
      const response = await apiFetch(`${this.baseUrl}/admin/recipes/${recipeId}/feature`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.recipe;
    } catch (error) {
      console.error('Error unfeaturing recipe:', error);
      throw error;
    }
  }
}

export const recipesApi = new RecipesApi();

// Re-export split API modules for backward compatibility
export { recipesUploadApi } from './recipesUploadApi';
export { recipesEngagementApi } from './recipesEngagementApi';
