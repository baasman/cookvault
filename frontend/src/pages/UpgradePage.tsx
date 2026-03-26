import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/Button';
import { paymentsApi, type PaymentIntent, type Subscription } from '../services/paymentsApi';

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

const UpgradePage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoadingSubscription, setIsLoadingSubscription] = useState(true);
  const [step, setStep] = useState<'overview' | 'payment' | 'success' | 'error'>('overview');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSubscription = async () => {
      if (!isAuthenticated) {
        setIsLoadingSubscription(false);
        return;
      }
      try {
        const subData = await paymentsApi.getUserSubscription();
        setSubscription(subData);
        // If already premium, show success state
        if (subData.is_premium) {
          setStep('success');
        }
      } catch (err) {
        console.error('Failed to load subscription:', err);
      } finally {
        setIsLoadingSubscription(false);
      }
    };
    loadSubscription();
  }, [isAuthenticated]);

  const handlePaymentSuccess = () => {
    setStep('success');
  };

  const handlePaymentError = (errorMessage: string) => {
    setError(errorMessage);
    setStep('error');
  };

  // Not authenticated - prompt to login
  if (!isAuthenticated) {
    return (
      <div className="max-w-lg mx-auto py-12 px-4">
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center" style={{ borderColor: '#e8d7cf' }}>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Upgrade to Premium
          </h1>
          <p className="text-gray-600 mb-6">
            Please log in to upgrade your account to Premium.
          </p>
          <div className="flex gap-3 justify-center">
            <Button onClick={() => navigate('/login')} variant="primary">
              Log In
            </Button>
            <Button onClick={() => navigate('/register')} variant="secondary">
              Create Account
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Loading subscription
  if (isLoadingSubscription) {
    return (
      <div className="max-w-lg mx-auto py-12 px-4">
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center" style={{ borderColor: '#e8d7cf' }}>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{ borderColor: '#f15f1c' }}></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Already premium
  if (step === 'success' || subscription?.is_premium) {
    return (
      <div className="max-w-lg mx-auto py-12 px-4">
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center" style={{ borderColor: '#e8d7cf' }}>
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {step === 'success' ? 'Welcome to Premium!' : 'You\'re Already Premium!'}
          </h1>
          <p className="text-gray-600 mb-6">
            {step === 'success'
              ? 'Your account has been upgraded successfully. You now have unlimited recipe uploads!'
              : 'Your account already has Premium features enabled. Enjoy unlimited recipe uploads!'
            }
          </p>
          <Button onClick={() => navigate('/upload')} variant="primary">
            Upload a Recipe
          </Button>
        </div>
      </div>
    );
  }

  // Error state
  if (step === 'error') {
    return (
      <div className="max-w-lg mx-auto py-12 px-4">
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center" style={{ borderColor: '#e8d7cf' }}>
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Upgrade Failed
          </h1>
          <p className="text-gray-600 mb-6">
            {error || 'Something went wrong with your upgrade. Please try again.'}
          </p>
          <div className="flex gap-3 justify-center">
            <Button onClick={() => navigate('/')} variant="secondary">
              Go Home
            </Button>
            <Button onClick={() => setStep('overview')} variant="primary">
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Overview / Payment flow
  return (
    <div className="max-w-lg mx-auto py-12 px-4">
      <div className="bg-white rounded-xl shadow-sm border p-8" style={{ borderColor: '#e8d7cf' }}>
        {step === 'overview' ? (
          <>
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Upgrade to Premium
              </h1>
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

            {/* Current usage info */}
            {subscription && (
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Current plan:</span> Free
                </p>
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Uploads remaining:</span> {subscription.remaining_uploads} of {subscription.remaining_uploads + subscription.monthly_upload_count}
                </p>
              </div>
            )}

            <div className="flex gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => navigate(-1)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={() => setStep('payment')}
              >
                Continue to Payment
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Complete Your Upgrade
              </h1>
              <p className="text-gray-600">
                Enter your payment details to upgrade to Premium
              </p>
              <div className="mt-2">
                <span className="inline-block bg-green-100 text-green-800 text-xs font-semibold px-2 py-1 rounded-full mb-1">
                  Early Adopter Price
                </span>
                <div>
                  <span className="text-xl font-bold text-indigo-600">$0.99</span>
                  <span className="text-gray-600 ml-1">/ month</span>
                </div>
              </div>
            </div>

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
              >
                ← Back
              </Button>
            </div>

            <p className="text-xs text-gray-500 text-center mt-4">
              Your payment is processed securely by Stripe.
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export { UpgradePage };
