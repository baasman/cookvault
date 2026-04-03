import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Button } from '../ui/Button';
import { paymentsApi, type Subscription } from '../../services/paymentsApi';
import { PremiumUpgradeModal } from './PremiumUpgradeModal';
import { isNativePlatform } from '../../utils/platform';

interface SubscriptionStatusProps {
  className?: string;
  showUpgradeButton?: boolean;
}

export const SubscriptionStatus: React.FC<SubscriptionStatusProps> = ({
  className = '',
  showUpgradeButton = true,
}) => {
  const navigate = useNavigate();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [isCanceling, setIsCanceling] = useState(false);

  const loadSubscription = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const subData = await paymentsApi.getUserSubscription();
      setSubscription(subData);
    } catch (err) {
      console.error('Failed to load subscription:', err);
      setError(err instanceof Error ? err.message : 'Failed to load subscription');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSubscription();
  }, []);

  const handleCancelSubscription = async () => {
    if (!subscription?.is_premium) return;
    
    const confirmed = window.confirm(
      'Are you sure you want to cancel your premium subscription? You will lose access to premium features at the end of your current billing period.'
    );
    
    if (!confirmed) return;

    try {
      setIsCanceling(true);
      await paymentsApi.cancelSubscription();
      await loadSubscription(); // Refresh subscription data
    } catch (err) {
      console.error('Failed to cancel subscription:', err);
      toast.error('Failed to cancel subscription. Please try again.');
    } finally {
      setIsCanceling(false);
    }
  };

  const handleUpgradeSuccess = () => {
    loadSubscription(); // Refresh subscription data
  };

  // Handler for upgrade action - navigate to upgrade page on native, show modal on web
  const handleUpgradeClick = async () => {
    if (isNativePlatform()) {
      navigate('/upgrade');
    } else {
      setShowUpgradeModal(true);
    }
  };

  if (isLoading) {
    return (
      <div className={`animate-pulse ${className}`}>
        <div className="h-20 bg-gray-200 rounded-lg"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}>
        <p className="text-red-700 text-sm">{error}</p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-2"
          onClick={loadSubscription}
        >
          Retry
        </Button>
      </div>
    );
  }

  if (!subscription) {
    return null;
  }

  const isPremium = subscription.is_premium;
  const hasUnlimitedUploads = subscription.remaining_uploads === -1;
  // const isCanceled = subscription.canceled_at !== null;
  const willCancel = subscription.cancel_at_period_end;

  return (
    <div className={className}>
      <div className={`rounded-lg p-4 border ${isPremium || hasUnlimitedUploads ? 'bg-gradient-to-r from-purple-50 to-indigo-50 border-indigo-200' : 'bg-gray-50 border-gray-200'}`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-gray-900">
                {isPremium || hasUnlimitedUploads ? 'Premium Plan' : 'Free Plan'}
              </h3>
              {(isPremium || hasUnlimitedUploads) && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                  {hasUnlimitedUploads && !isPremium ? 'Admin' : 'Premium'}
                </span>
              )}
              {willCancel && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                  Canceling
                </span>
              )}
            </div>
            
            <div className="text-sm text-gray-600">
              {isPremium || subscription.remaining_uploads === -1 ? (
                <div>
                  <p>Unlimited recipe uploads</p>
                  {subscription.current_period_end && (
                    <p className="mt-1">
                      {willCancel ? 'Access expires' : 'Renews'}: {' '}
                      {new Date(subscription.current_period_end).toLocaleDateString()}
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  {(() => {
                    const totalLimit = subscription.remaining_uploads + subscription.monthly_upload_count;
                    return (
                      <>
                        <p>
                          {subscription.remaining_uploads} of {totalLimit} uploads remaining this month
                        </p>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{
                              width: `${totalLimit > 0 ? Math.max(0, (subscription.remaining_uploads / totalLimit) * 100) : 0}%`
                            }}
                          ></div>
                        </div>
                      </>
                    );
                  })()}
                </div>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            {/* Upgrade button - opens external browser on iOS (App Store Guideline 3.1.1) */}
            {!isPremium && !hasUnlimitedUploads && showUpgradeButton && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleUpgradeClick}
              >
                Upgrade to Premium
              </Button>
            )}

            {isPremium && !willCancel && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleCancelSubscription}
                disabled={isCanceling}
              >
                {isCanceling ? 'Canceling...' : 'Cancel Plan'}
              </Button>
            )}
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