import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../contexts/AuthContext';
import { userApi } from '../services/userApi';
import { Button } from '../components/ui';

interface PasswordFormData {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

const ChangePasswordPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [passwordData, setPasswordData] = useState<PasswordFormData>({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({});
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  const validatePasswordForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!passwordData.current_password) {
      newErrors.current_password = 'Current password is required';
    }

    if (!passwordData.new_password) {
      newErrors.new_password = 'New password is required';
    } else if (passwordData.new_password.length < 8) {
      newErrors.new_password = 'Password must be at least 8 characters';
    }

    if (!passwordData.confirm_password) {
      newErrors.confirm_password = 'Please confirm your new password';
    } else if (passwordData.new_password !== passwordData.confirm_password) {
      newErrors.confirm_password = 'Passwords do not match';
    }

    setPasswordErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validatePasswordForm()) return;

    setIsChangingPassword(true);
    setPasswordSuccess(false);

    try {
      await userApi.changePassword(passwordData.current_password, passwordData.new_password);

      // Clear the password form
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });

      // Show success message
      setPasswordSuccess(true);

      // Clear success message after 5 seconds
      setTimeout(() => setPasswordSuccess(false), 5000);
    } catch (error) {
      console.error('Failed to change password:', error);
      setPasswordErrors({ submit: error instanceof Error ? error.message : 'Failed to change password. Please try again.' });
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handlePasswordInputChange = (field: keyof PasswordFormData, value: string) => {
    setPasswordData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (passwordErrors[field]) {
      setPasswordErrors(prev => ({ ...prev, [field]: '' }));
    }
    // Clear success message when user starts typing
    if (passwordSuccess) {
      setPasswordSuccess(false);
    }
  };

  if (!isAuthenticated) {
    navigate('/login');
    return null;
  }

  return (
    <div className="max-w-2xl mx-auto py-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate('/profile')}
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeftIcon className="w-4 h-4 mr-1" />
          Back to Profile
        </button>
        <h1 className="text-3xl font-bold text-gray-900">Change Password</h1>
        <p className="mt-2 text-gray-600">Update your password to keep your account secure</p>
      </div>

      {/* Password Change Form */}
      <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
        <form onSubmit={handlePasswordChange} className="space-y-4">
          {/* Current Password */}
          <div>
            <label htmlFor="current_password" className="block text-sm font-medium text-gray-700 mb-1">
              Current Password
            </label>
            <input
              type="password"
              id="current_password"
              value={passwordData.current_password}
              onChange={(e) => handlePasswordInputChange('current_password', e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm"
              placeholder="Enter your current password"
            />
            {passwordErrors.current_password && (
              <p className="mt-1 text-sm text-red-600">{passwordErrors.current_password}</p>
            )}
          </div>

          {/* New Password */}
          <div>
            <label htmlFor="new_password" className="block text-sm font-medium text-gray-700 mb-1">
              New Password
            </label>
            <input
              type="password"
              id="new_password"
              value={passwordData.new_password}
              onChange={(e) => handlePasswordInputChange('new_password', e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm"
              placeholder="Enter your new password"
            />
            {passwordErrors.new_password && (
              <p className="mt-1 text-sm text-red-600">{passwordErrors.new_password}</p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Must be at least 8 characters long
            </p>
          </div>

          {/* Confirm Password */}
          <div>
            <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-700 mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              id="confirm_password"
              value={passwordData.confirm_password}
              onChange={(e) => handlePasswordInputChange('confirm_password', e.target.value)}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm"
              placeholder="Confirm your new password"
            />
            {passwordErrors.confirm_password && (
              <p className="mt-1 text-sm text-red-600">{passwordErrors.confirm_password}</p>
            )}
          </div>

          {/* Success Message */}
          {passwordSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-md p-4">
              <p className="text-sm text-green-600">Password changed successfully!</p>
            </div>
          )}

          {/* Password Change Errors */}
          {passwordErrors.submit && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-sm text-red-600">{passwordErrors.submit}</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate('/profile')}
              disabled={isChangingPassword}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isChangingPassword}
              className="bg-orange-600 hover:bg-orange-700"
            >
              {isChangingPassword ? 'Changing Password...' : 'Change Password'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export { ChangePasswordPage };
