import type { Recipe, Source } from '../types';
import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';

export interface SourcesResponse {
  sources: Source[];
  pagination: {
    page: number;
    pages: number;
    per_page: number;
    total: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface SourceDetailResponse {
  source: Source;
  recipes: Recipe[];
  pagination: {
    page: number;
    pages: number;
    per_page: number;
    total: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

interface GetSourcesParams {
  page?: number;
  per_page?: number;
  sort?: 'recipe_count' | 'domain' | 'name' | 'created_at';
  order?: 'asc' | 'desc';
  search?: string;
}

interface GetSourceParams {
  page?: number;
  per_page?: number;
  search?: string;
}

interface UpdateSourceParams {
  name?: string | null;
}

class SourcesApi {
  private baseUrl = getApiUrl();

  async getSources(params: GetSourcesParams = {}): Promise<SourcesResponse> {
    const { page = 1, per_page = 20, sort = 'recipe_count', order = 'desc', search } = params;

    const searchParams = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
      sort,
      order,
    });

    if (search && search.trim()) {
      searchParams.append('search', search.trim());
    }

    try {
      const response = await apiFetch(`${this.baseUrl}/sources?${searchParams}`, {
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
      console.error('Error fetching sources:', error);
      throw new Error('Failed to fetch sources');
    }
  }

  async getSource(sourceId: number, params: GetSourceParams = {}): Promise<SourceDetailResponse> {
    const { page = 1, per_page = 12, search } = params;

    const searchParams = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
    });

    if (search && search.trim()) {
      searchParams.append('search', search.trim());
    }

    try {
      const response = await apiFetch(`${this.baseUrl}/sources/${sourceId}?${searchParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Source not found');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching source:', error);
      throw error;
    }
  }

  async updateSource(sourceId: number, params: UpdateSourceParams): Promise<Source> {
    try {
      const response = await apiFetch(`${this.baseUrl}/sources/${sourceId}`, {
        method: 'PATCH',
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
      console.error('Error updating source:', error);
      throw error;
    }
  }
}

export const sourcesApi = new SourcesApi();
