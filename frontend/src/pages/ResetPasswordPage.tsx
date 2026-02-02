import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Button } from '../components/ui';
import { userApi } from '../services/userApi';

type Status = 'validating' | 'ready' | 'submitting' | 'success' | 'error';

interface PasswordFormData {
  new_password: string;
  confirm_password: string;
}

const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const [status, setStatus] = useState<Status>('validating');
  const [maskedEmail, setMaskedEmail] = useState('');
  const [error, setError] = useState('');

  const [passwordData, setPasswordData] = useState<PasswordFormData>({
    new_password: '',
    confirm_password: ''
  });
  const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setStatus('error');
        setError('No reset token provided. Please request a new password reset link.');
        return;
      }

      const result = await userApi.validateResetToken(token);

      if (result.valid && result.email) {
        setMaskedEmail(result.email);
        setStatus('ready');
      } else {
        setStatus('error');
        setError(result.error || 'Invalid or expired reset token');
      }
    };

    validateToken();
  }, [token]);

  const validatePasswordForm = (): boolean => {
    const newErrors: Record<string, string> = {};

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validatePasswordForm()) return;

    setStatus('submitting');
    setError('');

    try {
      await userApi.resetPassword(token, passwordData.new_password);
      setStatus('success');
    } catch (err) {
      setStatus('ready');
      setError(err instanceof Error ? err.message : 'Failed to reset password. Please try again.');
    }
  };

  const handlePasswordInputChange = (field: keyof PasswordFormData, value: string) => {
    setPasswordData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (passwordErrors[field]) {
      setPasswordErrors(prev => ({ ...prev, [field]: '' }));
    }
    if (error) {
      setError('');
    }
  };

  if (status === 'validating') {
    return (
      <div className="max-w-md mx-auto">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 mx-auto mb-6" style={{borderColor: '#f15f1c'}}></div>
          <h1 className="text-2xl font-bold mb-2" style={{color: '#1c120d'}}>
            Validating Reset Link
          </h1>
          <p style={{color: '#9b644b'}}>
            Please wait while we verify your reset token...
          </p>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="max-w-md mx-auto">
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center" style={{backgroundColor: '#f0fdf4'}}>
            <svg className="w-8 h-8" style={{color: '#16a34a'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-2" style={{color: '#1c120d'}}>
            Password Reset!
          </h1>
          <p style={{color: '#9b644b'}}>
            Your password has been successfully reset.
          </p>
        </div>

        <div className="p-8 rounded-lg shadow-sm text-center" style={{backgroundColor: '#ffffff', border: '1px solid #e8d7cf'}}>
          <div className="space-y-4">
            <p style={{color: '#1c120d'}}>
              You can now log in with your new password.
            </p>

            <div className="pt-4">
              <Button
                onClick={() => navigate('/login')}
                variant="primary"
                size="lg"
                className="w-full"
              >
                Go to Login
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'error' && !passwordData.new_password) {
    return (
      <div className="max-w-md mx-auto">
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center" style={{backgroundColor: '#fef2f2'}}>
            <svg className="w-8 h-8" style={{color: '#dc2626'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-2" style={{color: '#1c120d'}}>
            Invalid Reset Link
          </h1>
          <p style={{color: '#9b644b'}}>
            We couldn't verify your password reset link.
          </p>
        </div>

        <div className="p-8 rounded-lg shadow-sm" style={{backgroundColor: '#ffffff', border: '1px solid #e8d7cf'}}>
          <div className="p-4 rounded-md mb-6" style={{backgroundColor: '#fef2f2', border: '1px solid #fecaca'}}>
            <p className="text-sm font-medium" style={{color: '#dc2626'}}>
              {error}
            </p>
          </div>

          <div className="space-y-4">
            <p className="text-sm text-center" style={{color: '#9b644b'}}>
              The reset link may have expired or been used already. Please request a new one.
            </p>

            <div className="flex flex-col gap-3">
              <Link to="/forgot-password">
                <Button
                  variant="primary"
                  size="md"
                  className="w-full"
                >
                  Request New Reset Link
                </Button>
              </Link>

              <Link to="/login">
                <Button
                  variant="secondary"
                  size="md"
                  className="w-full"
                >
                  Back to Login
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Ready state - show password form
  return (
    <div className="max-w-md mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-page-title font-bold mb-2" style={{color: '#1c120d'}}>
          Reset Your Password
        </h1>
        <p style={{color: '#9b644b'}}>
          Enter a new password for <strong>{maskedEmail}</strong>
        </p>
      </div>

      <div className="p-8 rounded-lg shadow-sm" style={{backgroundColor: '#ffffff', border: '1px solid #e8d7cf'}}>
        <form onSubmit={handleSubmit} className="space-y-4">
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

          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-md" style={{backgroundColor: '#fef2f2', border: '1px solid #fecaca'}}>
              <p className="text-sm font-medium" style={{color: '#dc2626'}}>
                {error}
              </p>
            </div>
          )}

          <div className="pt-2">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={status === 'submitting'}
              className="w-full"
            >
              {status === 'submitting' ? 'Resetting Password...' : 'Reset Password'}
            </Button>
          </div>
        </form>

        <div className="mt-6 text-center">
          <Link to="/login" className="text-sm font-medium hover:underline" style={{color: '#f15f1c'}}>
            Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
};

export { ResetPasswordPage };
