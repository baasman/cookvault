import React, { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Button } from '../components/ui';
import { apiFetch } from '../utils/apiInterceptor';

const VerifyEmailSentPage: React.FC = () => {
  const location = useLocation();
  const { email, method } = location.state || {};
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState('');
  const [resendError, setResendError] = useState('');

  const handleResend = async () => {
    if (!email) return;

    setIsResending(true);
    setResendMessage('');
    setResendError('');

    try {
      const apiUrl = import.meta.env.VITE_API_URL || '/api';
      const response = await apiFetch(`${apiUrl}/auth/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email_or_phone: email,
          method: method || 'email',
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to resend verification');
      }

      setResendMessage('Verification email sent! Please check your inbox.');
    } catch (err) {
      setResendError(err instanceof Error ? err.message : 'Failed to resend verification');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="text-center mb-8">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center" style={{backgroundColor: '#fef6f1'}}>
          <svg className="w-8 h-8" style={{color: '#f15f1c'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold mb-2" style={{color: '#1c120d'}}>
          Check Your Email
        </h1>
        <p style={{color: '#9b644b'}}>
          We've sent a verification link to
        </p>
        <p className="font-medium mt-1" style={{color: '#1c120d'}}>
          {email || 'your email address'}
        </p>
      </div>

      <div className="p-8 rounded-lg shadow-sm space-y-6" style={{backgroundColor: '#ffffff', border: '1px solid #e8d7cf'}}>
        <div className="space-y-4">
          <div className="flex items-start">
            <div className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5" style={{backgroundColor: '#fef6f1', color: '#f15f1c'}}>
              <span className="text-sm font-bold">1</span>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium" style={{color: '#1c120d'}}>Check your inbox</p>
              <p className="text-sm mt-1" style={{color: '#9b644b'}}>Look for an email from Cookbook Creator</p>
            </div>
          </div>

          <div className="flex items-start">
            <div className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5" style={{backgroundColor: '#fef6f1', color: '#f15f1c'}}>
              <span className="text-sm font-bold">2</span>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium" style={{color: '#1c120d'}}>Click the verification link</p>
              <p className="text-sm mt-1" style={{color: '#9b644b'}}>This will activate your account</p>
            </div>
          </div>

          <div className="flex items-start">
            <div className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center mt-0.5" style={{backgroundColor: '#fef6f1', color: '#f15f1c'}}>
              <span className="text-sm font-bold">3</span>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium" style={{color: '#1c120d'}}>Start cooking!</p>
              <p className="text-sm mt-1" style={{color: '#9b644b'}}>You'll be automatically logged in</p>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t" style={{borderColor: '#e8d7cf'}}>
          <p className="text-sm text-center mb-3" style={{color: '#9b644b'}}>
            Didn't receive the email?
          </p>
          <Button
            type="button"
            variant="secondary"
            size="md"
            onClick={handleResend}
            disabled={isResending || !email}
            className="w-full"
          >
            {isResending ? 'Sending...' : 'Resend Verification Email'}
          </Button>

          {resendMessage && (
            <div className="mt-3 p-3 rounded-md" style={{backgroundColor: '#f0fdf4', border: '1px solid #86efac'}}>
              <p className="text-sm text-center" style={{color: '#16a34a'}}>
                {resendMessage}
              </p>
            </div>
          )}

          {resendError && (
            <div className="mt-3 p-3 rounded-md" style={{backgroundColor: '#fef2f2', border: '1px solid #fecaca'}}>
              <p className="text-sm text-center" style={{color: '#dc2626'}}>
                {resendError}
              </p>
            </div>
          )}
        </div>

        <div className="pt-4 border-t text-center" style={{borderColor: '#e8d7cf'}}>
          <p className="text-sm" style={{color: '#9b644b'}}>
            Changed your mind?{' '}
            <Link to="/login" className="font-medium hover:underline" style={{color: '#f15f1c'}}>
              Back to login
            </Link>
          </p>
        </div>
      </div>

      <div className="mt-6 p-4 rounded-lg" style={{backgroundColor: '#fef6f1'}}>
        <p className="text-xs text-center" style={{color: '#9b644b'}}>
          <strong>Note:</strong> The verification link will expire in 24 hours.
          Check your spam folder if you don't see it in your inbox.
        </p>
      </div>
    </div>
  );
};

export { VerifyEmailSentPage };
