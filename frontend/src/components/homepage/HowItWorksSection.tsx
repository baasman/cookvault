import React from 'react';

interface StepProps {
  number: number;
  title: string;
  description: string;
}

const Step: React.FC<StepProps> = ({ number, title, description }) => {
  return (
    <div className="text-center p-8">
      {/* Step Number Circle */}
      <div className="w-12 h-12 bg-accent text-white rounded-full flex items-center justify-center font-bold text-xl mx-auto mb-6">
        {number}
      </div>
      
      
      <h3 className="text-xl font-semibold text-text-primary mb-3">
        {title}
      </h3>
      <p className="text-text-secondary">
        {description}
      </p>
    </div>
  );
};

const HowItWorksSection: React.FC = () => {
  const steps = [
    {
      number: 1,
      title: "Upload",
      description: "Take a photo or upload an image of your recipe from any cookbook, handwritten note, or printed page.",
    },
    {
      number: 2,
      title: "Process",
      description: "Our system automatically converts and organizes the text, identifying ingredients, instructions, and cooking details for you.",
    },
    {
      number: 3,
      title: "Organize",
      description: "Your digital recipe is ready! Edit, organize into cookbooks, add tags, and enjoy your perfectly structured recipe collection.",
    }
  ];

  return (
    <section className="py-24 bg-background">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl lg:text-5xl font-bold text-text-primary mb-4">
            How It Works
          </h2>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
          {steps.map((step, index) => (
            <React.Fragment key={index}>
              <Step
                number={step.number}
                title={step.title}
                description={step.description}
                icon={step.icon}
              />
              
              {/* Arrow connector between steps (hidden on mobile) */}
              {index < steps.length - 1 && (
                <div className="hidden md:flex items-center justify-center absolute top-20 transform -translate-y-1/2" 
                     style={{ 
                       left: `${((index + 1) * 100) / 3 - 100/6}%`,
                       width: `${100/3}%`
                     }}>
                  <div className="w-8 h-0.5 bg-border"></div>
                  <div className="w-0 h-0 border-l-4 border-l-border border-t-2 border-t-transparent border-b-2 border-b-transparent ml-1"></div>
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </section>
  );
};

export { HowItWorksSection };