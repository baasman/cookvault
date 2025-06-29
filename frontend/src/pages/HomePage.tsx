import React from 'react';
import { HeroSection, FeaturesSection, HowItWorksSection, CTASection } from '../components/homepage';

const HomePage: React.FC = () => {
  return (
    <>
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <CTASection />
    </>
  );
};

export { HomePage };