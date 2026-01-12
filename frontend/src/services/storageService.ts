import { Preferences } from '@capacitor/preferences';
import { isNativePlatform } from '../utils/platform';

/**
 * Cross-platform storage service that uses Capacitor Preferences on native
 * and localStorage on web.
 */
export const storageService = {
  async set(key: string, value: string): Promise<void> {
    if (isNativePlatform()) {
      await Preferences.set({ key, value });
    } else {
      localStorage.setItem(key, value);
    }
  },

  async get(key: string): Promise<string | null> {
    if (isNativePlatform()) {
      const { value } = await Preferences.get({ key });
      return value;
    } else {
      return localStorage.getItem(key);
    }
  },

  async remove(key: string): Promise<void> {
    if (isNativePlatform()) {
      await Preferences.remove({ key });
    } else {
      localStorage.removeItem(key);
    }
  },

  async clear(): Promise<void> {
    if (isNativePlatform()) {
      await Preferences.clear();
    } else {
      localStorage.clear();
    }
  },
};

// Auth token helpers
const AUTH_TOKEN_KEY = 'auth_token';

export const getAuthToken = async (): Promise<string | null> => {
  return storageService.get(AUTH_TOKEN_KEY);
};

export const setAuthToken = async (token: string): Promise<void> => {
  return storageService.set(AUTH_TOKEN_KEY, token);
};

export const removeAuthToken = async (): Promise<void> => {
  return storageService.remove(AUTH_TOKEN_KEY);
};
