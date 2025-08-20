import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { paymentsApi } from '../../services/paymentsApi';

interface PaymentStatusHandlerProps {
  className?: string;
}

type PaymentStatus = 'checking' | 'success' | 'error' | 'canceled';

interface PaymentResult {
  status: PaymentStatus;
  message: string;
  paymentType?: 'subscription' | 'cookbook';
  cookbookId?: number;
}

export const PaymentStatusHandler: React.FC<PaymentStatusHandlerProps> = ({
  className = '',
}) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [result, setResult] = useState<PaymentResult>({ status: 'checking', message: 'Processing payment...' });

  useEffect(() => {
    const checkPaymentStatus = async () => {
      try {
        // Get URL parameters
        const paymentIntent = searchParams.get('payment_intent');
        // const paymentIntentClientSecret = searchParams.get('payment_intent_client_secret');
        const redirectStatus = searchParams.get('redirect_status');
        const cookbookId = searchParams.get('cookbook');

        if (!paymentIntent || !redirectStatus) {
          setResult({
            status: 'error',
            message: 'Invalid payment parameters. Please try again.',
          });
          return;
        }

        if (redirectStatus === 'succeeded') {
          // Verify payment status with our backend
          const payment = await paymentsApi.getPaymentStatus(paymentIntent);
          
          if (payment.status === 'succeeded') {
            setResult({
              status: 'success',
              message: payment.payment_type === 'subscription' 
                ? 'Your premium upgrade was successful! You now have unlimited recipe uploads.'
                : 'Your cookbook purchase was successful! You now have access to all recipes.',
              paymentType: payment.payment_type as 'subscription' | 'cookbook',
              cookbookId: cookbookId ? parseInt(cookbookId, 10) : undefined,
            });
          } else {
            setResult({
              status: 'error',
              message: 'Payment processing failed. Please contact support if this issue persists.',
            });
          }
        } else if (redirectStatus === 'failed') {
          setResult({
            status: 'error',
            message: 'Payment failed. Please try again or use a different payment method.',
          });
        } else {
          setResult({
            status: 'canceled',
            message: 'Payment was canceled. You can try again at any time.',
          });
        }
      } catch (error) {
        console.error('Payment status check failed:', error);
        setResult({
          status: 'error',
          message: 'Unable to verify payment status. Please contact support.',
        });
      }
    };

    checkPaymentStatus();
  }, [searchParams]);

  const handleContinue = () => {
    if (result.paymentType === 'subscription') {
      navigate('/recipes'); // Go to recipes page after subscription upgrade
    } else if (result.paymentType === 'cookbook' && result.cookbookId) {
      navigate(`/cookbooks/${result.cookbookId}`); // Go to purchased cookbook
    } else {
      navigate('/'); // Go to home page
    }
  };

  const handleRetry = () => {
    if (result.paymentType === 'cookbook' && result.cookbookId) {
      navigate(`/cookbooks/${result.cookbookId}`); // Go back to cookbook page
    } else {
      navigate('/account'); // Go to account page to retry upgrade
    }
  };

  const renderIcon = () => {
    switch (result.status) {
      case 'checking':
        return (
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
        );
      case 'success':
        return (
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </div>
        );
      case 'error':
        return (
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </div>
        );
      case 'canceled':
        return (
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </div>
        );
      default:
        return null;
    }
  };

  const getTitle = () => {
    switch (result.status) {
      case 'checking':
        return 'Processing Payment';
      case 'success':
        return result.paymentType === 'subscription' ? 'Welcome to Premium!' : 'Purchase Successful!';
      case 'error':
        return 'Payment Failed';
      case 'canceled':
        return 'Payment Canceled';
      default:
        return '';
    }
  };

  const getButtonText = () => {
    switch (result.status) {
      case 'success':
        return 'Continue';
      case 'error':
        return 'Try Again';
      case 'canceled':
        return 'Go Back';
      default:
        return 'Continue';
    }
  };

  return (
    <div className={`max-w-md mx-auto text-center ${className}`}>
      <div className="bg-white rounded-lg shadow-lg p-8">
        {renderIcon()}
        
        <h2 className="text-2xl font-bold text-gray-900 mt-4 mb-2">
          {getTitle()}
        </h2>
        
        <p className="text-gray-600 mb-6">
          {result.message}
        </p>

        {result.status !== 'checking' && (
          <div className="flex gap-3">
            {result.status === 'error' && (
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => navigate('/')}
              >
                Cancel
              </Button>
            )}
            <Button
              variant="primary"
              className="flex-1"
              onClick={result.status === 'error' ? handleRetry : handleContinue}
            >
              {getButtonText()}
            </Button>
          </div>
        )}

        {result.status === 'error' && (
          <p className="text-sm text-gray-500 mt-4">
            Need help? <a href="/contact" className="text-blue-600 hover:underline">Contact Support</a>
          </p>
        )}
      </div>
    </div>
  );
};