import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui';
import { apiFetch } from '../utils/apiInterceptor';

const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [error, setError] = useState('');
  const [user, setUser] = useState<{ username: string; email: string } | null>(null);

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get('token');

      if (!token) {
        setStatus('error');
        setError('No verification token provided');
        return;
      }

      try {
        const apiUrl = import.meta.env.VITE_API_URL || '/api';
        const response = await apiFetch(`${apiUrl}/auth/verify-email`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || 'Verification failed');
        }

        // Store the JWT token for immediate login
        if (data.access_token) {
          localStorage.setItem('auth_token', data.access_token);
        }

        setUser(data.user);
        setStatus('success');

        // Redirect to recipes page after 2 seconds
        setTimeout(() => {
          window.location.href = '/recipes'; // Use window.location to trigger full reload with new auth
        }, 2000);
      } catch (err) {
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Verification failed');
      }
    };

    verifyEmail();
  }, [searchParams]);

  if (status === 'verifying') {
    return (
      <div className="max-w-md mx-auto">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 mx-auto mb-6" style={{borderColor: '#f15f1c'}}></div>
          <h1 className="text-2xl font-bold mb-2" style={{color: '#1c120d'}}>
            Verifying Your Email
          </h1>
          <p style={{color: '#9b644b'}}>
            Please wait while we verify your account...
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
            Email Verified!
          </h1>
          <p style={{color: '#9b644b'}}>
            Your account has been successfully verified.
          </p>
        </div>

        <div className="p-8 rounded-lg shadow-sm text-center" style={{backgroundColor: '#ffffff', border: '1px solid #e8d7cf'}}>
          {user && (
            <div className="mb-6">
              <p className="text-sm" style={{color: '#9b644b'}}>Welcome,</p>
              <p className="text-xl font-bold mt-1" style={{color: '#1c120d'}}>{user.username}</p>
              <p className="text-sm mt-1" style={{color: '#9b644b'}}>{user.email}</p>
            </div>
          )}

          <div className="space-y-4">
            <p style={{color: '#1c120d'}}>
              You're all set! Redirecting you to your recipes...
            </p>

            <div className="pt-4">
              <Button
                onClick={() => window.location.href = '/recipes'}
                variant="primary"
                size="lg"
                className="w-full"
              >
                Go to Recipes Now
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  return (
    <div className="max-w-md mx-auto">
      <div className="text-center mb-8">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center" style={{backgroundColor: '#fef2f2'}}>
          <svg className="w-8 h-8" style={{color: '#dc2626'}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold mb-2" style={{color: '#1c120d'}}>
          Verification Failed
        </h1>
        <p style={{color: '#9b644b'}}>
          We couldn't verify your email address.
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
            The verification link may have expired or been used already.
          </p>

          <div className="flex flex-col gap-3">
            <Button
              onClick={() => navigate('/register')}
              variant="primary"
              size="md"
              className="w-full"
            >
              Register Again
            </Button>

            <Button
              onClick={() => navigate('/login')}
              variant="secondary"
              size="md"
              className="w-full"
            >
              Back to Login
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-6 text-center">
        <p className="text-sm" style={{color: '#9b644b'}}>
          Need help?{' '}
          <a href="mailto:support@cookbook-creator.com" className="font-medium hover:underline" style={{color: '#f15f1c'}}>
            Contact Support
          </a>
        </p>
      </div>
    </div>
  );
};

export { VerifyEmailPage };
