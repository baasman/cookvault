import React from 'react';

interface CookingModeProgressProps {
  currentStep: number;
  totalSteps: number;
  onClose: () => void;
}

const CookingModeProgress: React.FC<CookingModeProgressProps> = ({
  currentStep,
  totalSteps,
  onClose,
}) => {
  const progress = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0;
  const label = `Step ${currentStep} of ${totalSteps}`;

  return (
    <div className="flex-shrink-0">
      {/* Progress bar */}
      <div className="h-1 bg-gray-200 w-full">
        <div
          className="h-full transition-all duration-300 ease-out"
          style={{ width: `${progress}%`, backgroundColor: '#f15f1c' }}
        />
      </div>

      {/* Step label + close button */}
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-sm font-medium text-gray-600">{label}</span>
        <button
          onClick={onClose}
          className="p-2 -m-2 text-gray-400 hover:text-gray-600 active:scale-95"
          aria-label="Exit cooking mode"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export { CookingModeProgress };
