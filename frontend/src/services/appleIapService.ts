import { Capacitor, registerPlugin } from '@capacitor/core';

/**
 * Product information from the App Store
 */
export interface AppleProduct {
  id: string;
  displayName: string;
  description: string;
  price: string;
  displayPrice: string;
}

/**
 * Result of a successful purchase
 */
export interface PurchaseResult {
  success: boolean;
  transactionId: string;
  originalTransactionId: string;
  productId: string;
  jwsRepresentation: string;
}

/**
 * Transaction information from restore purchases
 */
export interface AppleTransaction {
  transactionId: string;
  originalTransactionId: string;
  productId: string;
  jwsRepresentation: string;
}

/**
 * Current subscription status
 */
export interface SubscriptionStatus {
  hasActiveSubscription: boolean;
  productId?: string;
  expirationDate?: string;
  originalTransactionId?: string;
  jwsRepresentation?: string;
}

/**
 * StoreKit plugin interface matching our native implementation
 */
interface StoreKitPlugin {
  getProducts(): Promise<{ products: AppleProduct[] }>;
  purchase(options: { productId: string }): Promise<PurchaseResult>;
  restorePurchases(): Promise<{ transactions: AppleTransaction[] }>;
  getActiveSubscription(): Promise<SubscriptionStatus>;
}

// Register the native plugin
const StoreKit = registerPlugin<StoreKitPlugin>('StoreKit');

/**
 * Service for handling Apple In-App Purchases via StoreKit 2
 */
class AppleIapService {
  /**
   * Check if Apple IAP is available (iOS native platform only)
   */
  async isAvailable(): Promise<boolean> {
    return Capacitor.getPlatform() === 'ios';
  }

  /**
   * Fetch available products from the App Store
   */
  async getProducts(): Promise<AppleProduct[]> {
    if (!await this.isAvailable()) {
      throw new Error('Apple IAP is only available on iOS');
    }
    const result = await StoreKit.getProducts();
    return result.products;
  }

  /**
   * Purchase a product by ID
   * @param productId The product ID to purchase
   * @returns Purchase result with transaction details
   */
  async purchase(productId: string): Promise<PurchaseResult> {
    if (!await this.isAvailable()) {
      throw new Error('Apple IAP is only available on iOS');
    }
    return await StoreKit.purchase({ productId });
  }

  /**
   * Restore previous purchases
   * Useful when user reinstalls or switches devices
   */
  async restorePurchases(): Promise<AppleTransaction[]> {
    if (!await this.isAvailable()) {
      throw new Error('Apple IAP is only available on iOS');
    }
    const result = await StoreKit.restorePurchases();
    return result.transactions;
  }

  /**
   * Get the currently active subscription
   */
  async getActiveSubscription(): Promise<SubscriptionStatus> {
    if (!await this.isAvailable()) {
      throw new Error('Apple IAP is only available on iOS');
    }
    return await StoreKit.getActiveSubscription();
  }
}

// Export singleton instance
export const appleIapService = new AppleIapService();
