import React from 'react';
import { Link } from 'react-router-dom';

interface ActivityItem {
  type: string;
  id: number;
  title: string;
  created_at: string;
  cookbook_title?: string;
}

interface RecentActivityProps {
  activities: ActivityItem[];
}

const RecentActivity: React.FC<RecentActivityProps> = ({ activities }) => {
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

  if (activities.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border p-6" style={{ borderColor: '#e8d7cf' }}>
        <h3 className="text-lg font-semibold mb-4" style={{ color: '#1c120d' }}>Recent Activity</h3>
        <div className="text-center py-8" style={{ color: '#9b644b' }}>
          <svg
            className="w-12 h-12 mx-auto mb-3 opacity-50"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <p className="mb-2">No recent activity</p>
          <Link
            to="/upload"
            className="hover:opacity-80 transition-opacity"
            style={{ color: '#f15f1c' }}
          >
            Upload your first recipe
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6" style={{ borderColor: '#e8d7cf' }}>
      <h3 className="text-lg font-semibold mb-4" style={{ color: '#1c120d' }}>Recent Activity</h3>
      <div className="space-y-3">
        {activities.map((activity) => (
          <div
            key={`${activity.type}-${activity.id}`}
            className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0"
          >
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#f15f1c' }}></div>
              <div>
                <Link
                  to={`/recipes/${activity.id}`}
                  className="font-medium transition-colors hover:opacity-80"
                  style={{ color: '#1c120d' }}
                >
                  {activity.title}
                </Link>
                {activity.cookbook_title && (
                  <p className="text-sm" style={{ color: '#9b644b' }}>
                    from {activity.cookbook_title}
                  </p>
                )}
              </div>
            </div>
            <span className="text-sm" style={{ color: '#9b644b' }}>
              {formatDate(activity.created_at)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export { RecentActivity };
