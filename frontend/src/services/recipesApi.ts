import type { Recipe, RecipesResponse, RecipeNote, RecipeComment, CommentsResponse, MultiUploadResponse, MultiJobStatusResponse, Instruction, RatingResponse, DeleteRatingResponse } from '../types';
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

class RecipesApi {
  private baseUrl = getApiUrl();

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

  /* 
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
  */

  async uploadRecipeImage(recipeId: number, imageFile: File): Promise<{message: string; image: any}> {
    try {
      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/images`, {
        method: 'POST',
        body: formData,
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

  async uploadPrimaryRecipeImage(recipeId: number, imageFile: File): Promise<{message: string; image: any; recipe: Recipe}> {
    try {
      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/images/primary`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading primary recipe image:', error);
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

  async addToCollection(recipeId: number): Promise<{ message: string; collection_item: any }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/add-to-collection`, {
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
      console.error('Error adding recipe to collection:', error);
      throw error;
    }
  }

  async removeFromCollection(recipeId: number): Promise<{ message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/remove-from-collection`, {
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
      console.error('Error removing recipe from collection:', error);
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
      // Use regular fetch instead of apiFetch for public access
      const response = await fetch(`${this.baseUrl}/recipes/discover?${searchParams}`, {
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

  // Recipe Notes Methods
  async getUserNote(recipeId: number): Promise<{ note: RecipeNote | null }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/notes`, {
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
      console.error('Error fetching user note:', error);
      throw new Error('Failed to fetch user note');
    }
  }

  async saveUserNote(recipeId: number, content: string): Promise<{ note: RecipeNote }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/notes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error saving user note:', error);
      throw error;
    }
  }

  async deleteUserNote(recipeId: number): Promise<{ message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/notes`, {
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
      console.error('Error deleting user note:', error);
      throw error;
    }
  }

  // Recipe Comments Methods
  async getRecipeComments(recipeId: number, params: { page?: number; per_page?: number } = {}): Promise<CommentsResponse> {
    const { page = 1, per_page = 20 } = params;
    
    const searchParams = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
    });

    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/comments?${searchParams}`, {
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
      console.error('Error fetching recipe comments:', error);
      throw new Error('Failed to fetch recipe comments');
    }
  }

  async createComment(recipeId: number, content: string): Promise<{ comment: RecipeComment }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error creating comment:', error);
      throw error;
    }
  }

  async updateComment(recipeId: number, commentId: number, content: string): Promise<{ comment: RecipeComment }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/comments/${commentId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating comment:', error);
      throw error;
    }
  }

  async deleteComment(recipeId: number, commentId: number): Promise<{ message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/comments/${commentId}`, {
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
      console.error('Error deleting comment:', error);
      throw error;
    }
  }

  async copyRecipe(recipeId: number): Promise<{ recipe: Recipe; message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/copy`, {
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
      console.error('Error copying recipe:', error);
      throw error;
    }
  }

  // Multi-image upload methods
  async uploadMultipleImages(images: File[], cookbook_id?: number, is_original_recipe?: boolean, translate_to_english?: boolean): Promise<MultiUploadResponse> {
    try {
      const formData = new FormData();

      // Add all images to form data
      images.forEach((image) => {
        formData.append('images', image);
      });

      if (cookbook_id) {
        formData.append('cookbook_id', cookbook_id.toString());
      }

      // Add recipe source information for copyright protection
      if (is_original_recipe !== undefined) {
        formData.append('is_original_recipe', is_original_recipe.toString());
      }

      // Add translation option
      if (translate_to_english) {
        formData.append('translate_to_english', 'true');
      }

      const response = await apiFetch(`${this.baseUrl}/recipes/upload-multi`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading multiple images:', error);
      throw error;
    }
  }

  async uploadRecipeText(text: string, formData: any): Promise<any> {
    try {
      const payload: any = {
        text: text,
      };

      // Add cookbook information if provided
      if (formData.create_new_cookbook) {
        payload.create_new_cookbook = true;
        payload.new_cookbook_title = formData.new_cookbook_title || '';
        if (formData.new_cookbook_author) payload.new_cookbook_author = formData.new_cookbook_author;
        if (formData.new_cookbook_description) payload.new_cookbook_description = formData.new_cookbook_description;
        if (formData.new_cookbook_publisher) payload.new_cookbook_publisher = formData.new_cookbook_publisher;
        if (formData.new_cookbook_isbn) payload.new_cookbook_isbn = formData.new_cookbook_isbn;
        if (formData.new_cookbook_publication_date) payload.new_cookbook_publication_date = formData.new_cookbook_publication_date;
      } else if (formData.search_existing_cookbook && formData.selected_existing_cookbook_id) {
        payload.cookbook_id = formData.selected_existing_cookbook_id;
      } else if (formData.cookbook_id) {
        payload.cookbook_id = formData.cookbook_id;
      }

      // Add recipe source information for copyright protection
      if (formData.is_original_recipe !== undefined) {
        payload.is_original_recipe = formData.is_original_recipe;
      }

      // Add translation option
      if (formData.translate_to_english) {
        payload.translate_to_english = true;
      }

      const response = await apiFetch(`${this.baseUrl}/recipes/upload-text`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading recipe text:', error);
      throw error;
    }
  }

  async uploadRecipeUrl(url: string, formData: any): Promise<any> {
    try {
      const payload: any = {
        url: url,
      };

      // Add cookbook information if provided
      if (formData.create_new_cookbook) {
        payload.create_new_cookbook = true;
        payload.new_cookbook_title = formData.new_cookbook_title || '';
        if (formData.new_cookbook_author) payload.new_cookbook_author = formData.new_cookbook_author;
        if (formData.new_cookbook_description) payload.new_cookbook_description = formData.new_cookbook_description;
        if (formData.new_cookbook_publisher) payload.new_cookbook_publisher = formData.new_cookbook_publisher;
        if (formData.new_cookbook_isbn) payload.new_cookbook_isbn = formData.new_cookbook_isbn;
        if (formData.new_cookbook_publication_date) payload.new_cookbook_publication_date = formData.new_cookbook_publication_date;
      } else if (formData.search_existing_cookbook && formData.selected_existing_cookbook_id) {
        payload.cookbook_id = formData.selected_existing_cookbook_id;
      } else if (formData.cookbook_id) {
        payload.cookbook_id = formData.cookbook_id;
      }

      // Add translation option
      if (formData.translate_to_english) {
        payload.translate_to_english = true;
      }

      const response = await apiFetch(`${this.baseUrl}/recipes/upload-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading recipe from URL:', error);
      throw error;
    }
  }

  async getMultiJobStatus(jobId: number): Promise<MultiJobStatusResponse> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/multi-job-status/${jobId}`, {
        method: 'GET',
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
      console.error('Error getting multi-job status:', error);
      throw error;
    }
  }

  async getJobStatus(jobId: number) {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/job-status/${jobId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('Error getting job status:', error);
      throw error;
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

  // Instruction Image Methods
  async uploadInstructionImage(recipeId: number, instructionId: number, imageFile: File): Promise<Instruction> {
    const formData = new FormData();
    formData.append('image', imageFile);

    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/instructions/${instructionId}/image`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.instruction;
    } catch (error) {
      console.error('Error uploading instruction image:', error);
      throw error;
    }
  }

  async removeInstructionImage(recipeId: number, instructionId: number): Promise<Instruction> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/instructions/${instructionId}/image`, {
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
      return data.instruction;
    } catch (error) {
      console.error('Error removing instruction image:', error);
      throw error;
    }
  }

  // Recipe Rating Methods
  async getRating(recipeId: number): Promise<RatingResponse> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/rating`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Recipe not found');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching recipe rating:', error);
      throw error;
    }
  }

  async submitRating(recipeId: number, rating: number): Promise<RatingResponse> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/rating`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ rating }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error submitting recipe rating:', error);
      throw error;
    }
  }

  async deleteRating(recipeId: number): Promise<DeleteRatingResponse> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/rating`, {
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
      console.error('Error deleting recipe rating:', error);
      throw error;
    }
  }
}

export const recipesApi = new RecipesApi();