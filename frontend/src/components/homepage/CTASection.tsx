import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../ui/Button';
import { useAuth } from '../../contexts/AuthContext';

const CTASection: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <section className="py-24 bg-gradient-to-br from-text-primary to-gray-900">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 className="text-4xl lg:text-5xl font-bold text-white mb-4">
          Start Building Your Digital Recipe Collection Today
        </h2>
        <p className="text-xl text-white/80 mb-10 max-w-2xl mx-auto">
          Join thousands of home cooks who have already digitized their favorite recipes. 
          Get started in minutes.
        </p>
        
        <Link to={isAuthenticated ? "/upload" : "/register"}>
          <Button 
            className="bg-white text-text-primary hover:bg-gray-100 transform hover:scale-105 hover:-translate-y-0.5 transition-all duration-300 shadow-lg"
            size="lg"
          >
            {isAuthenticated ? "Upload Your First Recipe" : "Create Your Account"}
            <svg className="ml-2 w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24" style={{maxWidth: '16px', maxHeight: '16px'}}>
              <path d="M4,11V13H16L10.5,18.5L11.92,19.92L19.84,12L11.92,4.08L10.5,5.5L16,11H4Z"/>
            </svg>
          </Button>
        </Link>
      </div>
    </section>
  );
};

export { CTASection };