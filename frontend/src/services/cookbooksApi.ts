import type { Cookbook } from '../types';

interface FetchCookbooksParams {
  page?: number;
  per_page?: number;
  search?: string;
  sort_by?: 'title' | 'author' | 'created_at' | 'recipe_count';
}

interface CookbooksResponse {
  cookbooks: Cookbook[];
  total: number;
  pages: number;
  current_page: number;
  per_page: number;
  has_next: boolean;
  has_prev: boolean;
}

interface CreateCookbookData {
  title: string;
  author?: string;
  description?: string;
  isbn?: string;
  publisher?: string;
  cover_image_url?: string;
  publication_date?: string;
}

interface GoogleBook {
  google_books_id: string;
  title: string;
  author: string;
  publisher: string;
  publication_date: string | null;
  isbn: string;
  description: string;
  thumbnail_url: string | null;
  categories: string[];
  page_count: number | null;
}

interface GoogleBooksResponse {
  books: GoogleBook[];
  total: number;
  query: string;
}

class CookbooksApi {
  private baseUrl = import.meta.env.VITE_API_URL || '/api';

  async fetchCookbooks(params: FetchCookbooksParams = {}): Promise<CookbooksResponse> {
    const { page = 1, per_page = 12, search, sort_by = 'title' } = params;
    
    const searchParams = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
      sort_by,
    });

    if (search && search.trim()) {
      searchParams.append('search', search.trim());
    }

    try {
      const response = await fetch(`${this.baseUrl}/cookbooks?${searchParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies for session auth
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching cookbooks:', error);
      throw new Error('Failed to fetch cookbooks');
    }
  }

  async fetchCookbook(id: number, search?: string): Promise<Cookbook> {
    try {
      const searchParams = new URLSearchParams();
      if (search) {
        searchParams.append('search', search);
      }
      
      const url = `${this.baseUrl}/cookbooks/${id}${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Cookbook not found');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching cookbook:', error);
      throw error;
    }
  }

  async createCookbook(data: CreateCookbookData): Promise<Cookbook> {
    try {
      const response = await fetch(`${this.baseUrl}/cookbooks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.cookbook;
    } catch (error) {
      console.error('Error creating cookbook:', error);
      throw error;
    }
  }

  async updateCookbook(id: number, data: Partial<CreateCookbookData>): Promise<Cookbook> {
    try {
      const response = await fetch(`${this.baseUrl}/cookbooks/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.cookbook;
    } catch (error) {
      console.error('Error updating cookbook:', error);
      throw error;
    }
  }

  async deleteCookbook(id: number): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/cookbooks/${id}`, {
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
    } catch (error) {
      console.error('Error deleting cookbook:', error);
      throw error;
    }
  }

  async searchAllCookbooks(query: string): Promise<Cookbook[]> {
    try {
      const searchParams = new URLSearchParams({
        q: query.trim(),
      });

      const response = await fetch(`${this.baseUrl}/cookbooks/search?${searchParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.cookbooks || [];
    } catch (error) {
      console.error('Error searching cookbooks:', error);
      throw new Error('Failed to search cookbooks');
    }
  }

  async uploadCookbookImage(cookbookId: number, imageFile: File): Promise<any> {
    try {
      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await fetch(`${this.baseUrl}/cookbooks/${cookbookId}/images`, {
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
      console.error('Error uploading cookbook image:', error);
      throw error;
    }
  }

  async searchGoogleBooks(query: string, maxResults: number = 10): Promise<GoogleBooksResponse> {
    try {
      const searchParams = new URLSearchParams({
        q: query.trim(),
        max_results: maxResults.toString(),
      });

      const response = await fetch(`${this.baseUrl}/cookbooks/search/google-books?${searchParams}`, {
        method: 'GET',
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
      console.error('Error searching online book database:', error);
      throw error;
    }
  }

  async searchGoogleBooksByIsbn(isbn: string): Promise<GoogleBook | null> {
    try {
      const response = await fetch(`${this.baseUrl}/cookbooks/search/google-books/isbn/${encodeURIComponent(isbn)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.book;
    } catch (error) {
      console.error('Error searching online book database by ISBN:', error);
      throw error;
    }
  }

  async createCookbookFromGoogleBooks(googleBooksId: string): Promise<Cookbook> {
    try {
      const response = await fetch(`${this.baseUrl}/cookbooks/from-google-books`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          google_books_id: googleBooksId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.cookbook;
    } catch (error) {
      console.error('Error creating cookbook from online database:', error);
      throw error;
    }
  }
}

export const cookbooksApi = new CookbooksApi();

export type { GoogleBook, GoogleBooksResponse };