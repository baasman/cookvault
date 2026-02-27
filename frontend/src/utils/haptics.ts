import { Haptics, ImpactStyle, NotificationType } from '@capacitor/haptics';
import { isNativePlatform } from './platform';

/**
 * Trigger a light impact haptic feedback
 * Good for UI element interactions like button taps
 */
export const lightImpact = async (): Promise<void> => {
  if (!isNativePlatform()) return;
  try {
    await Haptics.impact({ style: ImpactStyle.Light });
  } catch (error) {
    console.error('Haptic feedback failed:', error);
  }
};

/**
 * Trigger a medium impact haptic feedback
 * Good for confirming actions or selections
 */
export const mediumImpact = async (): Promise<void> => {
  if (!isNativePlatform()) return;
  try {
    await Haptics.impact({ style: ImpactStyle.Medium });
  } catch (error) {
    console.error('Haptic feedback failed:', error);
  }
};

/**
 * Trigger a heavy impact haptic feedback
 * Good for significant actions or errors
 */
export const heavyImpact = async (): Promise<void> => {
  if (!isNativePlatform()) return;
  try {
    await Haptics.impact({ style: ImpactStyle.Heavy });
  } catch (error) {
    console.error('Haptic feedback failed:', error);
  }
};

/**
 * Trigger a selection changed haptic feedback
 * Good for picker/selection changes
 */
export const selectionChanged = async (): Promise<void> => {
  if (!isNativePlatform()) return;
  try {
    await Haptics.selectionChanged();
  } catch (error) {
    console.error('Haptic feedback failed:', error);
  }
};

/**
 * Trigger a success notification haptic
 */
export const notifySuccess = async (): Promise<void> => {
  if (!isNativePlatform()) return;
  try {
    await Haptics.notification({ type: NotificationType.Success });
  } catch (error) {
    console.error('Haptic feedback failed:', error);
  }
};

/**
 * Trigger a warning notification haptic
 */
export const notifyWarning = async (): Promise<void> => {
  if (!isNativePlatform()) return;
  try {
    await Haptics.notification({ type: NotificationType.Warning });
  } catch (error) {
    console.error('Haptic feedback failed:', error);
  }
};

/**
 * Trigger an error notification haptic
 */
export const notifyError = async (): Promise<void> => {
  if (!isNativePlatform()) return;
  try {
    await Haptics.notification({ type: NotificationType.Error });
  } catch (error) {
    console.error('Haptic feedback failed:', error);
  }
};
