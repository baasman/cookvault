import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { useAuth } from '../../contexts/AuthContext';
import { PremiumUpgradeModal } from '../payments/PremiumUpgradeModal';
import { BetaModeRestrictionModal } from '../ui/BetaModeRestrictionModal';
import { useBetaModeRestriction } from '../../hooks/useBetaModeRestriction';
import { paymentsApi, type Subscription } from '../../services/paymentsApi';
import type { NavItem } from '../../types';
import { isIOS, isNativePlatform } from '../../utils/platform';
import { ActionSheet } from '../ui/ActionSheet';

// Check if we're on native iOS for header adjustments
const isNativeIOS = (): boolean => isIOS() && isNativePlatform();

interface HeaderProps {
  navItems?: NavItem[];
}

const Header: React.FC<HeaderProps> = ({
  navItems = [
    { label: 'Recipes', href: '/recipes' },
    { label: 'Cookbooks', href: '/cookbooks' },
    { label: 'Sources', href: '/sources' }
  ]
}) => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isAddMenuOpen, setIsAddMenuOpen] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const addMenuRef = useRef<HTMLDivElement>(null);

  // Beta mode restriction hook
  const { checkBetaRestriction, betaModalState, closeBetaModal } = useBetaModeRestriction();

  // iOS action sheet states
  const [isUserActionSheetOpen, setIsUserActionSheetOpen] = useState(false);
  const [isAddActionSheetOpen, setIsAddActionSheetOpen] = useState(false);

  // Check if we're on native iOS
  const showIOSLayout = isNativeIOS();

  // On native platforms, open external browser for payments (App Store Guideline 3.1.1)
  const isNative = isNativePlatform();

  // Handler for upgrade action - navigate to upgrade page on iOS, show modal on web
  const handleUpgradeClick = async () => {
    if (checkBetaRestriction('premium')) {
      return;
    }
    if (isNative) {
      navigate('/upgrade');
    } else {
      setShowUpgradeModal(true);
    }
  };

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
      if (addMenuRef.current && !addMenuRef.current.contains(event.target as Node)) {
        setIsAddMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      const loadSubscription = async () => {
        try {
          const subData = await paymentsApi.getUserSubscription();
          setSubscription(subData);
        } catch (err) {
          console.error('Failed to load subscription:', err);
        }
      };
      loadSubscription();
    }
  }, [isAuthenticated]);

  const handleLogout = () => {
    logout();
    setIsMobileMenuOpen(false);
  };

  const handleUpgradeSuccess = () => {
    // Refresh subscription data
    setSubscription(prev => prev ? { ...prev, tier: 'premium', is_premium: true } : null);
    setShowUpgradeModal(false);
  };

  // Get user initials for avatar
  const getUserInitials = () => {
    if (user?.name) {
      return user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    return user?.email?.[0]?.toUpperCase() || 'U';
  };

  return (
    <header className="border-b sticky top-0 z-50" style={{backgroundColor: '#fcf9f8', borderColor: '#e8d7cf', paddingTop: 'env(safe-area-inset-top)'}}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex-shrink-0">
              <Link to="/" className="flex items-center gap-2">
                <img
                  src="/icons/icon-192x192.png"
                  alt="Cookle"
                  className="w-10 h-10 rounded-lg"
                />
                <span className="text-2xl font-bold" style={{color: '#1c120d'}}>
                  Cookle
                </span>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-8">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  to={item.href}
                  className="font-medium transition-colors hover:text-orange-500"
                  style={{color: '#9b644b'}}
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            {/* Desktop Auth & Actions */}
            <div className="hidden md:flex items-center space-x-3">
              {isAuthenticated ? (
                <>
                  {/* Add Recipe Dropdown */}
                  <div className="relative" ref={addMenuRef}>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setIsAddMenuOpen(!isAddMenuOpen)}
                    >
                      + Add Recipe
                    </Button>
                    {isAddMenuOpen && (
                      <div
                        className="absolute right-0 mt-2 w-48 rounded-lg shadow-lg py-1 z-50 border"
                        style={{ backgroundColor: '#fff', borderColor: '#e8d7cf' }}
                      >
                        <Link
                          to="/upload"
                          className="block px-4 py-2 text-sm hover:bg-orange-50 transition-colors"
                          style={{ color: '#1c120d' }}
                          onClick={() => setIsAddMenuOpen(false)}
                        >
                          📷 Upload from Image
                        </Link>
                        <Link
                          to="/upload?mode=url"
                          className="block px-4 py-2 text-sm hover:bg-orange-50 transition-colors"
                          style={{ color: '#1c120d' }}
                          onClick={() => setIsAddMenuOpen(false)}
                        >
                          🔗 Import from URL
                        </Link>
                        <Link
                          to="/upload?mode=video"
                          className="block px-4 py-2 text-sm hover:bg-orange-50 transition-colors"
                          style={{ color: '#1c120d' }}
                          onClick={() => setIsAddMenuOpen(false)}
                        >
                          🎬 Import from Video
                        </Link>
                        <Link
                          to="/recipes/create"
                          className="block px-4 py-2 text-sm hover:bg-orange-50 transition-colors"
                          style={{ color: '#1c120d' }}
                          onClick={() => setIsAddMenuOpen(false)}
                        >
                          ✏️ Create Manually
                        </Link>
                      </div>
                    )}
                  </div>

                  {/* User Menu Dropdown */}
                  <div className="relative" ref={userMenuRef}>
                    <button
                      onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                      className="flex items-center space-x-2 rounded-full focus:outline-none focus:ring-2 focus:ring-orange-500"
                    >
                      <div
                        className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium text-white"
                        style={{ backgroundColor: '#e27b36' }}
                      >
                        {getUserInitials()}
                      </div>
                    </button>
                    {isUserMenuOpen && (
                      <div
                        className="absolute right-0 mt-2 w-56 rounded-lg shadow-lg py-1 z-50 border"
                        style={{ backgroundColor: '#fff', borderColor: '#e8d7cf' }}
                      >
                        {/* User info */}
                        <div className="px-4 py-3 border-b" style={{ borderColor: '#e8d7cf' }}>
                          <p className="text-sm font-medium" style={{ color: '#1c120d' }}>
                            {user?.name || 'User'}
                          </p>
                          <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                          {subscription?.is_premium && (
                            <span className="inline-block mt-1 px-2 py-0.5 text-xs font-semibold text-yellow-800 bg-yellow-100 rounded-full">
                              ⭐ Premium
                            </span>
                          )}
                        </div>

                        {/* Menu items */}
                        <Link
                          to="/profile"
                          className="block px-4 py-2 text-sm hover:bg-orange-50 transition-colors"
                          style={{ color: '#1c120d' }}
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          Profile
                        </Link>
                        <Link
                          to="/settings"
                          className="block px-4 py-2 text-sm hover:bg-orange-50 transition-colors"
                          style={{ color: '#1c120d' }}
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          Settings
                        </Link>

                        {/* Upgrade option if not premium - opens external browser on iOS */}
                        {subscription && !subscription.is_premium && (
                          <button
                            onClick={() => {
                              setIsUserMenuOpen(false);
                              handleUpgradeClick();
                            }}
                            className="w-full text-left px-4 py-2 text-sm hover:bg-orange-50 transition-colors"
                            style={{ color: '#e27b36' }}
                          >
                            ⭐ Upgrade to Premium
                          </button>
                        )}

                        <div className="border-t my-1" style={{ borderColor: '#e8d7cf' }} />
                        <button
                          onClick={() => {
                            setIsUserMenuOpen(false);
                            handleLogout();
                          }}
                          className="w-full text-left px-4 py-2 text-sm hover:bg-orange-50 transition-colors text-gray-600"
                        >
                          Logout
                        </button>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <Link to="/login">
                    <Button variant="secondary" size="sm">
                      Login
                    </Button>
                  </Link>
                  <Link to="/register">
                    <Button variant="primary" size="sm">
                      Register
                    </Button>
                  </Link>
                </>
              )}
            </div>

            {/* Mobile menu button - hidden on iOS native */}
            {!showIOSLayout && (
              <div className="md:hidden">
                <button
                  type="button"
                  className="p-2 rounded-md focus:outline-none focus:ring-2"
                  style={{color: '#9b644b'}}
                  onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                  aria-label="Open menu"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
              </div>
            )}

            {/* iOS login button when not authenticated */}
            {showIOSLayout && !isAuthenticated && (
              <Link to="/login">
                <Button variant="primary" size="sm">
                  Login
                </Button>
              </Link>
            )}

            {/* iOS user avatar - opens action sheet */}
            {showIOSLayout && isAuthenticated && (
              <button
                onClick={() => setIsUserActionSheetOpen(true)}
                className="flex items-center rounded-full focus:outline-none focus:ring-2 focus:ring-orange-500 active:opacity-70"
              >
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium text-white"
                  style={{ backgroundColor: '#e27b36' }}
                >
                  {getUserInitials()}
                </div>
              </button>
            )}
          </div>

          {/* Mobile Navigation Menu - hidden on iOS native */}
          {!showIOSLayout && isMobileMenuOpen && (
            <>
              {/* Overlay to close menu when clicking outside */}
              <div
                className="fixed inset-0 z-40"
                onClick={() => setIsMobileMenuOpen(false)}
                aria-hidden="true"
              />
              <div className="md:hidden border-t relative z-50" style={{borderColor: '#e8d7cf', backgroundColor: '#fcf9f8'}}>
                <div className="px-2 pt-2 pb-3 space-y-1">
                  {/* User info when authenticated */}
                  {isAuthenticated && (
                    <div className="px-3 py-3 mb-2 border-b" style={{ borderColor: '#e8d7cf' }}>
                      <div className="flex items-center space-x-3">
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium text-white"
                          style={{ backgroundColor: '#e27b36' }}
                        >
                          {getUserInitials()}
                        </div>
                        <div>
                          <p className="font-medium" style={{ color: '#1c120d' }}>
                            {user?.name || 'User'}
                          </p>
                          <p className="text-sm text-gray-500">{user?.email}</p>
                        </div>
                      </div>
                      {subscription?.is_premium && (
                        <span className="inline-block mt-2 px-2 py-0.5 text-xs font-semibold text-yellow-800 bg-yellow-100 rounded-full">
                          ⭐ Premium
                        </span>
                      )}
                    </div>
                  )}

                  {/* Navigation links */}
                  {navItems.map((item) => (
                    <Link
                      key={item.href}
                      to={item.href}
                      className="block px-3 py-2 rounded-md text-base font-medium transition-colors hover:text-orange-500"
                      style={{color: '#9b644b'}}
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      {item.label}
                    </Link>
                  ))}

                  {/* Auth-specific links */}
                  {isAuthenticated && (
                    <>
                      <Link
                        to="/profile"
                        className="block px-3 py-2 rounded-md text-base font-medium transition-colors hover:text-orange-500"
                        style={{color: '#9b644b'}}
                        onClick={() => setIsMobileMenuOpen(false)}
                      >
                        Profile
                      </Link>
                      <Link
                        to="/settings"
                        className="block px-3 py-2 rounded-md text-base font-medium transition-colors hover:text-orange-500"
                        style={{color: '#9b644b'}}
                        onClick={() => setIsMobileMenuOpen(false)}
                      >
                        Settings
                      </Link>
                    </>
                  )}

                  {/* Mobile Auth Actions */}
                  <div className="pt-4 border-t" style={{borderColor: '#e8d7cf'}}>
                    {isAuthenticated ? (
                      <div className="space-y-2">
                        {/* Upgrade option if not premium - opens external browser on iOS */}
                        {subscription && !subscription.is_premium && (
                          <button
                            onClick={() => {
                              setIsMobileMenuOpen(false);
                              handleUpgradeClick();
                            }}
                            className="w-full text-left px-3 py-2 rounded-md text-base font-medium transition-colors hover:bg-orange-50"
                            style={{ color: '#e27b36' }}
                          >
                            ⭐ Upgrade to Premium
                          </button>
                        )}
                        <Link
                          to="/upload"
                          className="block w-full"
                          onClick={() => setIsMobileMenuOpen(false)}
                        >
                          <Button variant="primary" size="md" className="w-full">
                            📷 Upload from Image
                          </Button>
                        </Link>
                        <Link
                          to="/upload?mode=url"
                          className="block w-full"
                          onClick={() => setIsMobileMenuOpen(false)}
                        >
                          <Button variant="secondary" size="md" className="w-full">
                            🔗 Import from URL
                          </Button>
                        </Link>
                        <Link
                          to="/recipes/create"
                          className="block w-full"
                          onClick={() => setIsMobileMenuOpen(false)}
                        >
                          <Button variant="secondary" size="md" className="w-full">
                            ✏️ Create Manually
                          </Button>
                        </Link>
                        <Button variant="secondary" size="sm" onClick={handleLogout} className="w-full mt-4">
                          Logout
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Link
                          to="/login"
                          className="block w-full"
                          onClick={() => setIsMobileMenuOpen(false)}
                        >
                          <Button variant="secondary" size="md" className="w-full">
                            Login
                          </Button>
                        </Link>
                        <Link
                          to="/register"
                          className="block w-full"
                          onClick={() => setIsMobileMenuOpen(false)}
                        >
                          <Button variant="primary" size="md" className="w-full">
                            Register
                          </Button>
                        </Link>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
        
        {/* Premium Upgrade Modal */}
        <PremiumUpgradeModal
          isOpen={showUpgradeModal}
          onClose={() => setShowUpgradeModal(false)}
          onSuccess={handleUpgradeSuccess}
        />
        
        {/* Beta Mode Restriction Modal */}
        <BetaModeRestrictionModal
          isOpen={betaModalState.isOpen}
          onClose={closeBetaModal}
          feature={betaModalState.feature}
          cookbookTitle={betaModalState.cookbookTitle}
          price={betaModalState.price}
        />

        {/* iOS User Action Sheet */}
        <ActionSheet
          isOpen={isUserActionSheetOpen}
          onClose={() => setIsUserActionSheetOpen(false)}
          title={user?.name || user?.email || 'Account'}
          options={[
            {
              label: 'Profile',
              onClick: () => navigate('/profile'),
            },
            {
              label: 'Settings',
              onClick: () => navigate('/settings'),
            },
            ...(subscription && !subscription.is_premium
              ? [{
                  label: 'Upgrade to Premium',
                  onClick: handleUpgradeClick,
                }]
              : []),
            {
              label: 'Logout',
              onClick: handleLogout,
              destructive: true,
            },
          ]}
        />

        {/* iOS Add Recipe Action Sheet */}
        <ActionSheet
          isOpen={isAddActionSheetOpen}
          onClose={() => setIsAddActionSheetOpen(false)}
          title="Add Recipe"
          options={[
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
          ]}
        />
      </header>
  );
};

export { Header };