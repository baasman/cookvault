import React from 'react';
import { Link } from 'react-router-dom';
import { AIIcon, BookIcon, CollectionIcon } from '../components/icons'; // Assuming these exist or will be created
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
            <p>...Name... offers a comprehensive suite of tools designed to simplify recipe management and enhance your cooking experience.</p>
          </div>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">
                <AIIcon className="icon icon-white" style={{ width: '2rem', height: '2rem' }} />
              </div>
              <h3>AI-Powered Recognition</h3>
              <p>Our advanced OCR technology accurately extracts text from your handwritten or printed recipes, ensuring consistency in measurements and formatting for perfect results every time.</p>
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
              <p>Our AI technology extracts and digitizes the text, identifying ingredients, instructions, and cooking details automatically.</p>
            </div>
            <div className="step">
              <div className="step-number">3</div>
              <h3>Organize</h3>
              <p>Your digital recipe is ready! Edit, organize, add tags, and enjoy your perfectly structured recipe collection.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta">
        <div className="container">
          <h2>Start Building Your Digital Recipe Collection Today</h2>
          <p>Join thousands of home cooks who have already digitized their favorite recipes. Get started in minutes.</p>
          <Link to="/register" className="btn btn-white btn-lg">
            Create Your Account
            <svg className="icon" viewBox="0 0 24 24">
              <path d="M4,11V13H16L10.5,18.5L11.92,19.92L19.84,12L11.92,4.08L10.5,5.5L16,11H4Z"/>
            </svg>
          </Link>
        </div>
      </section>
    </>
  );
};

export default HomePage;
