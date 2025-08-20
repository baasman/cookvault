import React, { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Button } from '../ui/Button';
import { BetaModeRestrictionModal } from '../ui/BetaModeRestrictionModal';
import { useBetaModeRestriction } from '../../hooks/useBetaModeRestriction';
import { paymentsApi, type PaymentIntent } from '../../services/paymentsApi';

interface CookbookPurchaseButtonProps {
  cookbook: {
    id: number;
    title: string;
    price: number;
    is_purchasable: boolean;
    has_purchased?: boolean;
    is_available_for_purchase?: boolean;
  };
  onPurchaseSuccess?: () => void;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '');

export const CookbookPurchaseButton: React.FC<CookbookPurchaseButtonProps> = ({
  cookbook,
  onPurchaseSuccess,
  className = '',
  size = 'md',
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Beta mode restriction hook
  const { checkBetaRestriction, betaModalState, closeBetaModal } = useBetaModeRestriction();

  const handlePurchase = async () => {
    // Check beta restriction first
    if (checkBetaRestriction('cookbook', { 
      cookbookTitle: cookbook.title, 
      price: cookbook.price 
    })) {
      return; // Beta modal will be shown by hook
    }
    
    try {
      setIsLoading(true);
      setError(null);

      // Create payment intent
      const paymentIntent: PaymentIntent = await paymentsApi.createCookbookPurchase(cookbook.id);

      // Load Stripe
      const stripe = await stripePromise;
      if (!stripe) {
        throw new Error('Stripe failed to load');
      }

      // Confirm payment
      const { error: stripeError } = await stripe.confirmPayment({
        clientSecret: paymentIntent.client_secret,
        confirmParams: {
          return_url: `${window.location.origin}/cookbooks/${cookbook.id}/purchase-success`,
        },
        redirect: 'if_required',
      });

      if (stripeError) {
        throw new Error(stripeError.message || 'Payment failed');
      }

      // Payment succeeded
      onPurchaseSuccess?.();

    } catch (err) {
      console.error('Cookbook purchase failed:', err);
      setError(err instanceof Error ? err.message : 'Purchase failed');
    } finally {
      setIsLoading(false);
    }
  };

  // Don't show button if cookbook is not purchasable
  if (!cookbook.is_purchasable || cookbook.price <= 0) {
    return null;
  }

  // Show "Already Purchased" if user has purchased
  if (cookbook.has_purchased) {
    return (
      <Button
        variant="secondary"
        size={size}
        className={`cursor-default ${className}`}
        disabled
      >
        ✓ Purchased
      </Button>
    );
  }

  // Show "Not Available" if not available for purchase
  if (cookbook.is_available_for_purchase === false) {
    return (
      <Button
        variant="secondary"
        size={size}
        className={`cursor-default ${className}`}
        disabled
      >
        Not Available
      </Button>
    );
  }

  return (
    <div className={className}>
      <Button
        variant="primary"
        size={size}
        onClick={handlePurchase}
        disabled={isLoading}
        className="w-full"
      >
        {isLoading ? (
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
            Processing...
          </div>
        ) : (
          <div className="flex items-center justify-center">
            <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4zm14 5H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM5 12a1 1 0 011-1h1a1 1 0 110 2H6a1 1 0 01-1-1zm5 0a1 1 0 011-1h1a1 1 0 110 2h-1a1 1 0 01-1-1z" clipRule="evenodd" />
            </svg>
            Purchase for ${cookbook.price.toFixed(2)}
          </div>
        )}
      </Button>
      
      {error && (
        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}
      
      {/* Beta Mode Restriction Modal */}
      <BetaModeRestrictionModal
        isOpen={betaModalState.isOpen}
        onClose={closeBetaModal}
        feature={betaModalState.feature}
        cookbookTitle={betaModalState.cookbookTitle}
        price={betaModalState.price}
      />
    </div>
  );
};