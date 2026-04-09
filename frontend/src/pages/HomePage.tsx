import React from 'react';
import { Link } from 'react-router-dom';
import { HeroSection, AppStoreBanner } from '../components/homepage';
import { FeaturedRecipes } from '../components/recipe/FeaturedRecipes';
import { AuthenticatedDashboard } from '../components/dashboard';
import { useAuth } from '../contexts/AuthContext';

const HomePage: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <div className="text-center">
          <div
            className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4"
            style={{ borderColor: '#f15f1c' }}
          ></div>
          <p style={{ color: '#9b644b' }}>Loading...</p>
        </div>
      </div>
    );
  }

  // Show personalized dashboard for authenticated users
  if (isAuthenticated) {
    return <AuthenticatedDashboard />;
  }

  // Show marketing landing page for unauthenticated users
  return (
    <>
      <AppStoreBanner />
      <HeroSection />

      <FeaturedRecipes />

      {/* How It Works - Consolidated */}
      <section className="py-16 bg-white">
        <div className="max-w-5xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: '#f15f1c' }}>
                <span className="text-white font-bold text-xl">1</span>
              </div>
              <h3 className="font-semibold text-lg mb-2">Capture</h3>
              <p className="text-text-secondary">
                Snap photos, paste URLs, import from videos, or write your own recipes from scratch
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: '#f15f1c' }}>
                <span className="text-white font-bold text-xl">2</span>
              </div>
              <h3 className="font-semibold text-lg mb-2">Digitize</h3>
              <p className="text-text-secondary">
                AI extracts ingredients, instructions, and details into a searchable library
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: '#f15f1c' }}>
                <span className="text-white font-bold text-xl">3</span>
              </div>
              <h3 className="font-semibold text-lg mb-2">Print</h3>
              <p className="text-text-secondary">
                Organize into custom cookbooks and print beautiful physical copies
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Cooking Mode Highlight */}
      <section className="py-12" style={{ backgroundColor: '#fcf9f8' }}>
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center gap-6 bg-white rounded-2xl border p-8" style={{ borderColor: '#e8d7cf' }}>
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: '#f15f1c' }}>
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1 text-center md:text-left">
              <h3 className="text-xl font-bold mb-1" style={{ color: '#1c120d' }}>Cook with Confidence</h3>
              <p className="text-text-secondary">
                Follow recipes step-by-step with smart timers, ingredient checklists, and personal notes — right from your phone.
              </p>
            </div>
            <Link to="/register" className="flex-shrink-0 px-6 py-3 rounded-xl text-white font-medium" style={{ backgroundColor: '#f15f1c' }}>
              Get Started
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-gradient-to-r from-text-primary to-gray-800 text-center">
        <div className="max-w-2xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-white mb-4">
            Start Your Cookbook Collection
          </h2>
          <p className="text-gray-300 mb-8">
            Free to start. Import unlimited recipes.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/register" className="btn btn-white btn-lg">
              Create Account
            </Link>
            <Link to="/cookbooks" className="btn btn-secondary btn-lg">
              Browse Cookbooks
            </Link>
          </div>
        </div>
      </section>
    </>
  );
};

export { HomePage };
