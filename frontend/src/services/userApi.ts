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

  async changePassword(currentPassword: string, newPassword: string): Promise<any> {
    try {
      const response = await apiFetch(`${this.baseUrl}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Current password is incorrect');
        }
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error changing password:', error);
      throw error;
    }
  }

  async requestPasswordReset(email: string): Promise<{ message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('Error requesting password reset:', error);
      throw error;
    }
  }

  async validateResetToken(token: string): Promise<{ valid: boolean; email?: string; error?: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/auth/validate-reset-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      });

      const data = await response.json();

      // Even if response is not ok, we still want to return the data
      // since the backend returns { valid: false, error: "..." }
      return data;
    } catch (error) {
      console.error('Error validating reset token:', error);
      return { valid: false, error: 'Failed to validate token' };
    }
  }

  async resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    try {
      const response = await apiFetch(`${this.baseUrl}/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('Error resetting password:', error);
      throw error;
    }
  }
}

export const userApi = new UserApi();