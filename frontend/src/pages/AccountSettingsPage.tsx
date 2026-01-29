import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { SubscriptionStatus } from '../components/payments';
import { Button } from '../components/ui';

const AccountSettingsPage: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{ color: '#1c120d' }}>
          Please log in to view account settings
        </h2>
        <Button onClick={() => navigate('/login')}>Sign In</Button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-8" style={{ color: '#1c120d' }}>
        Account Settings
      </h1>

      {/* Subscription Section */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4" style={{ color: '#1c120d' }}>
          Subscription
        </h2>
        <SubscriptionStatus showUpgradeButton={true} />
      </section>

      {/* Profile Section */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4" style={{ color: '#1c120d' }}>
          Profile
        </h2>
        <div
          className="bg-white rounded-lg border p-6"
          style={{ borderColor: '#e8d7cf' }}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-500">
                Username
              </label>
              <p className="mt-1 text-gray-900">{user?.name}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500">
                Email
              </label>
              <p className="mt-1 text-gray-900">{user?.email}</p>
            </div>
            <div className="pt-4 flex gap-3">
              <Link to="/profile/edit">
                <Button variant="secondary" size="sm">
                  Edit Profile
                </Button>
              </Link>
              <Link to="/profile/change-password">
                <Button variant="secondary" size="sm">
                  Change Password
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Danger Zone */}
      <section>
        <h2 className="text-xl font-semibold mb-4 text-red-600">Danger Zone</h2>
        <div className="bg-red-50 rounded-lg border border-red-200 p-6">
          <p className="text-gray-600 mb-4">
            Once you delete your account, there is no going back. Please be
            certain.
          </p>
          <Button
            variant="secondary"
            size="sm"
            className="text-red-600 border-red-300 hover:bg-red-100"
            onClick={() => {
              alert(
                'Account deletion is not yet implemented. Please contact support.'
              );
            }}
          >
            Delete Account
          </Button>
        </div>
      </section>
    </div>
  );
};

export { AccountSettingsPage };
