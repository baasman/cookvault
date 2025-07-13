import React from 'react';

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ icon, title, description }) => {
  return (
    <div className="bg-background border border-border rounded-2xl p-10 text-center transition-all duration-300 hover:transform hover:-translate-y-1 hover:shadow-2xl" style={{boxShadow: 'hover:0 20px 40px rgba(28, 18, 13, 0.1)'}}>
      <div className="w-16 h-16 bg-gradient-to-br from-accent to-accent-hover rounded-2xl flex items-center justify-center mx-auto mb-6 overflow-hidden">
        {icon}
      </div>
      <h3 className="text-2xl font-semibold text-text-primary mb-4">
        {title}
      </h3>
      <p className="text-text-secondary leading-relaxed">
        {description}
      </p>
    </div>
  );
};

const FeaturesSection: React.FC = () => {
  const features = [
    {
      icon: <svg className="text-white w-8 h-8 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24" style={{maxWidth: '32px', maxHeight: '32px'}}>
        <path d="M12,2A3,3 0 0,1 15,5V11A3,3 0 0,1 12,14A3,3 0 0,1 9,11V5A3,3 0 0,1 12,2M19,11C19,14.53 16.39,17.44 13,17.93V21H11V17.93C7.61,17.44 5,14.53 5,11H7A5,5 0 0,0 12,16A5,5 0 0,0 17,11H19Z"/>
      </svg>,
      title: "Smart Text Recognition",
      description: "Our advanced scanning technology accurately extracts text from your handwritten or printed recipes, ensuring consistency in measurements and formatting for perfect results every time."
    },
    {
      icon: <svg className="text-white w-8 h-8 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} style={{maxWidth: '32px', maxHeight: '32px'}}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>,
      title: "Smart Organization",
      description: "Organize your recipes into digital cookbooks with automatic tagging and smart categorization. Find any recipe instantly with our powerful search and filtering system."
    },
    {
      icon: <svg className="text-white w-8 h-8 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} style={{maxWidth: '32px', maxHeight: '32px'}}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>,
      title: "Recipe Collection Management",
      description: "Build and maintain your personal recipe library. Access your complete collection from any device with cloud sync and never lose a cherished family recipe again."
    }
  ];

  return (
    <section id="features" className="py-24 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl lg:text-5xl font-bold text-text-primary mb-4">
            Key Features
          </h2>
          <p className="text-xl text-text-secondary max-w-3xl mx-auto">
            Cookbook Creator offers a comprehensive suite of tools designed to simplify recipe management and enhance your cooking experience.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <FeatureCard
              key={index}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

export { FeaturesSection };