import React from 'react';
import { CheckIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import type { PrintQuote } from './PrintOrderModal';

interface OrderSummaryProps {
  quote: PrintQuote | null;
  cookbookTitle: string;
  onNext: () => void;
  onBack: () => void;
  loading: boolean;
}

export const OrderSummary: React.FC<OrderSummaryProps> = ({
  quote,
  cookbookTitle,
  onNext,
  onBack,
  loading
}) => {
  if (!quote) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatSpecification = (spec: any) => {
    const formatName = (str: string) => {
      return str.replace(/_/g, ' ')
               .replace(/\b\w/g, (l: string) => l.toUpperCase());
    };

    return {
      trimSize: formatName(spec.trim_size),
      bindingType: formatName(spec.binding_type),
      paperType: formatName(spec.paper_type),
      coverFinish: formatName(spec.cover_finish)
    };
  };

  const specification = formatSpecification(quote.specification);
  const validUntil = new Date(quote.valid_until).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });

  return (
    <div className="space-y-6">
      {/* Order Details */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
          <CheckIcon className="h-5 w-5 text-emerald-500 mr-2" />
          Order Summary
        </h3>
        
        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Cookbook</span>
            <span className="text-sm font-medium text-gray-900">"{cookbookTitle}"</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Quantity</span>
            <span className="text-sm font-medium text-gray-900">{quote.quantity} {quote.quantity === 1 ? 'copy' : 'copies'}</span>
          </div>
          
          <div className="border-t border-gray-200 pt-3">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Print Specifications</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Size</span>
                <span className="text-gray-900">{specification.trimSize}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Binding</span>
                <span className="text-gray-900">{specification.bindingType}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Paper</span>
                <span className="text-gray-900">{specification.paperType}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Cover</span>
                <span className="text-gray-900">{specification.coverFinish}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Pages</span>
                <span className="text-gray-900">{quote.specification.page_count} pages</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Color Pages</span>
                <span className="text-gray-900">{quote.specification.color_pages ? 'Yes' : 'No'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Cost Breakdown */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Cost Breakdown</h3>
        
        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Printing Cost</span>
            <span className="text-sm text-gray-900">{formatCurrency(quote.costs.printing_cost)}</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Shipping</span>
            <span className="text-sm text-gray-900">{formatCurrency(quote.costs.shipping_cost)}</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Platform Fee</span>
            <span className="text-sm text-gray-900">{formatCurrency(quote.costs.platform_fee)}</span>
          </div>
          
          {quote.costs.tax_amount > 0 && (
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Tax</span>
              <span className="text-sm text-gray-900">{formatCurrency(quote.costs.tax_amount)}</span>
            </div>
          )}
          
          <div className="border-t border-gray-200 pt-3">
            <div className="flex justify-between">
              <span className="text-base font-semibold text-gray-900">Total</span>
              <span className="text-base font-semibold text-gray-900">{formatCurrency(quote.costs.total_cost)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Shipping Information */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <InformationCircleIcon className="h-5 w-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-medium text-blue-800 mb-1">Shipping & Delivery</h4>
            <div className="text-sm text-blue-700 space-y-1">
              <p>
                Estimated delivery: <strong>{quote.estimated_delivery_days} business days</strong> to{' '}
                {quote.shipping_destination.state ? 
                  `${quote.shipping_destination.state}, ${quote.shipping_destination.country}` :
                  quote.shipping_destination.country
                }
              </p>
              <p>You'll receive tracking information once your order ships.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quote Validity */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start">
          <InformationCircleIcon className="h-5 w-5 text-yellow-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-medium text-yellow-800 mb-1">Quote Validity</h4>
            <p className="text-sm text-yellow-700">
              This quote is valid until <strong>{validUntil}</strong>. 
              Prices may change if you return to this step after the quote expires.
            </p>
          </div>
        </div>
      </div>

      {/* Important Notes */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Important Information</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• Your cookbook will be printed on-demand and shipped directly to you</li>
          <li>• Orders typically process within 1-2 business days before shipping</li>
          <li>• You can cancel your order for a full refund before it enters production</li>
          <li>• Final page count may vary slightly from the estimate</li>
          <li>• Questions? Contact us at support@cookbookcreator.com</li>
        </ul>
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between pt-4">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center px-6 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500"
        >
          Back to Shipping
        </button>
        
        <button
          type="button"
          onClick={onNext}
          disabled={loading}
          className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Creating Order...' : 'Proceed to Payment'}
        </button>
      </div>
    </div>
  );
};