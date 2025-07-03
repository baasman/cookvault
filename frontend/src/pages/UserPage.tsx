import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { userApi } from '../services/userApi';
import { ProfileHeader } from '../components/user/ProfileHeader';
import { StatCard } from '../components/user/StatCard';
import { Button } from '../components/ui';

const UserPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const { 
    data: profileData, 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['userProfile'],
    queryFn: () => userApi.fetchUserProfile(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const formatTime = (minutes: number) => {
    if (!minutes) return '0 min';
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '';
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Please log in to view your profile
        </h2>
        <Button onClick={() => navigate('/login')}>
          Sign In
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
          <p style={{color: '#9b644b'}}>Loading profile...</p>
        </div>
      </div>
    );
  }

  if (error || !profileData) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Error loading profile
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          Unable to load your profile information. Please try again.
        </p>
        <Button onClick={() => window.location.reload()}>
          Retry
        </Button>
      </div>
    );
  }

  const { user, statistics, recent_activity } = profileData;

  return (
    <div className="max-w-6xl mx-auto">
      {/* Profile Header */}
      <ProfileHeader user={user} />

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Recipes"
          value={statistics.total_recipes}
          subtitle="recipes created"
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H7m5 0v-9a2 2 0 00-2-2H7a2 2 0 00-2 2v9m14 0h2" />
            </svg>
          }
        />

        <StatCard
          title="Total Cookbooks"
          value={statistics.total_cookbooks}
          subtitle="cookbooks owned"
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          }
        />

        <StatCard
          title="Avg Cook Time"
          value={formatTime(statistics.avg_cook_time_minutes)}
          subtitle="per recipe"
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />

        <StatCard
          title="Recipes per Cookbook"
          value={statistics.avg_recipes_per_cookbook}
          subtitle="on average"
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
      </div>

      {/* Secondary Statistics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Recipe Difficulty Breakdown */}
        <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
          <h3 className="text-lg font-semibold text-text-primary mb-4">Recipe Difficulty</h3>
          <div className="space-y-3">
            {Object.entries(statistics.difficulty_breakdown).map(([difficulty, count]) => {
              const total = statistics.total_recipes;
              const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
              const colors = {
                easy: '#22c55e',
                medium: '#f59e0b', 
                hard: '#ef4444',
                unspecified: '#9b644b'
              };
              
              return (
                <div key={difficulty} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div 
                      className="w-3 h-3 rounded-full"
                      style={{backgroundColor: colors[difficulty as keyof typeof colors]}}
                    ></div>
                    <span className="text-sm font-medium text-text-primary capitalize">
                      {difficulty}
                    </span>
                  </div>
                  <div className="text-sm text-text-secondary">
                    {count} ({percentage}%)
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Most Popular Cookbook */}
        <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
          <h3 className="text-lg font-semibold text-text-primary mb-4">Most Popular Cookbook</h3>
          {statistics.most_popular_cookbook ? (
            <div className="text-center">
              <Link 
                to={`/cookbooks/${statistics.most_popular_cookbook.id}`}
                className="text-accent hover:text-accent/80 transition-colors"
              >
                <h4 className="text-xl font-medium mb-2">
                  {statistics.most_popular_cookbook.title}
                </h4>
              </Link>
              <p className="text-text-secondary">
                {statistics.most_popular_cookbook.recipe_count} recipe{statistics.most_popular_cookbook.recipe_count !== 1 ? 's' : ''}
              </p>
            </div>
          ) : (
            <div className="text-center text-text-secondary">
              <p>No recipes in cookbooks yet</p>
              <Link to="/upload" className="text-accent hover:text-accent/80 transition-colors text-sm">
                Upload your first recipe
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
        <h3 className="text-lg font-semibold text-text-primary mb-4">Recent Activity</h3>
        {recent_activity.length > 0 ? (
          <div className="space-y-3">
            {recent_activity.map((activity) => (
              <div key={`${activity.type}-${activity.id}`} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-accent rounded-full"></div>
                  <div>
                    <Link 
                      to={`/recipes/${activity.id}`}
                      className="font-medium text-text-primary hover:text-accent transition-colors"
                    >
                      {activity.title}
                    </Link>
                    {activity.cookbook_title && (
                      <p className="text-sm text-text-secondary">
                        from {activity.cookbook_title}
                      </p>
                    )}
                  </div>
                </div>
                <span className="text-sm text-text-secondary">
                  {formatDate(activity.created_at)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-text-secondary py-8">
            <p className="mb-2">No recent activity</p>
            <Link to="/upload" className="text-accent hover:text-accent/80 transition-colors">
              Upload your first recipe
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export { UserPage };