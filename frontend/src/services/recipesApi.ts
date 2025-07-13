import type { Recipe, RecipesResponse } from '../types';

interface FetchRecipesParams {
  page?: number;
  per_page?: number;
  search?: string;
  filter?: 'collection' | 'discover' | 'mine';
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

class RecipesApi {
  private baseUrl = '/api';

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

    try {
      const response = await fetch(`${this.baseUrl}/recipes?${searchParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for session auth
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

  async fetchRecipe(id: number): Promise<Recipe> {
    try {
      const response = await fetch(`${this.baseUrl}/recipes/${id}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

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

  private matchesSearch(recipe: Recipe, searchTerm: string): boolean {
    // Search in recipe title
    if (recipe.title.toLowerCase().includes(searchTerm)) {
      return true;
    }

    // Search in recipe description
    if (recipe.description?.toLowerCase().includes(searchTerm)) {
      return true;
    }

    // Search in ingredients
    if (recipe.ingredients.some(ingredient => 
      ingredient.name.toLowerCase().includes(searchTerm)
    )) {
      return true;
    }

    // Search in tags
    if (recipe.tags.some(tag => 
      tag.name.toLowerCase().includes(searchTerm)
    )) {
      return true;
    }

    // Search in cookbook title
    if (recipe.cookbook?.title.toLowerCase().includes(searchTerm)) {
      return true;
    }

    // Search in instructions
    if (recipe.instructions.some(instruction => 
      instruction.text.toLowerCase().includes(searchTerm)
    )) {
      return true;
    }

    return false;
  }

  async uploadRecipeImage(recipeId: number, imageFile: File): Promise<{message: string; image: any}> {
    try {
      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}/images`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading recipe image:', error);
      throw error;
    }
  }

  async updateRecipe(recipeId: number, params: UpdateRecipeParams): Promise<Recipe> {
    try {
      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
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

  async updateRecipeIngredients(recipeId: number, params: UpdateIngredientsParams): Promise<Recipe> {
    try {
      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}/ingredients`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
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
      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}/instructions`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
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
      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}/tags`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
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

  async toggleRecipePrivacy(recipeId: number, isPublic: boolean): Promise<Recipe> {
    try {
      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}/privacy`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ is_public: isPublic }),
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
      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}/publish`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
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
      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}/unpublish`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
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

  async addToCollection(recipeId: number): Promise<{ message: string; collection_item: any }> {
    try {
      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}/add-to-collection`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error adding recipe to collection:', error);
      throw error;
    }
  }

  async removeFromCollection(recipeId: number): Promise<{ message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/recipes/${recipeId}/remove-from-collection`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error removing recipe from collection:', error);
      throw error;
    }
  }

  async fetchDiscoverRecipes(params: { page?: number; per_page?: number; search?: string } = {}): Promise<RecipesResponse> {
    const { page = 1, per_page = 12, search } = params;
    
    const searchParams = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
    });

    if (search && search.trim()) {
      searchParams.append('search', search.trim());
    }

    try {
      const response = await fetch(`${this.baseUrl}/recipes/discover?${searchParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching discover recipes:', error);
      throw new Error('Failed to fetch discover recipes');
    }
  }
}

export const recipesApi = new RecipesApi();