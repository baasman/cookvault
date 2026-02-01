import { Capacitor } from '@capacitor/core';

/**
 * Check if the app is running on a native platform (iOS or Android)
 */
export const isNativePlatform = (): boolean => {
  return Capacitor.isNativePlatform();
};

/**
 * Check if the app is running on iOS
 */
export const isIOS = (): boolean => {
  return Capacitor.getPlatform() === 'ios';
};

/**
 * Check if the app is running on Android
 */
export const isAndroid = (): boolean => {
  return Capacitor.getPlatform() === 'android';
};

/**
 * Check if the app is running in a web browser
 */
export const isWeb = (): boolean => {
  return Capacitor.getPlatform() === 'web';
};

/**
 * Get the current platform
 */
export const getPlatform = (): 'ios' | 'android' | 'web' => {
  return Capacitor.getPlatform() as 'ios' | 'android' | 'web';
};

/**
 * Open an external URL or mailto link.
 * On native platforms, uses the system browser/mail app.
 * On web, uses window.open or location.href.
 */
export const openExternalUrl = async (url: string): Promise<void> => {
  if (url.startsWith('mailto:')) {
    // For mailto links, use window.location to trigger native mail handler
    window.location.href = url;
  } else if (isNativePlatform()) {
    // For regular URLs on native, use the Browser plugin
    const { Browser } = await import('@capacitor/browser');
    await Browser.open({ url });
  } else {
    // On web, use window.open
    window.open(url, '_blank');
  }
};
