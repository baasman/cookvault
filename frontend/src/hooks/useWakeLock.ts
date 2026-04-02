import { useState, useEffect, useRef, useCallback } from 'react';

export function useWakeLock(enabled: boolean): { isSupported: boolean; isActive: boolean } {
  const [isActive, setIsActive] = useState(false);
  const wakeLockRef = useRef<WakeLockSentinel | null>(null);
  const isSupported = 'wakeLock' in navigator;

  const requestWakeLock = useCallback(async () => {
    if (!isSupported || !enabled) return;

    try {
      wakeLockRef.current = await navigator.wakeLock.request('screen');
      setIsActive(true);

      wakeLockRef.current.addEventListener('release', () => {
        setIsActive(false);
      });
    } catch (error) {
      console.error('Wake lock request failed:', error);
      setIsActive(false);
    }
  }, [isSupported, enabled]);

  const releaseWakeLock = useCallback(async () => {
    if (wakeLockRef.current) {
      try {
        await wakeLockRef.current.release();
      } catch (error) {
        console.error('Wake lock release failed:', error);
      }
      wakeLockRef.current = null;
      setIsActive(false);
    }
  }, []);

  // Request/release based on enabled flag
  useEffect(() => {
    if (enabled) {
      requestWakeLock();
    } else {
      releaseWakeLock();
    }

    return () => {
      releaseWakeLock();
    };
  }, [enabled, requestWakeLock, releaseWakeLock]);

  // Re-acquire when page becomes visible again (wake lock auto-releases on tab hide)
  useEffect(() => {
    if (!enabled) return;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && enabled) {
        requestWakeLock();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [enabled, requestWakeLock]);

  return { isSupported, isActive };
}
