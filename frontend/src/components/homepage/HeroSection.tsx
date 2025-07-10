import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../ui/Button';
import { useAuth } from '../../contexts/AuthContext';

const HeroSection: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <section className="relative py-16 lg:py-24 bg-gradient-to-br from-primary-100 via-background to-primary-200 overflow-hidden">
      <div className="absolute top-0 right-0 w-3/5 h-full opacity-30 pointer-events-none" style={{backgroundImage: "url('data:image/svg+xml,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1200 800\"><defs><pattern id=\"cooking\" patternUnits=\"userSpaceOnUse\" width=\"100\" height=\"100\"><circle cx=\"50\" cy=\"50\" r=\"2\" fill=\"%23f15f1c\" opacity=\"0.1\"/></pattern></defs><rect width=\"1200\" height=\"800\" fill=\"url(%23cooking)\"/></svg>')", backgroundSize: 'cover', backgroundRepeat: 'no-repeat'}}></div>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="flex justify-center items-center min-h-[60vh]">
          {/* Hero Text */}
          <div className="text-center max-w-4xl mx-auto">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl xl:text-6xl font-bold text-text-primary leading-tight mb-6">
              Your Recipes, Perfectly Organized
            </h1>
            <p className="text-lg sm:text-xl text-text-secondary mb-10 max-w-3xl mx-auto">
              Transform handwritten notes, blog posts, image recipes and more into digital files with AI-powered OCR technology.
              From scattered recipes to organized recipe collections.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to={isAuthenticated ? "/upload" : "/register"}>
                <Button variant="primary" size="lg" className="w-full sm:w-auto">
                  <svg className="text-white w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24" style={{maxWidth: '20px', maxHeight: '20px'}}>
                    <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                  </svg>
                  {isAuthenticated ? "Upload Recipe" : "Get Started"}
                </Button>
              </Link>
              <Button
                variant="secondary"
                size="lg"
                className="w-full sm:w-auto"
                onClick={() => {
                  const featuresSection = document.getElementById('features');
                  featuresSection?.scrollIntoView({ behavior: 'smooth' });
                }}
              >
                Learn More
              </Button>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
};

export { HeroSection };