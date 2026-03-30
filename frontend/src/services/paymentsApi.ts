import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';

const API_BASE_URL = getApiUrl();

// Types
export interface Subscription {
  id: number;
  user_id: number;
  tier: 'free' | 'premium';
  status: string;
  is_premium: boolean;
  payment_provider: 'stripe' | 'apple' | null;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  canceled_at: string | null;
  monthly_upload_count: number;
  remaining_uploads: number;
  can_upload: boolean;
  created_at: string;
  updated_at: string;
  // Apple IAP fields
  apple_expires_date: string | null;
}

export interface Payment {
  id: number;
  user_id: number;
  subscription_id: number | null;
  cookbook_id: number | null;
  payment_type: 'subscription' | 'cookbook';
  status: 'pending' | 'succeeded' | 'failed' | 'canceled' | 'refunded';
  amount: number;
  currency: string;
  description: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface CookbookPurchase {
  id: number;
  user_id: number;
  cookbook_id: number;
  payment_id: number;
  purchase_price: number;
  access_granted: boolean;
  has_access: boolean;
  purchase_date: string;
  access_revoked_at: string | null;
  cookbook: any; // Full cookbook object
}

export interface PaymentIntent {
  client_secret: string;
  payment_intent_id?: string;
  subscription_id?: string;
  amount: number;
  currency: string;
  cookbook?: any;
  status?: string;
}

export interface PaymentMethod {
  id: string;
  card: {
    brand: string;
    last4: string;
    exp_month: number;
    exp_year: number;
  };
}

class PaymentsApi {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}/payments${endpoint}`;
    
    const defaultOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    };

    const response = await apiFetch(url, { ...defaultOptions, ...options });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    return data;
  }

  // Subscription Management
  async createSubscriptionUpgrade(): Promise<PaymentIntent> {
    const response = await this.request<{
      success: boolean;
      subscription?: {
        subscription_id: string;
        client_secret: string;
        status: string;
        amount: number;
        currency: string;
      };
      client_secret?: string;
      payment_intent?: PaymentIntent;
    }>('/subscription/upgrade', {
      method: 'POST',
    });

    if (!response.success) {
      throw new Error('Failed to create subscription upgrade');
    }

    // Handle new subscription-based response format
    if (response.subscription) {
      return {
        client_secret: response.subscription.client_secret || response.client_secret || '',
        subscription_id: response.subscription.subscription_id,
        amount: response.subscription.amount,
        currency: response.subscription.currency,
        status: response.subscription.status,
      };
    }

    // Fallback for legacy payment_intent format
    if (response.payment_intent) {
      return response.payment_intent;
    }

    throw new Error('Invalid response format from subscription upgrade');
  }

  async cancelSubscription(): Promise<void> {
    const response = await this.request<{ success: boolean; message: string }>('/subscription/cancel', {
      method: 'POST',
    });

    if (!response.success) {
      throw new Error('Failed to cancel subscription');
    }
  }

  async confirmSubscription(): Promise<Subscription> {
    const response = await this.request<{ success: boolean; subscription: Subscription; message?: string }>('/subscription/confirm', {
      method: 'POST',
    });

    if (!response.success) {
      throw new Error(response.message || 'Failed to confirm subscription');
    }

    return response.subscription;
  }

  async getUserSubscription(): Promise<Subscription> {
    const response = await this.request<{ success: boolean; subscription: Subscription }>('/user/subscription');
    
    if (!response.success) {
      throw new Error('Failed to get user subscription');
    }
    
    return response.subscription;
  }

  // Cookbook Purchases
  async createCookbookPurchase(cookbookId: number): Promise<PaymentIntent> {
    const response = await this.request<{ success: boolean; payment_intent: PaymentIntent }>(`/cookbook/${cookbookId}/purchase`, {
      method: 'POST',
    });
    
    if (!response.success) {
      throw new Error('Failed to create cookbook purchase');
    }
    
    return response.payment_intent;
  }

  // Payment History
  async getUserPayments(page: number = 1, perPage: number = 20): Promise<{
    payments: Payment[];
    pagination: {
      page: number;
      per_page: number;
      total: number;
      pages: number;
      has_next: boolean;
      has_prev: boolean;
    };
  }> {
    const response = await this.request<{
      success: boolean;
      payments: Payment[];
      pagination: any;
    }>(`/user/payments?page=${page}&per_page=${perPage}`);
    
    if (!response.success) {
      throw new Error('Failed to get user payments');
    }
    
    return {
      payments: response.payments,
      pagination: response.pagination,
    };
  }

  // Purchase History
  async getUserPurchases(): Promise<CookbookPurchase[]> {
    const response = await this.request<{ success: boolean; purchases: CookbookPurchase[] }>('/user/purchases');
    
    if (!response.success) {
      throw new Error('Failed to get user purchases');
    }
    
    return response.purchases;
  }

  // Payment Methods
  async getUserPaymentMethods(): Promise<PaymentMethod[]> {
    const response = await this.request<{ success: boolean; payment_methods: PaymentMethod[] }>('/user/payment-methods');
    
    if (!response.success) {
      throw new Error('Failed to get user payment methods');
    }
    
    return response.payment_methods;
  }

  // Payment Status
  async getPaymentStatus(paymentIntentId: string): Promise<Payment> {
    const response = await this.request<{ success: boolean; payment: Payment }>(`/payment/${paymentIntentId}/status`);
    
    if (!response.success) {
      throw new Error('Failed to get payment status');
    }
    
    return response.payment;
  }
}

export const paymentsApi = new PaymentsApi();