import type { UserProfile } from '../types';
import { apiFetch } from '../utils/apiInterceptor';

class UserApi {
  private baseUrl = import.meta.env.VITE_API_URL || '/api';

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
}

export const userApi = new UserApi();