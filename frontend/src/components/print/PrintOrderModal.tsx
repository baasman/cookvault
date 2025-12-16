import React, { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { PrintSpecificationForm } from './PrintSpecificationForm';
import { ShippingAddressForm } from './ShippingAddressForm';
import { OrderSummary } from './OrderSummary';
import { PaymentForm } from './PaymentForm';
import { getApiUrl } from '../../utils/getApiUrl';
import { apiFetch } from '../../utils/apiInterceptor';

interface PrintOrderModalProps {
  cookbookId: number;
  cookbookTitle: string;
  isOpen: boolean;
  onClose: () => void;
}

export interface PrintSpecification {
  trim_size: string;
  binding_type: string;
  paper_type: string;
  cover_finish: string;
  template: string;
  page_count: number;
  color_pages: boolean;
}

export interface ShippingAddress {
  name: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state_code: string;
  postal_code: string;
  country_code: string;
  email: string;
  phone?: string;
}

export interface PrintQuote {
  cookbook_id: number;
  cookbook_title: string;
  quantity: number;
  specification: PrintSpecification;
  costs: {
    printing_cost: number;
    shipping_cost: number;
    tax_amount: number;
    platform_fee: number;
    total_cost: number;
  };
  estimated_delivery_days: number;
  valid_until: string;
  quote_id: string;
  shipping_destination: {
    country: string;
    state: string | null;
  };
}

type OrderStep = 'specifications' | 'shipping' | 'summary' | 'payment' | 'complete';

export const PrintOrderModal: React.FC<PrintOrderModalProps> = ({
  cookbookId,
  cookbookTitle,
  isOpen,
  onClose
}) => {
  const [currentStep, setCurrentStep] = useState<OrderStep>('specifications');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form data
  const [specification, setSpecification] = useState<PrintSpecification | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [shippingAddress, setShippingAddress] = useState<ShippingAddress | null>(null);
  const [quote, setQuote] = useState<PrintQuote | null>(null);
  const [printOrderId, setPrintOrderId] = useState<number | null>(null);

  // Available options from API
  const [printOptions, setPrintOptions] = useState<any>(null);
  const [bulkPricingTiers, setBulkPricingTiers] = useState<any[]>([]);

  useEffect(() => {
    if (isOpen) {
      fetchPrintOptions();
    }
  }, [isOpen]);

  const fetchPrintOptions = async () => {
    try {
      setLoading(true);
      const response = await apiFetch(`${getApiUrl()}/print-orders/specifications?cookbook_id=${cookbookId}`);
      if (response.ok) {
        const data = await response.json();
        setPrintOptions(data);
        setBulkPricingTiers(data.bulk_pricing_tiers || []);
      } else {
        throw new Error('Failed to fetch print options');
      }
    } catch (err) {
      setError('Failed to load print options. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const generateQuote = async () => {
    if (!specification || !shippingAddress) return;

    try {
      setLoading(true);
      setError(null);

      const response = await apiFetch(`${getApiUrl()}/print-orders/quote`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cookbook_id: cookbookId,
          quantity,
          specification,
          shipping_address: shippingAddress
        })
      });

      if (response.ok) {
        const quoteData = await response.json();
        setQuote(quoteData);
        setCurrentStep('summary');
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate quote');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate quote');
    } finally {
      setLoading(false);
    }
  };

  const createOrder = async () => {
    if (!specification || !shippingAddress) return;

    try {
      setLoading(true);
      setError(null);

      const response = await apiFetch(`${getApiUrl()}/print-orders/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cookbook_id: cookbookId,
          quantity,
          specification,
          shipping_address: shippingAddress
        })
      });

      if (response.ok) {
        const orderData = await response.json();
        setPrintOrderId(orderData.order.id);
        setCurrentStep('payment');
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create order');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create order');
    } finally {
      setLoading(false);
    }
  };

  const handleStepChange = (step: OrderStep) => {
    setCurrentStep(step);
    setError(null);
  };

  const handleClose = () => {
    // Reset all state when closing
    setCurrentStep('specifications');
    setSpecification(null);
    setQuantity(1);
    setShippingAddress(null);
    setQuote(null);
    setPrintOrderId(null);
    setError(null);
    onClose();
  };

  const getStepTitle = () => {
    switch (currentStep) {
      case 'specifications':
        return 'Print Specifications';
      case 'shipping':
        return 'Shipping Address';
      case 'summary':
        return 'Order Summary';
      case 'payment':
        return 'Payment';
      case 'complete':
        return 'Order Complete';
      default:
        return 'Print Order';
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 'specifications':
        return (
          <PrintSpecificationForm
            printOptions={printOptions}
            bulkPricingTiers={bulkPricingTiers}
            specification={specification}
            quantity={quantity}
            onSpecificationChange={setSpecification}
            onQuantityChange={setQuantity}
            onNext={() => handleStepChange('shipping')}
            loading={loading}
          />
        );

      case 'shipping':
        return (
          <ShippingAddressForm
            shippingAddress={shippingAddress}
            onAddressChange={setShippingAddress}
            onNext={generateQuote}
            onBack={() => handleStepChange('specifications')}
            loading={loading}
          />
        );

      case 'summary':
        return (
          <OrderSummary
            quote={quote}
            cookbookTitle={cookbookTitle}
            onNext={createOrder}
            onBack={() => handleStepChange('shipping')}
            loading={loading}
          />
        );

      case 'payment':
        return (
          <PaymentForm
            printOrderId={printOrderId}
            quote={quote}
            onPaymentComplete={() => handleStepChange('complete')}
            onBack={() => handleStepChange('summary')}
            loading={loading}
          />
        );

      case 'complete':
        return (
          <div className="text-center py-8">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
              <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="mt-4 text-lg font-medium text-gray-900">Order Placed Successfully!</h3>
            <p className="mt-2 text-sm text-gray-600">
              Your print order has been submitted. You'll receive an email confirmation shortly.
            </p>
            <button
              onClick={handleClose}
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500"
            >
              Close
            </button>
          </div>
        );

      default:
        return null;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">{getStepTitle()}</h2>
            <p className="text-sm text-gray-600 mt-1">Order print copy of "{cookbookTitle}"</p>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-500 focus:outline-none focus:text-gray-500"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Progress Steps */}
        {currentStep !== 'complete' && (
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center space-x-4">
              {['specifications', 'shipping', 'summary', 'payment'].map((step, index) => {
                const stepIndex = ['specifications', 'shipping', 'summary', 'payment'].indexOf(currentStep);
                const isCompleted = index < stepIndex;
                const isCurrent = step === currentStep;
                
                return (
                  <div key={step} className="flex items-center">
                    <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                      isCompleted ? 'bg-emerald-500 text-white' :
                      isCurrent ? 'bg-emerald-100 text-emerald-600 ring-2 ring-emerald-500' :
                      'bg-gray-100 text-gray-500'
                    }`}>
                      {isCompleted ? (
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        index + 1
                      )}
                    </div>
                    {index < 3 && (
                      <div className={`w-12 h-px ${
                        isCompleted ? 'bg-emerald-500' : 'bg-gray-200'
                      }`} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mx-6 mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Content */}
        <div className="p-6">
          {renderStepContent()}
        </div>
      </div>
    </div>
  );
};