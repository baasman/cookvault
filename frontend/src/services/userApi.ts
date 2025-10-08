import type { UserProfile } from '../types';
import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';

class UserApi {
  private baseUrl = getApiUrl();

  async fetchUserProfile(): Promise<UserProfile> {
    try {
      const response = await apiFetch(`${this.baseUrl}/user/profile`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching user profile:', error);
      throw error;
    }
  }

  async updateProfile(formData: FormData): Promise<any> {
    try {
      const response = await apiFetch(`${this.baseUrl}/user/profile`, {
        method: 'PUT',
        body: formData, // Don't set Content-Type for FormData, let the browser set it
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required');
        }
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating user profile:', error);
      throw error;
    }
  }

  async fetchPublicUserProfile(userId: number): Promise<any> {
    try {
      const response = await apiFetch(`${this.baseUrl}/users/${userId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('User not found');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching public user profile:', error);
      throw error;
    }
  }

  async fetchPublicUserByUsername(username: string): Promise<any> {
    try {
      const response = await apiFetch(`${this.baseUrl}/users/by-username/${encodeURIComponent(username)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('User not found');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching public user profile by username:', error);
      throw error;
    }
  }
}

export const userApi = new UserApi();