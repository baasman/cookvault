import React from 'react';
import type { UserInfo } from '../../types';

interface ProfileHeaderProps {
  user: UserInfo;
}

const ProfileHeader: React.FC<ProfileHeaderProps> = ({ user }) => {
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch {
      return '';
    }
  };

  const getDisplayName = () => {
    if (user.first_name || user.last_name) {
      return `${user.first_name || ''} ${user.last_name || ''}`.trim();
    }
    return user.username;
  };

  const getInitials = () => {
    if (user.first_name || user.last_name) {
      const first = user.first_name?.charAt(0) || '';
      const last = user.last_name?.charAt(0) || '';
      return `${first}${last}`.toUpperCase();
    }
    return user.username.slice(0, 2).toUpperCase();
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border p-8 mb-8" style={{borderColor: '#e8d7cf'}}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-6">
        {/* Avatar */}
        <div className="flex-shrink-0 mb-4 sm:mb-0">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={getDisplayName()}
              className="w-20 h-20 rounded-full object-cover"
            />
          ) : (
            <div 
              className="w-20 h-20 rounded-full flex items-center justify-center text-white text-xl font-bold"
              style={{backgroundColor: '#f15f1c'}}
            >
              {getInitials()}
            </div>
          )}
        </div>

        {/* User Info */}
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-text-primary mb-2">
            {getDisplayName()}
          </h1>
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-sm text-text-secondary">
            <span>@{user.username}</span>
            {user.email && (
              <>
                <span className="hidden sm:inline">•</span>
                <span>{user.email}</span>
              </>
            )}
            <span className="hidden sm:inline">•</span>
            <span>Joined {formatDate(user.created_at)}</span>
          </div>
          
          {user.bio && (
            <p className="mt-3 text-text-secondary leading-relaxed">
              {user.bio}
            </p>
          )}

          {/* Status indicators */}
          <div className="flex items-center gap-3 mt-4">
            <span 
              className={`px-2 py-1 text-xs font-medium rounded-full ${
                user.role === 'admin' 
                  ? 'bg-red-100 text-red-800' 
                  : 'bg-blue-100 text-blue-800'
              }`}
            >
              {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
            </span>
            
            {user.is_verified && (
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                Verified
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export { ProfileHeader };