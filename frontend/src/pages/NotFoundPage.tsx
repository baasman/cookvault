import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full text-center">
        <div className="mb-6">
          <span className="text-8xl font-bold text-amber-600">404</span>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Page not found
        </h1>

        <p className="text-gray-600 mb-8">
          Sorry, we couldn't find the page you're looking for. It might have been
          moved or doesn't exist.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => navigate(-1)}
            className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors"
          >
            Go Back
          </button>
          <Link
            to="/"
            className="px-6 py-3 bg-amber-600 text-white rounded-lg font-medium hover:bg-amber-700 transition-colors"
          >
            Go to Home
          </Link>
        </div>

        <div className="mt-8 pt-8 border-t border-gray-200">
          <p className="text-sm text-gray-500 mb-3">
            Looking for something specific?
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <Link
              to="/recipes"
              className="text-amber-600 hover:text-amber-700 text-sm font-medium"
            >
              My Recipes
            </Link>
            <span className="text-gray-300">|</span>
            <Link
              to="/cookbooks"
              className="text-amber-600 hover:text-amber-700 text-sm font-medium"
            >
              My Cookbooks
            </Link>
            <span className="text-gray-300">|</span>
            <Link
              to="/upload"
              className="text-amber-600 hover:text-amber-700 text-sm font-medium"
            >
              Upload Recipe
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
