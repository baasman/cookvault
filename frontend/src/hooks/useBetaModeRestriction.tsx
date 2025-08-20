import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface BetaRestrictionState {
  isOpen: boolean;
  feature: 'premium' | 'cookbook';
  cookbookTitle?: string;
  price?: number;
}

export const useBetaModeRestriction = () => {
  const { user, isAuthenticated } = useAuth();
  const [betaModalState, setBetaModalState] = useState<BetaRestrictionState>({
    isOpen: false,
    feature: 'premium',
  });

  // Check if user should be restricted (non-admin authenticated users)
  const isBetaRestricted = isAuthenticated && user?.role !== 'admin';

  const checkBetaRestriction = (
    feature: 'premium' | 'cookbook',
    options?: { cookbookTitle?: string; price?: number }
  ): boolean => {
    if (isBetaRestricted) {
      setBetaModalState({
        isOpen: true,
        feature,
        cookbookTitle: options?.cookbookTitle,
        price: options?.price,
      });
      return true; // Restricted
    }
    return false; // Not restricted
  };

  const closeBetaModal = () => {
    setBetaModalState(prev => ({ ...prev, isOpen: false }));
  };

  return {
    isBetaRestricted,
    betaModalState,
    checkBetaRestriction,
    closeBetaModal,
  };
};