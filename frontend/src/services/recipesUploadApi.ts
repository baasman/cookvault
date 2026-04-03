import type { Recipe, MultiUploadResponse, MultiJobStatusResponse, Instruction, VideoUploadResponse, VideoJobStatusResponse } from '../types';
import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';

class RecipesUploadApi {
  private baseUrl = getApiUrl();

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

  async uploadRecipeVideo(
    videoFile: File,
    options?: {
      cookbook_id?: number;
      is_original_recipe?: boolean;
      translate_to_english?: boolean;
      create_new_cookbook?: boolean;
      new_cookbook_title?: string;
      new_cookbook_author?: string;
      new_cookbook_description?: string;
      new_cookbook_publisher?: string;
      new_cookbook_isbn?: string;
    }
  ): Promise<VideoUploadResponse> {
    try {
      const formData = new FormData();
      formData.append('video', videoFile);

      if (options?.cookbook_id) {
        formData.append('cookbook_id', options.cookbook_id.toString());
      }

      if (options?.is_original_recipe !== undefined) {
        formData.append('is_original_recipe', options.is_original_recipe.toString());
      }

      if (options?.translate_to_english) {
        formData.append('translate_to_english', 'true');
      }

      if (options?.create_new_cookbook) {
        formData.append('create_new_cookbook', 'true');
        if (options.new_cookbook_title) {
          formData.append('new_cookbook_title', options.new_cookbook_title);
        }
        if (options.new_cookbook_author) {
          formData.append('new_cookbook_author', options.new_cookbook_author);
        }
        if (options.new_cookbook_description) {
          formData.append('new_cookbook_description', options.new_cookbook_description);
        }
        if (options.new_cookbook_publisher) {
          formData.append('new_cookbook_publisher', options.new_cookbook_publisher);
        }
        if (options.new_cookbook_isbn) {
          formData.append('new_cookbook_isbn', options.new_cookbook_isbn);
        }
      }

      const response = await apiFetch(`${this.baseUrl}/recipes/upload-video`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading recipe video:', error);
      throw error;
    }
  }

  async uploadRecipeYouTube(
    url: string,
    options?: {
      cookbook_id?: number;
      is_original_recipe?: boolean;
      translate_to_english?: boolean;
      create_new_cookbook?: boolean;
      new_cookbook_title?: string;
      new_cookbook_author?: string;
      new_cookbook_description?: string;
      new_cookbook_publisher?: string;
      new_cookbook_isbn?: string;
    }
  ): Promise<VideoUploadResponse> {
    try {
      const payload: Record<string, unknown> = { url };

      if (options?.cookbook_id) {
        payload.cookbook_id = options.cookbook_id;
      }

      if (options?.is_original_recipe !== undefined) {
        payload.is_original_recipe = options.is_original_recipe;
      }

      if (options?.translate_to_english) {
        payload.translate_to_english = true;
      }

      if (options?.create_new_cookbook) {
        payload.create_new_cookbook = true;
        if (options.new_cookbook_title) {
          payload.new_cookbook_title = options.new_cookbook_title;
        }
        if (options.new_cookbook_author) {
          payload.new_cookbook_author = options.new_cookbook_author;
        }
        if (options.new_cookbook_description) {
          payload.new_cookbook_description = options.new_cookbook_description;
        }
        if (options.new_cookbook_publisher) {
          payload.new_cookbook_publisher = options.new_cookbook_publisher;
        }
        if (options.new_cookbook_isbn) {
          payload.new_cookbook_isbn = options.new_cookbook_isbn;
        }
      }

      const response = await apiFetch(`${this.baseUrl}/recipes/upload-youtube`, {
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
      console.error('Error uploading YouTube recipe:', error);
      throw error;
    }
  }

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

  async cancelJob(jobId: number): Promise<{ message: string; status: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/job/${jobId}/cancel`, {
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
      console.error('Error cancelling job:', error);
      throw error;
    }
  }

  async cancelMultiJob(jobId: number): Promise<{ message: string; status: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/multi-job/${jobId}/cancel`, {
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
      console.error('Error cancelling multi-job:', error);
      throw error;
    }
  }

  async cancelVideoJob(jobId: number): Promise<{ message: string; status: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/video-job/${jobId}/cancel`, {
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
      console.error('Error cancelling video job:', error);
      throw error;
    }
  }

  async getVideoJobStatus(jobId: number): Promise<VideoJobStatusResponse> {
    try {
      const response = await apiFetch(`${this.baseUrl}/recipes/video-job-status/${jobId}`, {
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
      console.error('Error getting video job status:', error);
      throw error;
    }
  }
}

export const recipesUploadApi = new RecipesUploadApi();
