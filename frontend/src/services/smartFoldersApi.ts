import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';
import type { Recipe } from '../types';

export interface SmartFolderRule {
  field: string;
  operator: string;
  value: string | number | boolean | string[];
}

export interface SmartFolderRules {
  match: 'all' | 'any';
  conditions: SmartFolderRule[];
}

export interface SmartFolder {
  id: number;
  name: string;
  description?: string;
  rules: SmartFolderRules;
  icon?: string;
  recipe_count: number | null;
  created_at: string;
  updated_at: string;
}

interface SmartFoldersListResponse {
  smart_folders: SmartFolder[];
}

interface SmartFolderResponse {
  smart_folder: SmartFolder;
}

interface SmartFolderRecipesResponse {
  recipes: Recipe[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

interface PreviewResponse {
  count: number;
}

class SmartFoldersApi {
  private baseUrl = getApiUrl();

  async getSmartFolders(): Promise<SmartFoldersListResponse> {
    const response = await apiFetch(`${this.baseUrl}/smart-folders`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Failed to fetch smart folders');
    }
    return response.json();
  }

  async createSmartFolder(params: {
    name: string;
    description?: string;
    rules: SmartFolderRules;
    icon?: string;
  }): Promise<SmartFolderResponse> {
    const response = await apiFetch(`${this.baseUrl}/smart-folders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Failed to create smart folder');
    }
    return response.json();
  }

  async getSmartFolder(id: number): Promise<SmartFolderResponse> {
    const response = await apiFetch(`${this.baseUrl}/smart-folders/${id}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Smart folder not found');
    }
    return response.json();
  }

  async updateSmartFolder(
    id: number,
    params: { name?: string; description?: string; rules?: SmartFolderRules; icon?: string }
  ): Promise<SmartFolderResponse> {
    const response = await apiFetch(`${this.baseUrl}/smart-folders/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Failed to update smart folder');
    }
    return response.json();
  }

  async deleteSmartFolder(id: number): Promise<void> {
    const response = await apiFetch(`${this.baseUrl}/smart-folders/${id}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Failed to delete smart folder');
    }
  }

  async getSmartFolderRecipes(
    id: number,
    params?: { page?: number; per_page?: number; search?: string }
  ): Promise<SmartFolderRecipesResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.per_page) searchParams.set('per_page', String(params.per_page));
    if (params?.search) searchParams.set('search', params.search);

    const response = await apiFetch(
      `${this.baseUrl}/smart-folders/${id}/recipes?${searchParams}`,
      { method: 'GET', headers: { 'Content-Type': 'application/json' } }
    );
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Failed to fetch recipes');
    }
    return response.json();
  }

  async previewSmartFolder(rules: SmartFolderRules): Promise<PreviewResponse> {
    const response = await apiFetch(`${this.baseUrl}/smart-folders/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rules }),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Failed to preview');
    }
    return response.json();
  }
}

export const smartFoldersApi = new SmartFoldersApi();
