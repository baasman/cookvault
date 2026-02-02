import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { SubscriptionStatus } from '../components/payments';
import { Button, Modal, Input } from '../components/ui';

interface DeletionStatus {
  is_pending_deletion: boolean;
  deletion_scheduled_for: string | null;
  can_cancel: boolean;
}

const AccountSettingsPage: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  const [deletionStatus, setDeletionStatus] = useState<DeletionStatus | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      fetchDeletionStatus();
    }
  }, [isAuthenticated]);

  const fetchDeletionStatus = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/auth/account/deletion-status', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setDeletionStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch deletion status:', error);
    }
  };

  const handleRequestDeletion = async () => {
    if (!deletePassword) {
      setDeleteError('Please enter your password to confirm');
      return;
    }

    setIsDeleting(true);
    setDeleteError(null);

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/auth/account', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ password: deletePassword }),
      });

      const data = await response.json();

      if (!response.ok) {
        setDeleteError(data.error || 'Failed to schedule deletion');
        return;
      }

      setShowDeleteModal(false);
      setDeletePassword('');
      await fetchDeletionStatus();
    } catch (error) {
      console.error('Failed to request deletion:', error);
      setDeleteError('An error occurred. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelDeletion = async () => {
    setIsCancelling(true);

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/auth/account/cancel-deletion', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        await fetchDeletionStatus();
      }
    } catch (error) {
      console.error('Failed to cancel deletion:', error);
    } finally {
      setIsCancelling(false);
    }
  };

  const formatDeletionDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const handleExportData = async () => {
    setIsExporting(true);

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/auth/export', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      // Get the filename from the Content-Disposition header or use a default
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'cookle_data_export.zip';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match) {
          filename = match[1];
        }
      }

      // Download the file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export data:', error);
      alert('Failed to export data. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

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

      {/* Pending Deletion Banner */}
      {deletionStatus?.is_pending_deletion && (
        <div className="mb-8 bg-amber-50 border border-amber-300 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg
              className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <div className="flex-1">
              <h3 className="font-semibold text-amber-800">
                Account Scheduled for Deletion
              </h3>
              <p className="text-amber-700 mt-1">
                Your account will be permanently deleted on{' '}
                <strong>
                  {deletionStatus.deletion_scheduled_for
                    ? formatDeletionDate(deletionStatus.deletion_scheduled_for)
                    : 'soon'}
                </strong>
                . All your recipes, cookbooks, and data will be removed.
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-3"
                onClick={handleCancelDeletion}
                disabled={isCancelling}
              >
                {isCancelling ? 'Cancelling...' : 'Cancel Deletion'}
              </Button>
            </div>
          </div>
        </div>
      )}

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

      {/* Notifications Section */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4" style={{ color: '#1c120d' }}>
          Notifications
        </h2>
        <div
          className="bg-white rounded-lg border p-6"
          style={{ borderColor: '#e8d7cf' }}
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-gray-900">Email Notifications</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Receive updates about your account, new features, and tips.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  defaultChecked
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-600"></div>
              </label>
            </div>
            <div className="flex items-center justify-between pt-4 border-t border-gray-200">
              <div>
                <h3 className="font-medium text-gray-900">Recipe Tips</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Get occasional cooking tips and recipe suggestions.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  defaultChecked
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-600"></div>
              </label>
            </div>
          </div>
        </div>
      </section>

      {/* Data & Privacy Section */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4" style={{ color: '#1c120d' }}>
          Data & Privacy
        </h2>
        <div
          className="bg-white rounded-lg border p-6"
          style={{ borderColor: '#e8d7cf' }}
        >
          <div className="space-y-4">
            <div>
              <h3 className="font-medium text-gray-900">Download Your Data</h3>
              <p className="text-sm text-gray-600 mt-1">
                Export all your recipes, cookbooks, and profile information in a
                portable format.
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-3"
                onClick={handleExportData}
                disabled={isExporting}
              >
                {isExporting ? 'Preparing Download...' : 'Download My Data'}
              </Button>
            </div>
            <div className="pt-4 border-t border-gray-200">
              <h3 className="font-medium text-gray-900">Privacy Policy</h3>
              <p className="text-sm text-gray-600 mt-1">
                Learn how we collect, use, and protect your data.
              </p>
              <Link to="/privacy-policy">
                <Button variant="secondary" size="sm" className="mt-3">
                  View Privacy Policy
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Danger Zone */}
      {!deletionStatus?.is_pending_deletion && (
        <section>
          <h2 className="text-xl font-semibold mb-4 text-red-600">Danger Zone</h2>
          <div className="bg-red-50 rounded-lg border border-red-200 p-6">
            <h3 className="font-medium text-red-800">Delete Account</h3>
            <p className="text-gray-600 mt-2">
              Once you request account deletion, you'll have 7 days to change your
              mind. After that, all your data will be permanently deleted,
              including:
            </p>
            <ul className="list-disc list-inside text-gray-600 mt-2 text-sm">
              <li>All your recipes and images</li>
              <li>All your cookbooks</li>
              <li>Your profile and account information</li>
              <li>Your subscription (if any)</li>
            </ul>
            <Button
              variant="secondary"
              size="sm"
              className="mt-4 text-red-600 border-red-300 hover:bg-red-100"
              onClick={() => setShowDeleteModal(true)}
            >
              Delete Account
            </Button>
          </div>
        </section>
      )}

      {/* About Section */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4" style={{ color: '#1c120d' }}>
          About
        </h2>
        <div
          className="bg-white rounded-lg border p-6"
          style={{ borderColor: '#e8d7cf' }}
        >
          <div className="space-y-4">
            <div>
              <h3 className="font-medium text-gray-900">Cookle</h3>
              <p className="text-sm text-gray-600 mt-1">
                Version 1.0.0
              </p>
            </div>
            <div className="pt-4 border-t border-gray-200">
              <h3 className="font-medium text-gray-900">Support</h3>
              <p className="text-sm text-gray-600 mt-1">
                Have questions or feedback? We'd love to hear from you.
              </p>
              <a
                href="mailto:boudeyz@gmail.com"
                className="inline-block mt-2 text-sm text-amber-600 hover:text-amber-700"
              >
                Contact Support
              </a>
            </div>
            <div className="pt-4 border-t border-gray-200">
              <h3 className="font-medium text-gray-900">Legal</h3>
              <div className="flex flex-wrap gap-4 mt-2">
                <Link
                  to="/terms-of-service"
                  className="text-sm text-amber-600 hover:text-amber-700"
                >
                  Terms of Service
                </Link>
                <Link
                  to="/privacy-policy"
                  className="text-sm text-amber-600 hover:text-amber-700"
                >
                  Privacy Policy
                </Link>
                <Link
                  to="/copyright-policy"
                  className="text-sm text-amber-600 hover:text-amber-700"
                >
                  Copyright Policy
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setDeletePassword('');
          setDeleteError(null);
        }}
      >
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Delete Your Account
          </h2>

          <div className="space-y-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 text-sm">
                This action will schedule your account for permanent deletion. You'll
                have 7 days to cancel this request before all your data is
                permanently removed.
              </p>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-2">
                What will be deleted:
              </h4>
              <ul className="list-disc list-inside text-gray-600 text-sm space-y-1">
                <li>All your recipes and images</li>
                <li>All your cookbooks</li>
                <li>Your profile information</li>
                <li>Your subscription will be cancelled</li>
              </ul>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Enter your password to confirm
              </label>
              <Input
                type="password"
                value={deletePassword}
                onChange={(value) => setDeletePassword(value)}
                placeholder="Your password"
              />
            </div>

            {deleteError && (
              <p className="text-red-600 text-sm">{deleteError}</p>
            )}

            <div className="flex gap-3 justify-end pt-4">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeletePassword('');
                  setDeleteError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleRequestDeletion}
                disabled={isDeleting || !deletePassword}
                className="bg-red-600 hover:bg-red-700"
              >
                {isDeleting ? 'Scheduling...' : 'Delete My Account'}
              </Button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export { AccountSettingsPage };
