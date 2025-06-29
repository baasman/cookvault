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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center min-h-[60vh]">
          {/* Hero Text */}
          <div className="text-center lg:text-left">
            <h1 className="text-4xl lg:text-5xl xl:text-6xl font-bold text-text-primary leading-tight mb-6">
              Your Recipes, Perfectly Organized
            </h1>
            <p className="text-xl text-text-secondary mb-10 max-w-lg mx-auto lg:mx-0">
              Transform handwritten notes into digital files with AI-powered OCR technology. 
              From scattered recipes to organized cookbook collections.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
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

          {/* Hero Visual - Demo Card */}
          <div className="flex justify-center items-center">
            <div className="bg-white rounded-2xl p-8 shadow-2xl border border-border max-w-md w-full transform hover:scale-105 transition-all duration-300" style={{boxShadow: '0 20px 60px rgba(28, 18, 13, 0.15)'}}>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 bg-gradient-to-br from-accent to-accent-hover rounded-xl flex items-center justify-center overflow-hidden">
                  <svg className="text-white w-6 h-6 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24" style={{maxWidth: '24px', maxHeight: '24px'}}>
                    <path d="M12,2A3,3 0 0,1 15,5V11A3,3 0 0,1 12,14A3,3 0 0,1 9,11V5A3,3 0 0,1 12,2M19,11C19,14.53 16.39,17.44 13,17.93V21H11V17.93C7.61,17.44 5,14.53 5,11H7A5,5 0 0,0 12,16A5,5 0 0,0 17,11H19Z"/>
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-text-primary">
                  AI Recipe Extraction
                </h3>
              </div>
              
              <p className="text-text-secondary mb-6">
                Upload any recipe image and watch our AI extract ingredients, instructions, and details automatically.
              </p>
              
              {/* Upload Demo Area */}
              <div className="border-2 border-dashed border-border rounded-xl p-6 text-center bg-background">
                <svg className="text-text-secondary mx-auto mb-2 w-8 h-8 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24" style={{maxWidth: '32px', maxHeight: '32px'}}>
                  <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                </svg>
                <p className="text-sm text-text-secondary font-medium">
                  Drop your recipe image here
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export { HeroSection };