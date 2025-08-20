import React from 'react';
import { Modal } from './Modal';
import { Button } from './Button';

interface BetaModeRestrictionModalProps {
  isOpen: boolean;
  onClose: () => void;
  feature: 'premium' | 'cookbook';
  cookbookTitle?: string;
  price?: number;
}

export const BetaModeRestrictionModal: React.FC<BetaModeRestrictionModalProps> = ({
  isOpen,
  onClose,
  feature,
  cookbookTitle,
  price,
}) => {
  const getFeatureText = () => {
    if (feature === 'premium') {
      return {
        title: 'Premium Upgrade',
        description: 'premium subscription features',
      };
    } else {
      return {
        title: cookbookTitle || 'Cookbook Purchase',
        description: `the cookbook "${cookbookTitle}"`,
      };
    }
  };

  const { title, description } = getFeatureText();

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Beta Mode">
      <div className="p-6">
        {/* Beta Icon */}
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>

        {/* Main Content */}
        <div className="text-center mb-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-3">
            {title} - Coming Soon!
          </h3>
          <p className="text-gray-600 leading-relaxed mb-4">
            Thank you for your interest in {description}! Cookle is currently in beta mode, 
            and purchasing features are temporarily disabled while we fine-tune the experience.
          </p>
          
          {price && (
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <p className="text-sm text-gray-700">
                <span className="font-medium">Price when available:</span> ${price.toFixed(2)}
              </p>
            </div>
          )}
        </div>

        {/* Contact Information */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
          <h4 className="text-lg font-semibold text-blue-900 mb-3">
            🚀 Get Early Access
          </h4>
          <p className="text-blue-800 text-sm mb-4">
            Interested in being among the first to access our premium features? 
            We'd love to hear from you!
          </p>
          
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <svg className="h-4 w-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
              </svg>
              <a 
                href="mailto:admin@cookle.food?subject=Early Access Request - Beta User"
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                admin@cookle.food
              </a>
            </div>
            
            <div className="text-xs text-blue-600 bg-blue-100 rounded p-3">
              <p className="font-medium mb-1">📧 Email us about:</p>
              <ul className="space-y-1">
                <li>• Early access to premium features</li>
                <li>• Feedback on the beta experience</li>
                <li>• Special pricing for early supporters</li>
                <li>• Feature requests and suggestions</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex justify-center">
          <Button
            onClick={onClose}
            variant="primary"
            size="md"
            className="w-full sm:w-auto"
          >
            Continue Exploring Cookle
          </Button>
        </div>

        {/* Footer Note */}
        <div className="text-center mt-4">
          <p className="text-xs text-gray-500">
            We appreciate your patience as we perfect the Cookle experience!
          </p>
        </div>
      </div>
    </Modal>
  );
};