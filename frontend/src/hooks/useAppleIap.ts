import { useState, useCallback, useEffect } from 'react';
import { appleIapService } from '../services/appleIapService';
import type { AppleProduct, PurchaseResult } from '../services/appleIapService';
import { isIOS } from '../utils/platform';
import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';

const API_BASE_URL = getApiUrl();

interface UseAppleIapReturn {
  /** Available products from the App Store */
  products: AppleProduct[];
  /** Loading state for IAP operations */
  isLoading: boolean;
  /** Error message if any operation failed */
  error: string | null;
  /** Whether Apple IAP is available (iOS only) */
  isAvailable: boolean;
  /** Load products from the App Store */
  loadProducts: () => Promise<void>;
  /** Purchase a product by ID */
  purchase: (productId: string) => Promise<PurchaseResult | null>;
  /** Restore previous purchases */
  restorePurchases: () => Promise<boolean>;
  /** Validate a transaction with the backend */
  validateWithBackend: (jwsTransaction: string) => Promise<boolean>;
  /** Check current subscription status */
  checkSubscription: () => Promise<boolean>;
  /** Clear any error state */
  clearError: () => void;
}

/**
 * Hook for handling Apple In-App Purchases
 *
 * Usage:
 * ```tsx
 * const { products, isLoading, error, loadProducts, purchase } = useAppleIap();
 *
 * useEffect(() => {
 *   loadProducts();
 * }, [loadProducts]);
 *
 * const handlePurchase = async () => {
 *   const result = await purchase('com.cookle.app.premium.monthly');
 *   if (result) {
 *     // Purchase successful
 *   }
 * };
 * ```
 */
export const useAppleIap = (): UseAppleIapReturn => {
  const [products, setProducts] = useState<AppleProduct[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAvailable, setIsAvailable] = useState(false);

  // Check availability on mount
  useEffect(() => {
    const checkAvailability = async () => {
      const available = isIOS();
      setIsAvailable(available);
    };
    checkAvailability();
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Load available products from the App Store
   */
  const loadProducts = useCallback(async () => {
    if (!isIOS()) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const fetchedProducts = await appleIapService.getProducts();
      setProducts(fetchedProducts);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load products';
      setError(message);
      console.error('Failed to load Apple products:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Validate a JWS transaction with our backend
   */
  const validateWithBackend = useCallback(async (jwsTransaction: string): Promise<boolean> => {
    try {
      const response = await apiFetch(`${API_BASE_URL}/apple/validate-receipt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ jwsTransaction }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Validation failed' }));
        throw new Error(errorData.error || 'Validation failed');
      }

      const data = await response.json();
      return data.success === true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Validation failed';
      setError(message);
      console.error('Backend validation failed:', err);
      return false;
    }
  }, []);

  /**
   * Purchase a product by ID
   */
  const purchase = useCallback(async (productId: string): Promise<PurchaseResult | null> => {
    if (!isIOS()) {
      setError('Apple IAP is only available on iOS');
      return null;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Perform the purchase via StoreKit
      const result = await appleIapService.purchase(productId);

      // Validate the transaction with our backend
      if (result.jwsRepresentation) {
        const validated = await validateWithBackend(result.jwsRepresentation);
        if (!validated) {
          // Transaction was successful but backend validation failed
          // This is rare but we should still return the result
          // The backend webhook will eventually sync the subscription
          console.warn('Purchase successful but backend validation failed');
        }
      }

      return result;
    } catch (err) {
      // Handle specific StoreKit errors
      const message = err instanceof Error ? err.message : 'Purchase failed';

      // Check for user cancellation - don't show as error
      if (message.includes('USER_CANCELLED') || message.includes('cancelled')) {
        // User cancelled, just return null without error
        return null;
      }

      setError(message);
      console.error('Apple purchase failed:', err);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [validateWithBackend]);

  /**
   * Restore previous purchases
   */
  const restorePurchases = useCallback(async (): Promise<boolean> => {
    if (!isIOS()) {
      setError('Apple IAP is only available on iOS');
      return false;
    }

    setIsLoading(true);
    setError(null);

    try {
      const transactions = await appleIapService.restorePurchases();

      if (transactions.length === 0) {
        // No previous purchases found
        return false;
      }

      // Validate each transaction with the backend via the restore endpoint
      const response = await apiFetch(`${API_BASE_URL}/apple/restore`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          transactions: transactions.map(tx => ({
            jwsRepresentation: tx.jwsRepresentation,
          })),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Restore failed' }));
        throw new Error(errorData.error || 'Restore failed');
      }

      const data = await response.json();
      return data.success && data.restored_count > 0;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Restore failed';
      setError(message);
      console.error('Restore purchases failed:', err);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Check current subscription status
   */
  const checkSubscription = useCallback(async (): Promise<boolean> => {
    if (!isIOS()) {
      return false;
    }

    try {
      const status = await appleIapService.getActiveSubscription();
      return status.hasActiveSubscription;
    } catch (err) {
      console.error('Failed to check subscription:', err);
      return false;
    }
  }, []);

  return {
    products,
    isLoading,
    error,
    isAvailable,
    loadProducts,
    purchase,
    restorePurchases,
    validateWithBackend,
    checkSubscription,
    clearError,
  };
};
