import React from 'react';
import { Link } from 'react-router-dom';
import { useCookieConsent } from '../../contexts/CookieConsentContext';

export const CookieConsentBanner: React.FC = () => {
  const { hasConsented, acceptCookies, declineCookies } = useCookieConsent();

  // Don't show if user has already made a choice
  if (hasConsented !== null) {
    return null;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 shadow-lg p-4 sm:p-6">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            We value your privacy
          </h3>
          <p className="text-sm text-gray-600">
            We use cookies and similar technologies to help personalize content, improve your experience,
            and analyze site usage. By clicking "Accept", you consent to our use of cookies for analytics
            and error tracking.{' '}
            <Link to="/privacy-policy" className="text-orange-600 hover:text-orange-700 underline">
              Learn more
            </Link>
          </p>
        </div>
        <div className="flex gap-3 flex-shrink-0">
          <button
            onClick={declineCookies}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Decline
          </button>
          <button
            onClick={acceptCookies}
            className="px-4 py-2 text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 rounded-lg transition-colors"
          >
            Accept
          </button>
        </div>
      </div>
    </div>
  );
};
