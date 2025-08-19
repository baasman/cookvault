import React, { useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { paymentsApi, type Subscription } from '../../services/paymentsApi';
import { PremiumUpgradeModal } from './PremiumUpgradeModal';

interface UploadLimitWarningProps {
  onUpgradeSuccess?: () => void;
  className?: string;
}

export const UploadLimitWarning: React.FC<UploadLimitWarningProps> = ({
  onUpgradeSuccess,
  className = '',
}) => {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  useEffect(() => {
    const loadSubscription = async () => {
      try {
        const subData = await paymentsApi.getUserSubscription();
        setSubscription(subData);
      } catch (err) {
        console.error('Failed to load subscription:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadSubscription();
  }, []);

  const handleUpgradeSuccess = () => {
    // Refresh subscription data
    setSubscription(prev => prev ? { ...prev, tier: 'premium', is_premium: true, can_upload: true } : null);
    onUpgradeSuccess?.();
  };

  if (isLoading || !subscription) {
    return null;
  }

  // Don't show warning if user is premium or can still upload
  if (subscription.is_premium || subscription.can_upload) {
    return null;
  }

  return (
    <div className={className}>
      <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-orange-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-orange-800">
              Upload Limit Reached
            </h3>
            <div className="mt-2 text-sm text-orange-700">
              <p>
                You've used all {subscription.monthly_upload_count} of your free uploads this month. 
                Upgrade to Premium for unlimited uploads and access to advanced features.
              </p>
            </div>
            <div className="mt-4">
              <div className="flex">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setShowUpgradeModal(true)}
                >
                  Upgrade to Premium
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  className="ml-3"
                  onClick={() => {
                    // You could implement a "learn more" modal here
                    window.open('/pricing', '_blank');
                  }}
                >
                  Learn More
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <PremiumUpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        onSuccess={handleUpgradeSuccess}
      />
    </div>
  );
};

// Hook to check if user can upload
export const useCanUpload = () => {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadSubscription = async () => {
      try {
        const subData = await paymentsApi.getUserSubscription();
        setSubscription(subData);
      } catch (err) {
        console.error('Failed to load subscription:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadSubscription();
  }, []);

  return {
    canUpload: subscription?.can_upload ?? false,
    isPremium: subscription?.is_premium ?? false,
    remainingUploads: subscription?.remaining_uploads ?? 0,
    isLoading,
    subscription,
  };
};