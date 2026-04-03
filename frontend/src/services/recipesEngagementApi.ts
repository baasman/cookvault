import type { Recipe, RecipeNote, RecipeComment, CommentsResponse, RatingResponse, DeleteRatingResponse } from '../types';
import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';

class RecipesEngagementApi {
  private baseUrl = getApiUrl();

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

  // Collection Methods
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

  // Instruction Note Methods
  async saveInstructionNote(recipeId: number, instructionId: number, content: string): Promise<{ note: { content: string } | null }> {
    const response = await apiFetch(`${this.baseUrl}/recipes/${recipeId}/instructions/${instructionId}/note`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to save note');
    }

    return response.json();
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
}

export const recipesEngagementApi = new RecipesEngagementApi();
