import React, { useState } from 'react';
import { Modal, Button } from './';

interface CopyrightConsentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (consents: Record<string, boolean>) => void;
  recipeName: string;
  isLoading?: boolean;
}

const CopyrightConsentModal: React.FC<CopyrightConsentModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  recipeName,
  isLoading = false
}) => {
  const [consents, setConsents] = useState({
    rightsToShare: false,
    understandsPublic: false,
    personalUseOnly: false,
    noCopyrightViolation: false
  });

  const handleConsentChange = (key: keyof typeof consents) => {
    setConsents(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const allConsentsGiven = Object.values(consents).every(Boolean);

  const handleConfirm = () => {
    if (allConsentsGiven) {
      onConfirm(consents);
    }
  };

  const handleClose = () => {
    // Reset consents when closing
    setConsents({
      rightsToShare: false,
      understandsPublic: false,
      personalUseOnly: false,
      noCopyrightViolation: false
    });
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="lg">
      <div className="p-6">
        <div className="flex items-center mb-4">
          <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mr-4">
            <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Copyright Consent Required</h2>
            <p className="text-sm text-gray-600">Before making "{recipeName}" public</p>
          </div>
        </div>

        <div className="mb-6">
          <p className="text-gray-700 mb-4">
            You are about to make this recipe publicly visible. This means other users will be able to view, 
            save, and use this recipe for their personal cooking. Please confirm your understanding and rights:
          </p>
          
          <div className="bg-red-50 border border-red-200 p-4 rounded-lg mb-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-red-600 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <div>
                <h3 className="font-semibold text-red-900 mb-1">⚠️ Important: This Action Cannot Be Undone</h3>
                <p className="text-sm text-red-800">
                  <strong>Once you make this recipe public, you cannot make it private again.</strong> If you later want to 
                  remove it from public view, your only option will be to delete the recipe entirely. Please be certain 
                  you want to share this recipe publicly before proceeding.
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-50 p-4 rounded-lg mb-4">
            <h3 className="font-semibold text-gray-900 mb-2">Copyright Notice</h3>
            <p className="text-sm text-gray-700">
              Recipe ingredients and basic cooking methods are generally not copyrightable. However, 
              detailed creative descriptions, personal stories, unique presentations, and substantial 
              portions of published cookbooks may be protected by copyright.
            </p>
          </div>
        </div>

        <div className="space-y-4 mb-6">
          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consents.rightsToShare}
              onChange={() => handleConsentChange('rightsToShare')}
              className="mt-1 w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
              disabled={isLoading}
            />
            <span className="text-sm text-gray-700">
              <strong>I have the right to share this recipe publicly.</strong> I either created this recipe myself, 
              have permission to share it, or believe it contains only non-copyrightable factual cooking information.
            </span>
          </label>

          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consents.understandsPublic}
              onChange={() => handleConsentChange('understandsPublic')}
              className="mt-1 w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
              disabled={isLoading}
            />
            <span className="text-sm text-gray-700">
              <strong>I understand this recipe will be publicly visible.</strong> Other users will be able to view, 
              search for, and access this recipe once it's made public.
            </span>
          </label>

          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consents.personalUseOnly}
              onChange={() => handleConsentChange('personalUseOnly')}
              className="mt-1 w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
              disabled={isLoading}
            />
            <span className="text-sm text-gray-700">
              <strong>I grant others permission for personal use.</strong> I allow other users to use this recipe 
              for their personal, non-commercial cooking and meal preparation.
            </span>
          </label>

          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consents.noCopyrightViolation}
              onChange={() => handleConsentChange('noCopyrightViolation')}
              className="mt-1 w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
              disabled={isLoading}
            />
            <span className="text-sm text-gray-700">
              <strong>I will not violate copyright.</strong> I have not copied substantial portions of copyrighted 
              cookbooks, magazine articles, or other protected content without permission.
            </span>
          </label>
        </div>

        <div className="bg-blue-50 p-4 rounded-lg mb-6">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-blue-600 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="font-semibold text-blue-900 mb-1">Need Help?</h4>
              <p className="text-sm text-blue-800">
                If you're unsure about your rights to share this recipe, consider keeping it private or 
                consulting our <a href="/copyright-policy" className="underline hover:no-underline" target="_blank" rel="noopener noreferrer">Copyright Policy</a>.
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-end space-x-3">
          <Button
            onClick={handleClose}
            variant="secondary"
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            variant="primary"
            disabled={!allConsentsGiven || isLoading}
          >
            {isLoading ? 'Publishing...' : 'Confirm & Make Public'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export { CopyrightConsentModal };