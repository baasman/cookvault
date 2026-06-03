import React from 'react';
import { useNavigate } from 'react-router-dom';

interface BooksSubNavProps {
  active: 'cookbooks' | 'projects';
}

/**
 * Pill toggle between the two flavors of "Books" — personal cookbooks and
 * collaborative book projects. Shown at the top of both list pages so the
 * user can flip between them without rummaging through the header / iOS tab
 * bar. The iOS Books tab itself treats both routes as active.
 */
export const BooksSubNav: React.FC<BooksSubNavProps> = ({ active }) => {
  const navigate = useNavigate();

  const tabs: { id: 'cookbooks' | 'projects'; label: string; path: string }[] = [
    { id: 'cookbooks', label: 'My cookbooks', path: '/cookbooks' },
    { id: 'projects', label: 'Collaborative books', path: '/projects' },
  ];

  return (
    <div className="flex justify-center mb-6">
      <div
        className="inline-flex items-center p-1 rounded-full"
        style={{ backgroundColor: '#f6efe6' }}
      >
        {tabs.map((tab) => {
          const isActive = tab.id === active;
          return (
            <button
              key={tab.id}
              onClick={() => navigate(tab.path)}
              className="px-4 py-1.5 text-sm font-medium rounded-full transition-colors"
              style={{
                backgroundColor: isActive ? '#1c120d' : 'transparent',
                color: isActive ? '#fcf9f8' : '#6b5a52',
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default BooksSubNav;
