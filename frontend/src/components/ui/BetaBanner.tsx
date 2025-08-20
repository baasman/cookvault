import React, { useState, useEffect } from 'react';

const BetaBanner: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const STORAGE_KEY = 'cookle-beta-banner-dismissed';

  useEffect(() => {
    // Check if banner was previously dismissed
    const isDismissed = localStorage.getItem(STORAGE_KEY) === 'true';
    setIsVisible(!isDismissed);
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    localStorage.setItem(STORAGE_KEY, 'true');
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div 
      className="relative bg-amber-50 border-b border-amber-200 px-4 py-3 text-center animate-fadeIn"
      role="banner"
      aria-label="Beta version notice"
    >
      <div className="max-w-6xl mx-auto flex items-center justify-center">
        <div className="flex-1 flex items-center justify-center gap-2">
          <span className="text-amber-600 font-semibold">🚀 Beta Version</span>
          <span className="text-amber-800 text-sm md:text-base">
            Welcome to Cookle! We're actively developing new features. Things may change as we improve the experience.
          </span>
        </div>
        <button
          onClick={handleDismiss}
          className="ml-4 text-amber-600 hover:text-amber-800 transition-colors p-1"
          aria-label="Dismiss beta banner"
        >
          <svg 
            className="w-5 h-5" 
            fill="none" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth="2" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
    </div>
  );
};

export default BetaBanner;