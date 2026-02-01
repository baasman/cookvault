import { useState, useEffect, useCallback } from 'react';
import { Network, type ConnectionStatus } from '@capacitor/network';
import { isNativePlatform } from '../utils/platform';

interface NetworkState {
  isOnline: boolean;
  connectionType: string | null;
}

/**
 * Hook to track network connectivity status.
 * Uses Capacitor Network plugin on native platforms, falls back to navigator.onLine on web.
 */
export const useNetworkStatus = (): NetworkState => {
  const [networkState, setNetworkState] = useState<NetworkState>({
    isOnline: true,
    connectionType: null,
  });

  const updateNetworkStatus = useCallback((status: ConnectionStatus) => {
    setNetworkState({
      isOnline: status.connected,
      connectionType: status.connectionType,
    });
  }, []);

  useEffect(() => {
    let listenerHandle: { remove: () => void } | null = null;

    const initializeNetworkStatus = async () => {
      if (isNativePlatform()) {
        // Native platform: use Capacitor Network plugin
        try {
          // Get initial status
          const status = await Network.getStatus();
          updateNetworkStatus(status);

          // Listen for changes
          listenerHandle = await Network.addListener(
            'networkStatusChange',
            updateNetworkStatus
          );
        } catch (error) {
          console.error('Failed to initialize network status:', error);
          // Fallback to assuming online
          setNetworkState({ isOnline: true, connectionType: null });
        }
      } else {
        // Web platform: use navigator.onLine
        setNetworkState({
          isOnline: navigator.onLine,
          connectionType: null,
        });

        const handleOnline = () => {
          setNetworkState({ isOnline: true, connectionType: null });
        };

        const handleOffline = () => {
          setNetworkState({ isOnline: false, connectionType: null });
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        // Store cleanup for web listeners
        listenerHandle = {
          remove: () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
          },
        };
      }
    };

    initializeNetworkStatus();

    return () => {
      if (listenerHandle) {
        listenerHandle.remove();
      }
    };
  }, [updateNetworkStatus]);

  return networkState;
};

export default useNetworkStatus;
