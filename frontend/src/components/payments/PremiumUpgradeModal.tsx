import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { paymentsApi, type PaymentIntent } from '../../services/paymentsApi';
import { isIOS, isWeb } from '../../utils/platform';
import { useAppleIap } from '../../hooks/useAppleIap';

interface PremiumUpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '');

// Stripe payment form for web users
const StripePaymentForm: React.FC<{
  onSuccess: () => void;
  onError: (error: string) => void;
}> = ({ onSuccess, onError }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements) {
      onError('Stripe has not loaded yet.');
      return;
    }

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      onError('Card element not found.');
      return;
    }

    setIsLoading(true);

    try {
      // Create payment intent
      const paymentIntent: PaymentIntent = await paymentsApi.createSubscriptionUpgrade();

      // Confirm payment with card
      const { error: stripeError, paymentIntent: confirmedPayment } = await stripe.confirmCardPayment(
        paymentIntent.client_secret,
        {
          payment_method: {
            card: cardElement,
          },
        }
      );

      if (stripeError) {
        onError(stripeError.message || 'Payment failed');
      } else if (confirmedPayment?.status === 'succeeded') {
        // Payment succeeded, confirm subscription on backend
        try {
          await paymentsApi.confirmSubscription();
          onSuccess();
        } catch (confirmError) {
          console.error('Failed to confirm subscription:', confirmError);
          // Payment succeeded but confirmation failed - still show success
          // The webhook should eventually update the subscription
          onSuccess();
        }
      } else {
        onError('Payment was not completed. Please try again.');
      }
    } catch (err) {
      console.error('Premium upgrade failed:', err);
      onError(err instanceof Error ? err.message : 'Upgrade failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="bg-gray-50 p-4 rounded-lg">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Card Details
        </label>
        <div className="bg-white p-3 border rounded-md">
          <CardElement
            options={{
              style: {
                base: {
                  fontSize: '16px',
                  color: '#374151',
                  '::placeholder': {
                    color: '#9CA3AF',
                  },
                },
              },
            }}
          />
        </div>
      </div>

      <Button
        type="submit"
        variant="primary"
        className="w-full"
        disabled={!stripe || isLoading}
      >
        {isLoading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></div>
            Processing...
          </>
        ) : (
          'Confirm Payment ($0.99/month)'
        )}
      </Button>
    </form>
  );
};

// Apple IAP payment form for iOS users
const ApplePaymentForm: React.FC<{
  onSuccess: () => void;
  onError: (error: string) => void;
}> = ({ onSuccess, onError }) => {
  const {
    products,
    isLoading,
    error: iapError,
    loadProducts,
    purchase,
    restorePurchases,
    clearError,
  } = useAppleIap();

  const [isRestoring, setIsRestoring] = useState(false);

  // Load products when component mounts
  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  // Handle IAP errors
  useEffect(() => {
    if (iapError) {
      onError(iapError);
      clearError();
    }
  }, [iapError, onError, clearError]);

  const handlePurchase = async () => {
    const productId = 'com.cookle.app.premium.monthly';
    const result = await purchase(productId);

    if (result) {
      onSuccess();
    }
    // If result is null, user cancelled or there was an error (already handled)
  };

  const handleRestore = async () => {
    setIsRestoring(true);
    try {
      const restored = await restorePurchases();
      if (restored) {
        onSuccess();
      } else {
        onError('No previous purchases found to restore.');
      }
    } finally {
      setIsRestoring(false);
    }
  };

  // Get the premium product for display
  const premiumProduct = products.find(p => p.id === 'com.cookle.app.premium.monthly');

  return (
    <div className="space-y-4">
      {/* Product info from App Store */}
      {premiumProduct && (
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-center">
            <p className="text-sm text-gray-600">{premiumProduct.description}</p>
            <p className="text-2xl font-bold text-indigo-600 mt-2">
              {premiumProduct.displayPrice}
              <span className="text-sm font-normal text-gray-600">/month</span>
            </p>
          </div>
        </div>
      )}

      {/* Purchase button */}
      <Button
        type="button"
        variant="primary"
        className="w-full"
        onClick={handlePurchase}
        disabled={isLoading || !premiumProduct}
      >
        {isLoading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></div>
            Processing...
          </>
        ) : (
          <>
            <svg className="w-5 h-5 mr-2 inline-block" fill="currentColor" viewBox="0 0 24 24">
              <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
            </svg>
            Subscribe with Apple
          </>
        )}
      </Button>

      {/* Restore purchases */}
      <button
        type="button"
        className="w-full text-sm text-indigo-600 hover:text-indigo-800 disabled:opacity-50"
        onClick={handleRestore}
        disabled={isRestoring || isLoading}
      >
        {isRestoring ? 'Restoring...' : 'Restore Previous Purchases'}
      </button>

      {/* Loading products indicator */}
      {isLoading && !premiumProduct && (
        <div className="text-center text-sm text-gray-500">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600 mx-auto mb-2"></div>
          Loading subscription options...
        </div>
      )}
    </div>
  );
};

export const PremiumUpgradeModal: React.FC<PremiumUpgradeModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [isLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<'overview' | 'payment' | 'processing' | 'success' | 'error'>('overview');

  // Determine which payment method to use based on platform
  const useApplePay = isIOS();
  const useStripePay = isWeb();

  const handlePaymentSuccess = () => {
    setStep('success');
    setTimeout(() => {
      onSuccess?.();
      onClose();
    }, 2000);
  };

  const handlePaymentError = (errorMessage: string) => {
    setError(errorMessage);
    setStep('error');
  };

  const handleUpgrade = () => {
    setError(null);
    setStep('payment');
  };

  const handleClose = () => {
    if (!isLoading) {
      setStep('overview');
      setError(null);
      onClose();
    }
  };

  const renderContent = () => {
    switch (step) {
      case 'overview':
        return (
          <div className="p-6">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Upgrade to Premium
              </h2>
              <p className="text-gray-600">
                Unlock unlimited recipe uploads and enhanced features
              </p>
            </div>

            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 mb-6">
              <div className="text-center mb-4">
                <div className="inline-block bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded-full mb-2">
                  Early Adopter Price
                </div>
                <div>
                  <span className="text-3xl font-bold text-indigo-600">$0.99</span>
                  <span className="text-gray-600 ml-2">/ month</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">Lock in this price forever</p>
              </div>

              <ul className="space-y-3 text-sm">
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span>Unlimited recipe uploads</span>
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span>Priority customer support</span>
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span>Sell your cookbooks on Cookle (coming)</span>
                </li>
              </ul>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            <div className="flex gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={handleClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={handleUpgrade}
                disabled={isLoading}
              >
                {useApplePay ? 'Continue' : 'Continue to Payment'}
              </Button>
            </div>
          </div>
        );

      case 'payment':
        return (
          <div className="p-6">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Complete Your Upgrade
              </h2>
              <p className="text-gray-600">
                {useApplePay
                  ? 'Subscribe using your Apple ID'
                  : 'Enter your payment details to upgrade to Premium'
                }
              </p>
              {!useApplePay && (
                <div className="mt-2">
                  <span className="inline-block bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded-full mb-1">
                    Early Adopter Price
                  </span>
                  <div>
                    <span className="text-xl font-bold text-indigo-600">$0.99</span>
                    <span className="text-gray-600 ml-1">/ month</span>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            {/* Render appropriate payment form based on platform */}
            {useApplePay ? (
              <ApplePaymentForm
                onSuccess={handlePaymentSuccess}
                onError={handlePaymentError}
              />
            ) : useStripePay ? (
              <Elements stripe={stripePromise}>
                <StripePaymentForm
                  onSuccess={handlePaymentSuccess}
                  onError={handlePaymentError}
                />
              </Elements>
            ) : (
              <div className="text-center text-gray-600">
                <p>Payment is not available on this platform.</p>
              </div>
            )}

            <div className="mt-4">
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => setStep('overview')}
                disabled={isLoading}
              >
                &larr; Back
              </Button>
            </div>

            {isLoading && (
              <div className="mt-4 text-center text-sm text-gray-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600 mx-auto mb-2"></div>
                Please wait while we process your payment...
              </div>
            )}
          </div>
        );

      case 'processing':
        return (
          <div className="p-6 text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Processing Payment
            </h3>
            <p className="text-gray-600">
              Please wait while we process your upgrade...
            </p>
          </div>
        );

      case 'success':
        return (
          <div className="p-6 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Welcome to Premium!
            </h3>
            <p className="text-gray-600">
              Your account has been upgraded successfully. You now have unlimited recipe uploads!
            </p>
          </div>
        );

      case 'error':
        return (
          <div className="p-6 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Upgrade Failed
            </h3>
            <p className="text-gray-600 mb-4">
              {error || 'Something went wrong with your upgrade. Please try again.'}
            </p>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={handleClose}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={() => setStep('overview')}
              >
                Try Again
              </Button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose}>
      {renderContent()}
    </Modal>
  );
};
