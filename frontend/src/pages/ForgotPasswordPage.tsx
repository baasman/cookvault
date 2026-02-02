import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, Input } from '../components/ui';
import { userApi } from '../services/userApi';

type Status = 'idle' | 'submitting' | 'success' | 'error';

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setStatus('submitting');

    try {
      await userApi.requestPasswordReset(email);
      setStatus('success');
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Failed to send reset email. Please try again.');
    }
  };

  if (status === 'success') {
    return (
      <div className="max-w-md mx-auto">
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center" style={{backgroundColor: '#f0fdf4'}}>
            <svg className="w-8 h-8" style={{color: '#16a34a'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-2" style={{color: '#1c120d'}}>
            Check Your Email
          </h1>
          <p style={{color: '#9b644b'}}>
            We've sent a password reset link to your email.
          </p>
        </div>

        <div className="p-8 rounded-lg shadow-sm" style={{backgroundColor: '#ffffff', border: '1px solid #e8d7cf'}}>
          <div className="text-center space-y-4">
            <p style={{color: '#1c120d'}}>
              If an account exists for <strong>{email}</strong>, you will receive a password reset link.
            </p>
            <p className="text-sm" style={{color: '#9b644b'}}>
              The link will expire in 24 hours. If you don't see the email, check your spam folder.
            </p>

            <div className="pt-4 space-y-3">
              <Button
                onClick={() => {
                  setStatus('idle');
                  setEmail('');
                }}
                variant="secondary"
                size="md"
                className="w-full"
              >
                Send Another Email
              </Button>

              <Link to="/login">
                <Button
                  variant="primary"
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

  return (
    <div className="max-w-md mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-page-title font-bold mb-2" style={{color: '#1c120d'}}>
          Forgot Password?
        </h1>
        <p style={{color: '#9b644b'}}>
          No worries, we'll send you reset instructions.
        </p>
      </div>

      <div className="p-8 rounded-lg shadow-sm" style={{backgroundColor: '#ffffff', border: '1px solid #e8d7cf'}}>
        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="Email Address"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="Enter your email"
            required
          />

          {error && (
            <div className="p-3 rounded-md" style={{backgroundColor: '#fef2f2', border: '1px solid #fecaca'}}>
              <p className="text-sm font-medium" style={{color: '#dc2626'}}>
                {error}
              </p>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            size="lg"
            disabled={status === 'submitting' || !email}
            className="w-full"
          >
            {status === 'submitting' ? 'Sending...' : 'Send Reset Link'}
          </Button>
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

export { ForgotPasswordPage };
