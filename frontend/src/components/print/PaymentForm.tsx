import React, { useState, useEffect } from 'react';
import { CreditCardIcon, LockClosedIcon } from '@heroicons/react/24/outline';
import { getApiUrl } from '../../utils/getApiUrl';
import { apiFetch } from '../../utils/apiInterceptor';
import type { PrintQuote } from './PrintOrderModal';

interface PaymentFormProps {
  printOrderId: number | null;
  quote: PrintQuote | null;
  onPaymentComplete: () => void;
  onBack: () => void;
  loading: boolean;
}

interface PaymentIntent {
  client_secret: string;
  amount: number;
  currency: string;
}

export const PaymentForm: React.FC<PaymentFormProps> = ({
  printOrderId,
  quote,
  onPaymentComplete,
  onBack,
  loading: parentLoading
}) => {
  const [paymentIntent, setPaymentIntent] = useState<PaymentIntent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Mock payment form state for demonstration
  const [paymentData, setPaymentData] = useState({
    cardNumber: '',
    expiryDate: '',
    cvv: '',
    cardholderName: '',
    billingAddress: {
      line1: '',
      city: '',
      state: '',
      postal_code: '',
      country: 'US'
    }
  });

  useEffect(() => {
    if (printOrderId && !paymentIntent) {
      createPaymentIntent();
    }
  }, [printOrderId]);

  const createPaymentIntent = async () => {
    if (!printOrderId) return;

    try {
      setLoading(true);
      setError(null);

      const response = await apiFetch(`${getApiUrl()}/print-orders/${printOrderId}/payment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const data = await response.json();
        setPaymentIntent(data.payment_intent);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create payment intent');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize payment');
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = async () => {
    if (!paymentIntent || !quote) return;

    try {
      setProcessing(true);
      setError(null);

      // In a real implementation, this would use Stripe.js to process the payment
      // For now, we'll simulate the payment process
      
      // Simulate payment processing delay
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Simulate successful payment
      // In real implementation, Stripe webhooks would handle order status updates
      onPaymentComplete();

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Payment failed');
    } finally {
      setProcessing(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const validateField = (field: string, value: string): string => {
    switch (field) {
      case 'cardNumber':
        if (value.replace(/\s/g, '').length < 13) return 'Card number must be at least 13 digits';
        break;
      case 'expiryDate':
        if (!/^\d{2}\/\d{2}$/.test(value)) return 'Format must be MM/YY';
        const [month] = value.split('/');
        if (parseInt(month) < 1 || parseInt(month) > 12) return 'Invalid month';
        break;
      case 'cvv':
        if (value.length < 3) return 'CVV must be at least 3 digits';
        break;
      case 'cardholderName':
        if (value.trim().length === 0) return 'Cardholder name is required';
        break;
      case 'billing.line1':
        if (value.trim().length === 0) return 'Street address is required';
        break;
      case 'billing.city':
        if (value.trim().length === 0) return 'City is required';
        break;
      case 'billing.state':
        if (value.trim().length === 0) return 'State is required';
        break;
      case 'billing.postal_code':
        if (value.trim().length === 0) return 'ZIP code is required';
        break;
    }
    return '';
  };

  const handleInputChange = (field: string, value: string) => {
    // Format expiry date automatically
    if (field === 'expiryDate') {
      // Remove non-digits and format as MM/YY
      const digits = value.replace(/\D/g, '');
      if (digits.length <= 2) {
        value = digits;
      } else {
        value = digits.slice(0, 2) + '/' + digits.slice(2, 4);
      }
    }

    // Format card number with spaces
    if (field === 'cardNumber') {
      value = value.replace(/\s/g, '').replace(/(.{4})/g, '$1 ').trim();
    }

    if (field.startsWith('billing.')) {
      const billingField = field.replace('billing.', '');
      setPaymentData(prev => ({
        ...prev,
        billingAddress: {
          ...prev.billingAddress,
          [billingField]: value
        }
      }));
    } else {
      setPaymentData(prev => ({ ...prev, [field]: value }));
    }

    // Validate field and update errors
    const errorMessage = validateField(field, value);
    setFieldErrors(prev => ({
      ...prev,
      [field]: errorMessage
    }));
  };

  const isFormValid = () => {
    // Check if any field has errors
    const hasErrors = Object.values(fieldErrors).some(error => error !== '');
    if (hasErrors) return false;

    // Check if all required fields are filled
    return paymentData.cardNumber.replace(/\s/g, '').length >= 13 &&
           /^\d{2}\/\d{2}$/.test(paymentData.expiryDate) &&
           paymentData.cvv.length >= 3 &&
           paymentData.cardholderName.trim().length > 0 &&
           paymentData.billingAddress.line1.trim().length > 0 &&
           paymentData.billingAddress.city.trim().length > 0 &&
           paymentData.billingAddress.state.trim().length > 0 &&
           paymentData.billingAddress.postal_code.trim().length > 0;
  };

  if (loading || parentLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (!paymentIntent || !quote) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Unable to initialize payment. Please try again.</p>
        <button
          onClick={onBack}
          className="mt-4 inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50"
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Payment Amount Summary */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <LockClosedIcon className="h-5 w-5 text-emerald-600 mr-2" />
            <span className="text-sm font-medium text-emerald-800">Secure Payment</span>
          </div>
          <div className="text-lg font-semibold text-emerald-900">
            {formatCurrency(quote.costs.total_cost)}
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Payment Form */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
          <CreditCardIcon className="h-5 w-5 mr-2" />
          Payment Information
        </h3>

        <div className="space-y-4">
          {/* Card Number */}
          <div>
            <label htmlFor="cardNumber" className="block text-sm font-medium text-gray-700 mb-1">
              Card Number
            </label>
            <input
              type="text"
              id="cardNumber"
              value={paymentData.cardNumber}
              onChange={(e) => handleInputChange('cardNumber', e.target.value)}
              placeholder="1234 5678 9012 3456"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
              maxLength={19}
            />
          </div>

          {/* Expiry and CVV */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="expiryDate" className="block text-sm font-medium text-gray-700 mb-1">
                Expiry Date
              </label>
              <input
                type="text"
                id="expiryDate"
                value={paymentData.expiryDate}
                onChange={(e) => handleInputChange('expiryDate', e.target.value)}
                placeholder="MM/YY"
                className={`block w-full rounded-md shadow-sm sm:text-sm ${
                  fieldErrors.expiryDate
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300 focus:border-emerald-500 focus:ring-emerald-500'
                }`}
                maxLength={5}
              />
              {fieldErrors.expiryDate && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.expiryDate}</p>
              )}
            </div>

            <div>
              <label htmlFor="cvv" className="block text-sm font-medium text-gray-700 mb-1">
                CVV
              </label>
              <input
                type="text"
                id="cvv"
                value={paymentData.cvv}
                onChange={(e) => handleInputChange('cvv', e.target.value)}
                placeholder="123"
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
                maxLength={4}
              />
            </div>
          </div>

          {/* Cardholder Name */}
          <div>
            <label htmlFor="cardholderName" className="block text-sm font-medium text-gray-700 mb-1">
              Cardholder Name
            </label>
            <input
              type="text"
              id="cardholderName"
              value={paymentData.cardholderName}
              onChange={(e) => handleInputChange('cardholderName', e.target.value)}
              placeholder="John Doe"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
            />
          </div>

          {/* Billing Address */}
          <div className="pt-4 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Billing Address</h4>
            
            <div className="space-y-4">
              <div>
                <label htmlFor="billingLine1" className="block text-sm font-medium text-gray-700 mb-1">
                  Street Address
                </label>
                <input
                  type="text"
                  id="billingLine1"
                  value={paymentData.billingAddress.line1}
                  onChange={(e) => handleInputChange('billing.line1', e.target.value)}
                  placeholder="123 Main St"
                  className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label htmlFor="billingCity" className="block text-sm font-medium text-gray-700 mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    id="billingCity"
                    value={paymentData.billingAddress.city}
                    onChange={(e) => handleInputChange('billing.city', e.target.value)}
                    placeholder="New York"
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="billingState" className="block text-sm font-medium text-gray-700 mb-1">
                    State
                  </label>
                  <input
                    type="text"
                    id="billingState"
                    value={paymentData.billingAddress.state}
                    onChange={(e) => handleInputChange('billing.state', e.target.value)}
                    placeholder="NY"
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="billingPostalCode" className="block text-sm font-medium text-gray-700 mb-1">
                    ZIP Code
                  </label>
                  <input
                    type="text"
                    id="billingPostalCode"
                    value={paymentData.billingAddress.postal_code}
                    onChange={(e) => handleInputChange('billing.postal_code', e.target.value)}
                    placeholder="10001"
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Security Notice */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-start">
          <LockClosedIcon className="h-5 w-5 text-gray-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-1">Secure Payment</h4>
            <p className="text-sm text-gray-600">
              Your payment information is encrypted and processed securely through Stripe. 
              We never store your credit card details.
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between pt-4">
        <button
          type="button"
          onClick={onBack}
          disabled={processing}
          className="inline-flex items-center px-6 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Back to Summary
        </button>
        
        <button
          type="button"
          onClick={handlePayment}
          disabled={!isFormValid() || processing}
          className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {processing ? (
            <>
              <div className="animate-spin -ml-1 mr-3 h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
              Processing Payment...
            </>
          ) : (
            `Pay ${formatCurrency(quote.costs.total_cost)}`
          )}
        </button>
      </div>
    </div>
  );
};