import React, { useState } from 'react';
import { Navigate, useNavigate, Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { useAuth } from '../contexts/AuthContext';

const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid email or password');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
          <p style={{color: '#9b644b'}}>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-page-title font-bold mb-2" style={{color: '#1c120d'}}>
          Welcome Back
        </h1>
        <p style={{color: '#9b644b'}}>
          Sign in to your account to continue
        </p>
      </div>

      <div className="p-8 rounded-lg shadow-sm" style={{backgroundColor: '#ffffff', border: '1px solid #e8d7cf'}}>
        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="Enter your email"
            required
          />

          <Input
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="Enter your password"
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
            disabled={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? 'Signing In...' : 'Sign In'}
          </Button>
        </form>

        <div className="mt-6 text-center space-y-2">
          <p className="text-sm" style={{color: '#9b644b'}}>
            Don't have an account?{' '}
            <Link to="/register" className="font-medium hover:underline" style={{color: '#f15f1c'}}>
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export { LoginPage };