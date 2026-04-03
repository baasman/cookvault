import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { userApi } from '../services/userApi';
import { formatDateShort } from '../utils/formatters';
import { StatCard } from '../components/user/StatCard';

const PublicUserPage: React.FC = () => {
  const { userId, username } = useParams<{ userId?: string; username?: string }>();

  const { 
    data: profileData, 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['publicUserProfile', userId, username],
    queryFn: () => {
      if (userId) {
        return userApi.fetchPublicUserProfile(parseInt(userId, 10));
      } else if (username) {
        return userApi.fetchPublicUserByUsername(username);
      } else {
        throw new Error('No user ID or username provided');
      }
    },
    enabled: Boolean(userId || username),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const formatMemberSince = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long'
      });
    } catch {
      return 'Unknown';
    }
  };

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
          User Not Found
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          This user profile doesn't exist or is not available.
        </p>
        <Link 
          to="/recipes"
          className="inline-block px-6 py-2 rounded-full font-bold transition-colors"
          style={{backgroundColor: '#f15f1c', color: 'white'}}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#d54c15'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#f15f1c'}
        >
          Browse Recipes
        </Link>
      </div>
    );
  }

  const { user, statistics, recent_activity } = profileData;

  return (
    <div className="max-w-6xl mx-auto">
      {/* Profile Header - Modified version for public profile */}
      <div className="bg-white rounded-xl shadow-sm border p-8 mb-8" style={{borderColor: '#e8d7cf'}}>
        <div className="flex items-center space-x-6">
          {/* Avatar */}
          <div className="w-20 h-20 rounded-full flex-shrink-0 overflow-hidden" style={{backgroundColor: '#f1ece9'}}>
            {user.avatar_url ? (
              <img 
                src={user.avatar_url} 
                alt={`${user.username}'s avatar`}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <svg className="w-10 h-10" style={{color: '#f15f1c'}} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
                </svg>
              </div>
            )}
          </div>
          
          {/* User Info */}
          <div className="flex-grow">
            <h1 className="text-3xl font-bold mb-2" style={{color: '#1c120d'}}>
              {user.first_name && user.last_name 
                ? `${user.first_name} ${user.last_name}` 
                : user.username}
            </h1>
            {user.first_name && user.last_name && (
              <p className="text-lg mb-2" style={{color: '#9b644b'}}>@{user.username}</p>
            )}
            {user.bio && (
              <p className="text-base mb-4" style={{color: '#9b644b'}}>{user.bio}</p>
            )}
            <div className="flex items-center text-sm" style={{color: '#9b644b'}}>
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span>Member since {formatMemberSince(statistics.member_since)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="Public Recipes"
          value={statistics.total_public_recipes}
          subtitle="recipes shared publicly"
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
          title="Member Since"
          value={formatMemberSince(statistics.member_since)}
          subtitle="sharing recipes"
          icon={
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          }
        />
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
        <h3 className="text-lg font-semibold text-text-primary mb-4">Recent Public Recipes</h3>
        {recent_activity.length > 0 ? (
          <div className="space-y-3">
            {recent_activity.map((activity: any) => (
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
                  {formatDateShort(activity.created_at)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-text-secondary py-8">
            <p className="mb-2">No public recipes yet</p>
            <p className="text-sm">This user hasn't shared any recipes publicly.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export { PublicUserPage };