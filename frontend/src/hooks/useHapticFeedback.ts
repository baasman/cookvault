import { useCallback } from 'react';
import {
  lightImpact,
  mediumImpact,
  heavyImpact,
  selectionChanged,
  notifySuccess,
  notifyWarning,
  notifyError,
} from '../utils/haptics';

/**
 * Hook to provide haptic feedback utilities
 * All methods are no-ops on non-native platforms
 */
export const useHapticFeedback = () => {
  const triggerLight = useCallback(() => {
    lightImpact();
  }, []);

  const triggerMedium = useCallback(() => {
    mediumImpact();
  }, []);

  const triggerHeavy = useCallback(() => {
    heavyImpact();
  }, []);

  const triggerSelection = useCallback(() => {
    selectionChanged();
  }, []);

  const triggerSuccess = useCallback(() => {
    notifySuccess();
  }, []);

  const triggerWarning = useCallback(() => {
    notifyWarning();
  }, []);

  const triggerError = useCallback(() => {
    notifyError();
  }, []);

  return {
    triggerLight,
    triggerMedium,
    triggerHeavy,
    triggerSelection,
    triggerSuccess,
    triggerWarning,
    triggerError,
  };
};
