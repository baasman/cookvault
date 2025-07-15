import React from 'react';
import { Link } from 'react-router-dom';
import { ScanIcon, BookIcon, CollectionIcon } from '../components/icons'; // Assuming these exist or will be created
import { HeroSection } from '../components/homepage';

const HomePage: React.FC = () => {
  return (
    <>
      <HeroSection />

      {/* Features Section */}
      <section className="features" id="features">
        <div className="container">
          <div className="features-header">
            <h2>Key Features</h2>
            <p>CookVault offers a comprehensive suite of tools designed to simplify recipe management and enhance your cooking experience.</p>
          </div>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">
                <ScanIcon className="icon icon-white" style={{ width: '2rem', height: '2rem' }} />
              </div>
              <h3>Smart Text Recognition</h3>
              <p>Our advanced scanning technology accurately extracts text from your handwritten or printed recipes, ensuring consistency in measurements and formatting for perfect results every time.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">
                <BookIcon className="icon icon-white" style={{ width: '2rem', height: '2rem' }} />
              </div>
              <h3>Smart Organization</h3>
              <p>Organize your recipes into digital cookbooks with automatic tagging and smart categorization. Find any recipe instantly with our powerful search and filtering system.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">
                <CollectionIcon className="icon icon-white" style={{ width: '2rem', height: '2rem' }} />
              </div>
              <h3>Recipe Collection Management</h3>
              <p>Build and maintain your personal recipe library. Access your complete collection from any device with cloud sync and never lose a cherished family recipe again.</p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="how-it-works">
        <div className="container">
          <div className="section-header">
            <h2>How It Works</h2>
          </div>
          <div className="steps-grid">
            <div className="step">
              <div className="step-number">1</div>
              <h3>Upload</h3>
              <p>Link a video, blog post, or take a photo and upload an image of your recipe from any cookbook, handwritten note, or printed page.</p>
            </div>
            <div className="step">
              <div className="step-number">2</div>
              <h3>Process</h3>
              <p>Our system automatically converts and organizes the text, identifying ingredients, instructions, and cooking details for you.</p>
            </div>
            <div className="step">
              <div className="step-number">3</div>
              <h3>Organize</h3>
              <p>Your digital recipe is ready! Edit, organize, add tags, and enjoy your perfectly structured recipe collection.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="benefits py-24 bg-white">
        <div className="container">
          <div className="section-header text-center mb-16">
            <h2 className="text-4xl lg:text-5xl font-bold text-text-primary mb-4">Why Cookbooks Matter</h2>
            <p className="text-xl text-text-secondary max-w-3xl mx-auto">
              Cookbooks offer something that scattered online recipes simply can't match — curation, expertise, and timeless value.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="benefit-card text-center">
              <div className="w-16 h-16 bg-accent rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Tested Recipes</h3>
              <p className="text-text-secondary text-sm">Professional development and testing ensure every recipe works perfectly.</p>
            </div>
            <div className="benefit-card text-center">
              <div className="w-16 h-16 bg-accent rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Curated Collections</h3>
              <p className="text-text-secondary text-sm">Thoughtful recipe selection and pairing by culinary experts.</p>
            </div>
            <div className="benefit-card text-center">
              <div className="w-16 h-16 bg-accent rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Culinary Expertise</h3>
              <p className="text-text-secondary text-sm">Author knowledge and technique guidance you won't find elsewhere.</p>
            </div>
            <div className="benefit-card text-center">
              <div className="w-16 h-16 bg-accent rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Timeless Value</h3>
              <p className="text-text-secondary text-sm">Recipes that stand the test of time and preserve cultural heritage.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta">
        <div className="container">
          <h2>Start Digitizing Your Cookbook Collection Today</h2>
          <p>Join cookbook enthusiasts who are preserving their culinary libraries while keeping them more accessible than ever. Import your first cookbook in minutes.</p>
          <Link to="/register" className="btn btn-white btn-lg">
            Create Your Account
            <svg className="icon" viewBox="0 0 24 24">
              <path d="M4,11V13H16L10.5,18.5L11.92,19.92L19.84,12L11.92,4.08L10.5,5.5L16,11H4Z" />
            </svg>
          </Link>
        </div>
      </section>
    </>
  );
};

export default HomePage;
