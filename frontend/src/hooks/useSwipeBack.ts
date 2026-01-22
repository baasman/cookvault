import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { isIOS, isNativePlatform } from '../utils/platform';

interface SwipeState {
  isActive: boolean;
  startX: number;
  startY: number;
  currentX: number;
  progress: number; // 0 to 1
}

interface UseSwipeBackOptions {
  edgeWidth?: number; // Width of the edge detection zone (default: 25px)
  threshold?: number; // Minimum swipe distance to trigger back (default: 100px)
  maxDistance?: number; // Distance for full progress (default: 200px)
  enabled?: boolean;
}

export const useSwipeBack = (options: UseSwipeBackOptions = {}) => {
  const {
    edgeWidth = 25,
    threshold = 100,
    maxDistance = 200,
    enabled = true,
  } = options;

  const navigate = useNavigate();
  const location = useLocation();
  const [swipeState, setSwipeState] = useState<SwipeState>({
    isActive: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    progress: 0,
  });

  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);
  const isSwipingRef = useRef(false);

  // Don't enable on home page (nothing to go back to)
  const isHomePage = location.pathname === '/';
  const shouldEnable = enabled && (isIOS() || isNativePlatform()) && !isHomePage;

  const handleTouchStart = useCallback((e: TouchEvent) => {
    if (!shouldEnable) return;

    const touch = e.touches[0];
    const startX = touch.clientX;

    // Only start tracking if touch begins near the left edge
    if (startX <= edgeWidth) {
      touchStartRef.current = {
        x: startX,
        y: touch.clientY,
        time: Date.now(),
      };
      isSwipingRef.current = false;
    }
  }, [shouldEnable, edgeWidth]);

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!shouldEnable || !touchStartRef.current) return;

    const touch = e.touches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;

    // If vertical movement is greater than horizontal, cancel the swipe
    if (!isSwipingRef.current && Math.abs(deltaY) > Math.abs(deltaX)) {
      touchStartRef.current = null;
      return;
    }

    // Only proceed if swiping right (positive deltaX)
    if (deltaX > 10) {
      isSwipingRef.current = true;

      // Prevent default scrolling while swiping back
      e.preventDefault();

      const progress = Math.min(deltaX / maxDistance, 1);

      setSwipeState({
        isActive: true,
        startX: touchStartRef.current.x,
        startY: touchStartRef.current.y,
        currentX: touch.clientX,
        progress,
      });
    }
  }, [shouldEnable, maxDistance]);

  const handleTouchEnd = useCallback(() => {
    if (!shouldEnable || !touchStartRef.current) return;

    const wasActive = swipeState.isActive;
    const finalProgress = swipeState.progress;

    // Reset state
    touchStartRef.current = null;
    isSwipingRef.current = false;
    setSwipeState({
      isActive: false,
      startX: 0,
      startY: 0,
      currentX: 0,
      progress: 0,
    });

    // Navigate back if threshold was reached
    if (wasActive && finalProgress * maxDistance >= threshold) {
      navigate(-1);
    }
  }, [shouldEnable, swipeState, maxDistance, threshold, navigate]);

  useEffect(() => {
    if (!shouldEnable) return;

    // Use passive: false to allow preventDefault on touchmove
    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    document.addEventListener('touchmove', handleTouchMove, { passive: false });
    document.addEventListener('touchend', handleTouchEnd, { passive: true });
    document.addEventListener('touchcancel', handleTouchEnd, { passive: true });

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
      document.removeEventListener('touchcancel', handleTouchEnd);
    };
  }, [shouldEnable, handleTouchStart, handleTouchMove, handleTouchEnd]);

  return {
    isActive: swipeState.isActive,
    progress: swipeState.progress,
    translateX: swipeState.isActive ? swipeState.currentX - swipeState.startX : 0,
  };
};
