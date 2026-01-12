import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import type { Photo } from '@capacitor/camera';
import { isNativePlatform } from '../utils/platform';

export interface CapturedImage {
  dataUrl?: string;
  blob?: Blob;
  file?: File;
}

/**
 * Capture a photo using the native camera or photo library
 * Returns null on web platform (use file input instead)
 */
export const captureRecipePhoto = async (): Promise<CapturedImage | null> => {
  if (!isNativePlatform()) {
    // On web, return null to indicate file input should be used
    return null;
  }

  try {
    const photo: Photo = await Camera.getPhoto({
      quality: 85,
      allowEditing: true,
      resultType: CameraResultType.DataUrl,
      source: CameraSource.Prompt, // Let user choose camera or gallery
      correctOrientation: true,
      width: 1200,
      height: 1200,
    });

    if (photo.dataUrl) {
      // Convert data URL to Blob for upload
      const response = await fetch(photo.dataUrl);
      const blob = await response.blob();
      const file = new File([blob], `recipe-${Date.now()}.${photo.format || 'jpeg'}`, {
        type: `image/${photo.format || 'jpeg'}`,
      });

      return {
        dataUrl: photo.dataUrl,
        blob,
        file,
      };
    }

    return null;
  } catch (error) {
    console.error('Camera capture failed:', error);
    throw error;
  }
};

/**
 * Request camera and photo library permissions
 */
export const requestCameraPermissions = async (): Promise<boolean> => {
  if (!isNativePlatform()) {
    return true; // Web doesn't need explicit permissions
  }

  try {
    const permissions = await Camera.requestPermissions();
    return permissions.camera === 'granted' && permissions.photos === 'granted';
  } catch (error) {
    console.error('Failed to request camera permissions:', error);
    return false;
  }
};

/**
 * Check if camera permissions are granted
 */
export const checkCameraPermissions = async (): Promise<boolean> => {
  if (!isNativePlatform()) {
    return true;
  }

  try {
    const permissions = await Camera.checkPermissions();
    return permissions.camera === 'granted' && permissions.photos === 'granted';
  } catch (error) {
    console.error('Failed to check camera permissions:', error);
    return false;
  }
};
