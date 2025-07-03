import type { Recipe, RecipesResponse } from '../types';

interface FetchRecipesParams {
  page?: number;
  per_page?: number;
  search?: string;
}

class RecipesApi {
  private baseUrl = '/api';

  async fetchRecipes(params: FetchRecipesParams = {}): Promise<RecipesResponse> {
    const { page = 1, per_page = 12 } = params;
    
    const searchParams = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
    });

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
      
      // If search term is provided, filter on the frontend for now
      // TODO: Implement server-side search when backend supports it
      if (params.search && params.search.trim()) {
        const searchTerm = params.search.toLowerCase().trim();
        const filteredRecipes = data.recipes.filter((recipe: Recipe) => 
          this.matchesSearch(recipe, searchTerm)
        );
        
        return {
          ...data,
          recipes: filteredRecipes,
          total: filteredRecipes.length,
          pages: Math.ceil(filteredRecipes.length / per_page)
        };
      }

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

  async uploadRecipeImage(recipeId: number, imageFile: File): Promise<any> {
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
}

export const recipesApi = new RecipesApi();