import React from 'react';
import { Link } from 'react-router-dom';
import { openExternalUrl } from '../../utils/platform';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  const handleContactClick = (e: React.MouseEvent) => {
    e.preventDefault();
    openExternalUrl('mailto:boudeyz@gmail.com');
  };

  return (
    <footer className="border-t border-gray-200 mt-auto" style={{ backgroundColor: '#fcf9f8' }}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <img src="/icons/icon-192x192.png" alt="Cookle" className="w-8 h-8 rounded-lg" />
            <span className="text-lg font-semibold" style={{ color: '#1c120d' }}>Cookle</span>
            <span className="text-gray-500 text-sm">
              &copy; {currentYear} All rights reserved.
            </span>
          </div>

          <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm">
            <Link
              to="/privacy-policy"
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              Privacy Policy
            </Link>
            <Link
              to="/terms-of-service"
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              Terms of Service
            </Link>
            <Link
              to="/copyright-policy"
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              Copyright Policy
            </Link>
            <button
              onClick={handleContactClick}
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              Contact
            </button>
          </nav>
        </div>
      </div>
    </footer>
  );
};

export { Footer };
