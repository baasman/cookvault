import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { userApi } from '../../services/userApi';
import { StatCard } from '../user/StatCard';
import { QuickActions } from './QuickActions';
import { RecentActivity } from './RecentActivity';
import { AppStoreBanner } from '../homepage/AppStoreBanner';
import { OnboardingModal } from '../onboarding/OnboardingModal';

const ONBOARDING_KEY = 'cookle_has_seen_onboarding';
const COOKING_TIP_KEY = 'cookle_cooking_mode_tip_dismissed';

const AuthenticatedDashboard: React.FC = () => {
  const { user } = useAuth();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showCookingTip, setShowCookingTip] = useState(
    !localStorage.getItem(COOKING_TIP_KEY)
  );

  useEffect(() => {
    // Check if user has seen onboarding
    const hasSeenOnboarding = localStorage.getItem(ONBOARDING_KEY);
    if (!hasSeenOnboarding) {
      setShowOnboarding(true);
    }
  }, []);

  const handleOnboardingComplete = () => {
    localStorage.setItem(ONBOARDING_KEY, 'true');
    setShowOnboarding(false);
  };

  const {
    data: profileData,
    isLoading,
    error
  } = useQuery({
    queryKey: ['userProfile'],
    queryFn: () => userApi.fetchUserProfile(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const formatTime = (minutes: number) => {
    if (!minutes) return '0 min';
    const roundedMinutes = Math.round(minutes);
    if (roundedMinutes < 60) return `${roundedMinutes} min`;
    const hours = Math.floor(roundedMinutes / 60);
    const mins = roundedMinutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex justify-center py-12">
          <div className="text-center">
            <div
              className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4"
              style={{ borderColor: '#f15f1c' }}
            ></div>
            <p style={{ color: '#9b644b' }}>Loading your dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !profileData) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold mb-4" style={{ color: '#1c120d' }}>
            Unable to load dashboard
          </h2>
          <p className="mb-4" style={{ color: '#9b644b' }}>
            Please try refreshing the page.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg text-white"
            style={{ backgroundColor: '#f15f1c' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { statistics, recent_activity } = profileData;

  return (
    <>
      {showOnboarding && <OnboardingModal onComplete={handleOnboardingComplete} />}
      <AppStoreBanner />
      <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Welcome Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2" style={{ color: '#1c120d' }}>
          Welcome back, {user?.name || 'Chef'}!
        </h1>
        <p className="mb-4" style={{ color: '#9b644b' }}>
          Here's what's happening with your cookbook collection.
        </p>
        <QuickActions />
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Recipes"
          value={statistics.total_recipes}
          subtitle="recipes created"
          to="/recipes?filter=uploads"
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H7m5 0v-9a2 2 0 00-2-2H7a2 2 0 00-2 2v9m14 0h2"
              />
            </svg>
          }
        />

        <StatCard
          title="Total Cookbooks"
          value={statistics.total_cookbooks}
          subtitle="cookbooks owned"
          to="/cookbooks"
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
          }
        />

        <StatCard
          title="Avg Cook Time"
          value={formatTime(statistics.avg_cook_time_minutes)}
          subtitle="per recipe"
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />

        <StatCard
          title="Recipes per Cookbook"
          value={statistics.avg_recipes_per_cookbook}
          subtitle="on average"
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          }
        />
      </div>

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Left Column: Recent Activity */}
        <RecentActivity activities={recent_activity} />

        {/* Right Column: Quick Access */}
        <div className="space-y-6">
          {/* Most Popular Cookbook */}
          <div className="bg-white rounded-xl shadow-sm border p-6" style={{ borderColor: '#e8d7cf' }}>
            <h3 className="text-lg font-semibold mb-4" style={{ color: '#1c120d' }}>
              Most Popular Cookbook
            </h3>
            {statistics.most_popular_cookbook ? (
              <div className="text-center">
                <Link
                  to={`/cookbooks/${statistics.most_popular_cookbook.id}`}
                  className="hover:opacity-80 transition-opacity"
                  style={{ color: '#f15f1c' }}
                >
                  <h4 className="text-xl font-medium mb-2">
                    {statistics.most_popular_cookbook.title}
                  </h4>
                </Link>
                <p style={{ color: '#9b644b' }}>
                  {statistics.most_popular_cookbook.recipe_count} recipe
                  {statistics.most_popular_cookbook.recipe_count !== 1 ? 's' : ''}
                </p>
              </div>
            ) : (
              <div className="text-center" style={{ color: '#9b644b' }}>
                <p>No cookbooks yet</p>
                <Link
                  to="/cookbooks/create"
                  className="hover:opacity-80 transition-opacity text-sm"
                  style={{ color: '#f15f1c' }}
                >
                  Create your first cookbook
                </Link>
              </div>
            )}
          </div>

          {/* Quick Links */}
          <div className="bg-white rounded-xl shadow-sm border p-6" style={{ borderColor: '#e8d7cf' }}>
            <h3 className="text-lg font-semibold mb-4" style={{ color: '#1c120d' }}>
              Quick Links
            </h3>
            <div className="space-y-2">
              <Link
                to="/recipes"
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <span style={{ color: '#1c120d' }}>My Recipes</span>
                <svg
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  style={{ color: '#9b644b' }}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
              <Link
                to="/cookbooks"
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <span style={{ color: '#1c120d' }}>My Cookbooks</span>
                <svg
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  style={{ color: '#9b644b' }}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
              <Link
                to="/recipes"
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <span style={{ color: '#1c120d' }}>Browse Recipes</span>
                <svg
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  style={{ color: '#9b644b' }}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
              <Link
                to="/profile"
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <span style={{ color: '#1c120d' }}>Profile & Settings</span>
                <svg
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  style={{ color: '#9b644b' }}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>
          </div>

          {/* Cooking Mode Tip */}
          {showCookingTip && statistics.total_recipes > 0 && (
            <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-xl border p-5 relative" style={{ borderColor: '#e8d7cf' }}>
              <button
                onClick={() => {
                  localStorage.setItem(COOKING_TIP_KEY, 'true');
                  setShowCookingTip(false);
                }}
                className="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: '#f15f1c' }}>
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-sm mb-1" style={{ color: '#1c120d' }}>Try Cooking Mode</h4>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    Follow recipes step-by-step with smart timers and personal notes. Open any recipe and tap "Start Cooking".
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
    </>
  );
};

export { AuthenticatedDashboard };
