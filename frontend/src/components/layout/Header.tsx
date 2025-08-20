import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../ui/Button';
import { useAuth } from '../../contexts/AuthContext';
import { PremiumUpgradeModal } from '../payments/PremiumUpgradeModal';
import { paymentsApi, type Subscription } from '../../services/paymentsApi';
import type { NavItem } from '../../types';

interface HeaderProps {
  navItems?: NavItem[];
}

const Header: React.FC<HeaderProps> = ({ 
  navItems = [
    { label: 'Recipes', href: '/recipes' },
    { label: 'Cookbooks', href: '/cookbooks' }
  ]
}) => {
  const { isAuthenticated, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [subscription, setSubscription] = useState<Subscription | null>(null);

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

  // Add Profile to navigation only when authenticated
  const displayNavItems = isAuthenticated 
    ? [...navItems, { label: 'Profile', href: '/profile' }]
    : navItems;

  return (
    <header className="border-b sticky top-0 z-50" style={{backgroundColor: '#fcf9f8', borderColor: '#e8d7cf'}}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex-shrink-0">
              <Link to="/" className="flex items-center">
                <span className="text-2xl font-bold" style={{color: '#1c120d'}}>
                  Cookle
                </span>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-8">
              {displayNavItems.map((item) => (
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
            <div className="hidden md:flex items-center space-x-4">
              {isAuthenticated ? (
                <>
                  <div className="flex items-center space-x-2">
                    {/* Show upgrade button if not premium */}
                    {subscription && !subscription.is_premium && (
                      <Button 
                        variant="primary" 
                        size="sm"
                        onClick={() => setShowUpgradeModal(true)}
                        className="bg-gradient-to-r from-yellow-400 to-orange-500 hover:from-yellow-500 hover:to-orange-600 text-white"
                      >
                        ⭐ Upgrade to Premium
                      </Button>
                    )}
                    {/* Show premium badge if premium */}
                    {subscription && subscription.is_premium && (
                      <span className="px-3 py-1 text-xs font-semibold text-yellow-800 bg-yellow-100 rounded-full">
                        ⭐ Premium
                      </span>
                    )}
                    <Link to="/recipes/create">
                      <Button variant="secondary" size="md">
                        Create Recipe
                      </Button>
                    </Link>
                    <Link to="/upload">
                      <Button variant="primary" size="md">
                        Upload Recipe
                      </Button>
                    </Link>
                  </div>
                  <Button variant="secondary" size="sm" onClick={handleLogout}>
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Link to="/login">
                    <Button variant="secondary" size="md">
                      Login
                    </Button>
                  </Link>
                  <Link to="/register">
                    <Button variant="primary" size="md">
                      Register
                    </Button>
                  </Link>
                </>
              )}
            </div>

            {/* Mobile menu button */}
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
          </div>

          {/* Mobile Navigation Menu */}
          {isMobileMenuOpen && (
            <div className="md:hidden border-t" style={{borderColor: '#e8d7cf'}}>
              <div className="px-2 pt-2 pb-3 space-y-1">
                {displayNavItems.map((item) => (
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
                
                {/* Mobile Auth Actions */}
                <div className="pt-4 border-t" style={{borderColor: '#e8d7cf'}}>
                  {isAuthenticated ? (
                    <div className="space-y-2">
                      {/* Show upgrade button if not premium */}
                      {subscription && !subscription.is_premium && (
                        <Button 
                          variant="primary" 
                          size="md"
                          onClick={() => {
                            setShowUpgradeModal(true);
                            setIsMobileMenuOpen(false);
                          }}
                          className="w-full bg-gradient-to-r from-yellow-400 to-orange-500 hover:from-yellow-500 hover:to-orange-600 text-white"
                        >
                          ⭐ Upgrade to Premium
                        </Button>
                      )}
                      {/* Show premium badge if premium */}
                      {subscription && subscription.is_premium && (
                        <div className="text-center py-2">
                          <span className="px-3 py-1 text-xs font-semibold text-yellow-800 bg-yellow-100 rounded-full">
                            ⭐ Premium Member
                          </span>
                        </div>
                      )}
                      <Link
                        to="/recipes/create"
                        className="block w-full"
                        onClick={() => setIsMobileMenuOpen(false)}
                      >
                        <Button variant="secondary" size="md" className="w-full">
                          Create Recipe
                        </Button>
                      </Link>
                      <Link
                        to="/upload"
                        className="block w-full"
                        onClick={() => setIsMobileMenuOpen(false)}
                      >
                        <Button variant="primary" size="md" className="w-full">
                          Upload Recipe
                        </Button>
                      </Link>
                      <Button variant="secondary" size="sm" onClick={handleLogout} className="w-full">
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
          )}
        </div>
        
        {/* Premium Upgrade Modal */}
        <PremiumUpgradeModal
          isOpen={showUpgradeModal}
          onClose={() => setShowUpgradeModal(false)}
          onSuccess={handleUpgradeSuccess}
        />
      </header>
  );
};

export { Header };