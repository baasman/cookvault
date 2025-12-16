import React from 'react';
import { Link } from 'react-router-dom';
import { PlusIcon, BookOpenIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';

const QuickActions: React.FC = () => {
  return (
    <div className="flex flex-wrap gap-3">
      <Link
        to="/upload"
        className="inline-flex items-center px-4 py-2 rounded-lg text-white font-medium transition-colors"
        style={{ backgroundColor: '#f15f1c' }}
        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#d9541a'}
        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#f15f1c'}
      >
        <PlusIcon className="w-5 h-5 mr-2" />
        Upload Recipe
      </Link>
      <Link
        to="/cookbooks/create"
        className="inline-flex items-center px-4 py-2 rounded-lg border-2 font-medium transition-colors"
        style={{ borderColor: '#f15f1c', color: '#f15f1c' }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#f15f1c';
          e.currentTarget.style.color = 'white';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
          e.currentTarget.style.color = '#f15f1c';
        }}
      >
        <BookOpenIcon className="w-5 h-5 mr-2" />
        Create Cookbook
      </Link>
      <Link
        to="/recipes"
        className="inline-flex items-center px-4 py-2 rounded-lg border-2 font-medium transition-colors"
        style={{ borderColor: '#9b644b', color: '#9b644b' }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#9b644b';
          e.currentTarget.style.color = 'white';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
          e.currentTarget.style.color = '#9b644b';
        }}
      >
        <MagnifyingGlassIcon className="w-5 h-5 mr-2" />
        Browse Recipes
      </Link>
    </div>
  );
};

export { QuickActions };
