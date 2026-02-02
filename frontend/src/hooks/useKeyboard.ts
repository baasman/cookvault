import { useCallback, useEffect } from 'react';
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

/**
 * Hook to handle keyboard visibility and scroll focused inputs into view.
 * Call this once at the app level.
 */
export const useKeyboardScrollFix = () => {
  useEffect(() => {
    if (!isNativePlatform()) return;

    let cleanup: (() => void) | undefined;

    const setupListeners = async () => {
      try {
        // When keyboard shows, scroll the focused element into view
        const showListener = await Keyboard.addListener('keyboardWillShow', () => {
          const activeElement = document.activeElement as HTMLElement;
          if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
            // Add a small delay to let the keyboard animation start
            setTimeout(() => {
              activeElement.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
              });
            }, 100);
          }
        });

        cleanup = () => {
          showListener.remove();
        };
      } catch (error) {
        console.warn('Failed to set up keyboard listeners:', error);
      }
    };

    setupListeners();

    return () => {
      if (cleanup) {
        cleanup();
      }
    };
  }, []);
};
