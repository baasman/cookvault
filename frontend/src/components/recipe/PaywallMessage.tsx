import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CookbookPurchaseButton } from '../payments/CookbookPurchaseButton';

interface PaywallMessageProps {
  cookbook?: {
    id: number;
    title: string;
    price?: number;
    is_purchasable?: boolean;
    has_purchased?: boolean;
    is_available_for_purchase?: boolean;
  };
  message?: string;
  type: 'ingredients' | 'instructions';
}

export const PaywallMessage: React.FC<PaywallMessageProps> = ({ 
  cookbook, 
  message, 
  type 
}) => {
  const navigate = useNavigate();
  const defaultMessage = cookbook && cookbook.is_purchasable 
    ? `Purchase "${cookbook.title}" to view the full recipe ${type}.`
    : `This recipe's ${type} are not available.`;

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center bg-gray-50">
      <div className="max-w-md mx-auto">
        <div className="mb-4">
          <svg 
            className="w-12 h-12 mx-auto text-gray-400 mb-3" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={1}
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" 
            />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {type === 'ingredients' ? 'Ingredients' : 'Instructions'} Locked
          </h3>
          <p className="text-gray-600 text-sm leading-relaxed">
            {message || defaultMessage}
          </p>
        </div>

        {cookbook && cookbook.is_purchasable && (
          <div className="space-y-3">
            <CookbookPurchaseButton
              cookbook={{
                id: cookbook.id,
                title: cookbook.title,
                price: cookbook.price || 0,
                is_purchasable: cookbook.is_purchasable || false,
                has_purchased: cookbook.has_purchased,
                is_available_for_purchase: cookbook.is_available_for_purchase,
              }}
              size="md"
              onPurchaseSuccess={() => {
                // Navigate to the success page
                navigate(`/cookbooks/${cookbook.id}/purchase-success`);
              }}
            />
            
            <div className="pt-2 border-t border-gray-200">
              <Link 
                to={`/cookbooks/${cookbook.id}`}
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                View cookbook details →
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};