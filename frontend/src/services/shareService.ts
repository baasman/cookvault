import { Share } from '@capacitor/share';
import type { ShareResult } from '@capacitor/share';
import { isNativePlatform } from '../utils/platform';
import type { Recipe } from '../types';

/**
 * Share a recipe using the native share sheet or Web Share API
 */
export const shareRecipe = async (recipe: Recipe): Promise<ShareResult | null> => {
  const shareUrl = `https://cookle.food/recipes/${recipe.id}`;
  const shareText = recipe.description
    ? `${recipe.title} - ${recipe.description}`
    : recipe.title;

  if (isNativePlatform()) {
    try {
      return await Share.share({
        title: recipe.title,
        text: shareText,
        url: shareUrl,
        dialogTitle: 'Share this recipe',
      });
    } catch (error) {
      console.error('Native share failed:', error);
      throw error;
    }
  } else {
    // Web fallback - use Web Share API if available
    if (navigator.share) {
      try {
        await navigator.share({
          title: recipe.title,
          text: shareText,
          url: shareUrl,
        });
        return { activityType: 'web-share' };
      } catch (error) {
        // User cancelled or error
        console.log('Web share cancelled or failed:', error);
      }
    }

    // Final fallback: copy to clipboard
    try {
      await navigator.clipboard.writeText(shareUrl);
      return { activityType: 'clipboard' };
    } catch (error) {
      console.error('Clipboard copy failed:', error);
      return null;
    }
  }
};

/**
 * Check if native sharing is available
 */
export const canShare = (): boolean => {
  if (isNativePlatform()) {
    return true;
  }
  return typeof navigator.share === 'function' || typeof navigator.clipboard?.writeText === 'function';
};

/**
 * Share a generic URL with title and text
 */
export const shareUrl = async (
  url: string,
  title?: string,
  text?: string
): Promise<ShareResult | null> => {
  if (isNativePlatform()) {
    try {
      return await Share.share({
        title: title || 'Check this out',
        text: text,
        url,
        dialogTitle: 'Share',
      });
    } catch (error) {
      console.error('Native share failed:', error);
      throw error;
    }
  } else {
    if (navigator.share) {
      try {
        await navigator.share({
          title: title || 'Check this out',
          text,
          url,
        });
        return { activityType: 'web-share' };
      } catch (error) {
        console.log('Web share cancelled or failed:', error);
      }
    }

    try {
      await navigator.clipboard.writeText(url);
      return { activityType: 'clipboard' };
    } catch (error) {
      console.error('Clipboard copy failed:', error);
      return null;
    }
  }
};
