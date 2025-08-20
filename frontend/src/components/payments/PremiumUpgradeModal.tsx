import React, { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { paymentsApi, type PaymentIntent } from '../../services/paymentsApi';

interface PremiumUpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '');

const PaymentForm: React.FC<{
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
      const { error: stripeError } = await stripe.confirmCardPayment(
        paymentIntent.client_secret,
        {
          payment_method: {
            card: cardElement,
          },
        }
      );

      if (stripeError) {
        onError(stripeError.message || 'Payment failed');
      } else {
        onSuccess();
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
        <p className="text-xs text-gray-500 mt-1">
          Use test card: 4242 4242 4242 4242, any expiry/CVC
        </p>
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
          'Confirm Payment ($2.99/month)'
        )}
      </Button>
    </form>
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
                <span className="text-3xl font-bold text-indigo-600">$2.99</span>
                <span className="text-gray-600 ml-2">/ month</span>
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
                  <span>Advanced recipe organization</span>
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span>Enhanced recipe sharing features</span>
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span>Early access to new features</span>
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
                Continue to Payment
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
                Enter your payment details to upgrade to Premium
              </p>
              <div className="mt-2">
                <span className="text-xl font-bold text-indigo-600">$2.99</span>
                <span className="text-gray-600 ml-1">/ month</span>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            <Elements stripe={stripePromise}>
              <PaymentForm
                onSuccess={handlePaymentSuccess}
                onError={handlePaymentError}
              />
            </Elements>

            <div className="mt-4">
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => setStep('overview')}
                disabled={isLoading}
              >
                ← Back
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