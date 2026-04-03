import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { isIOS, isNativePlatform } from '../../utils/platform';
import { useAuth } from '../../contexts/AuthContext';
import { lightImpact, selectionChanged } from '../../utils/haptics';
import { ActionSheet, type ActionSheetOption } from '../ui/ActionSheet';
import {
  HomeIcon,
  BookOpenIcon,
  PlusIcon,
  BookmarkIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import {
  HomeIcon as HomeIconSolid,
  BookOpenIcon as BookOpenIconSolid,
  BookmarkIcon as BookmarkIconSolid,
  UserIcon as UserIconSolid,
} from '@heroicons/react/24/solid';

interface TabItem {
  id: string;
  label: string;
  path: string;
  icon: React.ReactNode;
  iconActive: React.ReactNode;
}

const tabs: TabItem[] = [
  {
    id: 'home',
    label: 'Home',
    path: '/',
    icon: <HomeIcon className="w-6 h-6" />,
    iconActive: <HomeIconSolid className="w-6 h-6" />,
  },
  {
    id: 'recipes',
    label: 'Recipes',
    path: '/recipes',
    icon: <BookOpenIcon className="w-6 h-6" />,
    iconActive: <BookOpenIconSolid className="w-6 h-6" />,
  },
  {
    id: 'add',
    label: 'Add',
    path: '', // Special case - opens action sheet
    icon: <PlusIcon className="w-6 h-6" />,
    iconActive: <PlusIcon className="w-6 h-6" />,
  },
  {
    id: 'cookbooks',
    label: 'Books',
    path: '/cookbooks',
    icon: <BookmarkIcon className="w-6 h-6" />,
    iconActive: <BookmarkIconSolid className="w-6 h-6" />,
  },
  {
    id: 'profile',
    label: 'Profile',
    path: '/profile',
    icon: <UserIcon className="w-6 h-6" />,
    iconActive: <UserIconSolid className="w-6 h-6" />,
  },
];

/**
 * iOS-style bottom tab bar navigation
 * Only renders on native iOS platform
 */
export const TabBar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const [isAddSheetOpen, setIsAddSheetOpen] = useState(false);

  // Only render on native iOS
  if (!isIOS() || !isNativePlatform()) {
    return null;
  }

  const isActiveTab = (tab: TabItem): boolean => {
    if (tab.id === 'home') {
      return location.pathname === '/';
    }
    if (tab.id === 'add') {
      return false; // Add button is never "active"
    }
    return location.pathname.startsWith(tab.path);
  };

  const handleTabPress = (tab: TabItem) => {
    if (tab.id === 'add') {
      // Open action sheet for add options
      lightImpact();
      if (isAuthenticated) {
        setIsAddSheetOpen(true);
      } else {
        navigate('/login');
      }
      return;
    }

    if (tab.id === 'profile' && !isAuthenticated) {
      // Redirect to login if not authenticated
      selectionChanged();
      navigate('/login');
      return;
    }

    // Navigate to tab
    selectionChanged();
    navigate(tab.path);
  };

  const addOptions: ActionSheetOption[] = [
    {
      label: 'Upload from Image',
      icon: <span className="text-lg">📷</span>,
      onClick: () => navigate('/upload'),
    },
    {
      label: 'Import from URL',
      icon: <span className="text-lg">🔗</span>,
      onClick: () => navigate('/upload?mode=url'),
    },
    {
      label: 'Create Manually',
      icon: <span className="text-lg">✏️</span>,
      onClick: () => navigate('/recipes/create'),
    },
  ];

  return (
    <>
      <nav className="ios-tab-bar" aria-label="Main navigation">
        <div className="flex items-center justify-around h-[49px]">
          {tabs.map((tab) => {
            const isActive = isActiveTab(tab);
            const isAddButton = tab.id === 'add';

            return (
              <button
                key={tab.id}
                onClick={() => handleTabPress(tab)}
                className={`flex flex-col items-center justify-center flex-1 h-full active:opacity-70 transition-opacity ${
                  isAddButton ? 'relative' : ''
                }`}
                aria-label={tab.label}
                aria-current={isActive ? 'page' : undefined}
              >
                {isAddButton ? (
                  // Centered Add button with accent color
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center -mt-3 shadow-lg active:scale-95 transition-transform"
                    style={{ backgroundColor: '#f15f1c' }}
                  >
                    <PlusIcon className="w-7 h-7 text-white" />
                  </div>
                ) : (
                  <>
                    <span
                      style={{
                        color: isActive ? '#f15f1c' : '#9b644b',
                      }}
                    >
                      {isActive ? tab.iconActive : tab.icon}
                    </span>
                    <span
                      className="text-[10px] mt-0.5 font-medium"
                      style={{
                        color: isActive ? '#f15f1c' : '#9b644b',
                      }}
                    >
                      {tab.label}
                    </span>
                  </>
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Add Recipe Action Sheet */}
      <ActionSheet
        isOpen={isAddSheetOpen}
        onClose={() => setIsAddSheetOpen(false)}
        title="Add Recipe"
        options={addOptions}
      />
    </>
  );
};
