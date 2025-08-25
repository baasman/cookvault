import React from 'react';
import { Link } from 'react-router-dom';
import { ScanIcon, BookIcon, CollectionIcon } from '../components/icons'; // Assuming these exist or will be created
import { HeroSection } from '../components/homepage';
import { FeaturedRecipes } from '../components/recipe/FeaturedRecipes';

const HomePage: React.FC = () => {
  return (
    <>
      <HeroSection />

      <FeaturedRecipes />

      {/* Features Section */}
      <section className="features" id="features">
        <div className="container">
          <div className="features-header">
            <h2>Core Features</h2>
            <p>Cookle combines the best of digital and physical cookbook experiences, offering unique capabilities for cookbook enthusiasts.</p>
          </div>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">
                <BookIcon className="icon icon-white" style={{ width: '2rem', height: '2rem' }} />
              </div>
              <h3>Create Your Personal Cookbook</h3>
              <p>Select your favorite recipes from your digital collection and publish them as a beautiful physical cookbook for personal use. Perfect for family recipe collections, gift-giving, or preserving your culinary journey in print.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">
                <CollectionIcon className="icon icon-white" style={{ width: '2rem', height: '2rem' }} />
              </div>
              <h3>Publisher Marketplace</h3>
              <p>Browse and purchase professionally digitized cookbooks directly from publishers. Get instant access to complete, searchable cookbook collections from your favorite authors and culinary experts.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">
                <ScanIcon className="icon icon-white" style={{ width: '2rem', height: '2rem' }} />
              </div>
              <h3>Smart Recipe Management</h3>
              <p>Upload recipes from any source — photos, handwritten notes, or links. Our AI accurately extracts and organizes content, making everything searchable and perfectly formatted for your collection.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Two Ways Section */}
      <section className="py-20 bg-gradient-to-br from-primary-50 to-background">
        <div className="container">
          <div className="text-center mb-12">
            <h2 className="text-3xl lg:text-4xl font-bold text-text-primary mb-4">Two Ways to Build Your Library</h2>
            <p className="text-lg text-text-secondary max-w-2xl mx-auto">
              Whether you want to preserve your own recipes or discover new ones from professionals, Cookle has you covered.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <div className="bg-white rounded-xl p-8 shadow-lg border border-border">
              <div className="w-12 h-12 bg-accent rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-text-primary mb-3">Import & Create</h3>
              <p className="text-text-secondary mb-4">
                Upload your own recipes from photos, handwritten notes, or online sources. Organize them into collections and transform them into beautiful physical cookbooks for your kitchen or as personal gifts.
              </p>
              <ul className="space-y-2 text-sm text-text-secondary">
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-accent mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Upload from any source
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-accent mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  AI-powered text extraction
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-accent mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Print personal cookbooks
                </li>
              </ul>
            </div>
            <div className="bg-white rounded-xl p-8 shadow-lg border border-border">
              <div className="w-12 h-12 bg-accent rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-text-primary mb-3">Browse & Buy</h3>
              <p className="text-text-secondary mb-4">
                Purchase complete, professionally digitized cookbooks directly from publishers. Get instant access to searchable, high-quality cookbook content from renowned chefs and culinary experts.
              </p>
              <ul className="space-y-2 text-sm text-text-secondary">
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-accent mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Publisher-quality content
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-accent mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Instant digital access
                </li>
                <li className="flex items-start">
                  <svg className="w-5 h-5 text-accent mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Fully searchable libraries
                </li>
              </ul>
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
            <h2 className="text-4xl lg:text-5xl font-bold text-text-primary mb-4">The Best of Both Worlds</h2>
            <p className="text-xl text-text-secondary max-w-3xl mx-auto">
              Combine the convenience of digital with the permanence of print. Access professional content and create your own lasting cookbook legacy.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="benefit-card text-center">
              <div className="w-16 h-16 bg-accent rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Physical Books You Create</h3>
              <p className="text-text-secondary text-sm">Transform your digital collection into beautiful printed cookbooks for personal use.</p>
            </div>
            <div className="benefit-card text-center">
              <div className="w-16 h-16 bg-accent rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Publisher Quality</h3>
              <p className="text-text-secondary text-sm">Access professionally digitized cookbooks with tested recipes and expert guidance.</p>
            </div>
            <div className="benefit-card text-center">
              <div className="w-16 h-16 bg-accent rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Instant Search</h3>
              <p className="text-text-secondary text-sm">Find any recipe across your entire library — personal and purchased — in seconds.</p>
            </div>
            <div className="benefit-card text-center">
              <div className="w-16 h-16 bg-accent rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Personal Touch</h3>
              <p className="text-text-secondary text-sm">Create custom cookbooks for gifts or preserve family recipes for generations.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta">
        <div className="container">
          <h2>Start Building Your Ultimate Cookbook Library</h2>
          <p>Join the future of cookbook collecting. Create personalized physical books from your favorite recipes or discover professionally digitized cookbooks from top publishers. Your culinary journey begins here.</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center mt-8">
            <Link to="/register" className="btn btn-white btn-lg">
              Create Your Account
              <svg className="icon" viewBox="0 0 24 24">
                <path d="M4,11V13H16L10.5,18.5L11.92,19.92L19.84,12L11.92,4.08L10.5,5.5L16,11H4Z" />
              </svg>
            </Link>
            <Link to="/cookbooks" className="btn btn-secondary btn-lg">
              Browse Cookbooks
              <svg className="icon" viewBox="0 0 24 24">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
            </Link>
          </div>
          <p className="text-sm text-gray-600 mt-4">
            Personal cookbook publishing is for personal use only • Publisher content available for purchase
          </p>
        </div>
      </section>
    </>
  );
};

export default HomePage;
