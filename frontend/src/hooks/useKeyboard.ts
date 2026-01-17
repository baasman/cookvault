import { useCallback } from 'react';
import { Keyboard } from '@capacitor/keyboard';
import { isNativePlatform } from '../utils/platform';

export const useKeyboard = () => {
  const hideKeyboard = useCallback(async () => {
    if (isNativePlatform()) {
      try {
        await Keyboard.hide();
      } catch (error) {
        console.warn('Failed to hide keyboard:', error);
      }
    }
  }, []);

  return { hideKeyboard };
};

export const hideKeyboard = async () => {
  if (isNativePlatform()) {
    try {
      await Keyboard.hide();
    } catch (error) {
      console.warn('Failed to hide keyboard:', error);
    }
  }
};
