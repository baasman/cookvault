import React, { useState, useEffect } from 'react';

interface RecipeScalerProps {
  originalServings: number | undefined;
  onScaleChange: (scaleFactor: number, desiredServings: number) => void;
}

export const RecipeScaler: React.FC<RecipeScalerProps> = ({ 
  originalServings, 
  onScaleChange 
}) => {
  const [desiredServings, setDesiredServings] = useState<number>(originalServings || 4);
  const [isScaling, setIsScaling] = useState(false);
  
  useEffect(() => {
    if (originalServings) {
      setDesiredServings(originalServings);
    }
  }, [originalServings]);

  const handleServingsChange = (value: string) => {
    const num = parseInt(value);
    if (!isNaN(num) && num > 0) {
      setDesiredServings(num);
      if (originalServings) {
        const scaleFactor = num / originalServings;
        onScaleChange(scaleFactor, num);
        setIsScaling(num !== originalServings);
      }
    }
  };

  const handleReset = () => {
    if (originalServings) {
      setDesiredServings(originalServings);
      onScaleChange(1, originalServings);
      setIsScaling(false);
    }
  };

  const quickScaleOptions = [
    { label: '½×', factor: 0.5 },
    { label: '2×', factor: 2 },
    { label: '3×', factor: 3 },
  ];

  const handleQuickScale = (factor: number) => {
    if (originalServings) {
      const newServings = Math.round(originalServings * factor);
      setDesiredServings(newServings);
      onScaleChange(factor, newServings);
      setIsScaling(true);
    }
  };

  if (!originalServings) {
    return (
      <div className="text-sm text-text-secondary italic">
        Servings not specified - scaling unavailable
      </div>
    );
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 w-full max-w-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-blue-900">Scale Recipe</h3>
        {isScaling && (
          <button
            onClick={handleReset}
            className="text-xs text-blue-600 hover:text-blue-800 underline flex-shrink-0"
          >
            Reset
          </button>
        )}
      </div>
      
      {/* Always stack vertically for better fit in narrow column */}
      <div className="space-y-3">
        <div className="flex items-center space-x-2">
          <label htmlFor="servings" className="text-sm text-gray-700 flex-shrink-0">
            Servings:
          </label>
          <input
            id="servings"
            type="number"
            min="1"
            max="100"
            value={desiredServings}
            onChange={(e) => handleServingsChange(e.target.value)}
            className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500 flex-shrink-0">Quick:</span>
          <div className="flex space-x-1 flex-wrap">
            {quickScaleOptions.map((option) => (
              <button
                key={option.label}
                onClick={() => handleQuickScale(option.factor)}
                className="px-2 py-1 text-xs font-medium text-blue-700 bg-white border border-blue-300 rounded hover:bg-blue-50 transition-colors"
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {isScaling && (
        <div className="mt-3 text-xs text-blue-600">
          <div className="font-medium">
            Scaled from {originalServings} to {desiredServings} servings
          </div>
          <div className="text-blue-500">
            ({(desiredServings / originalServings).toFixed(1)}× original)
          </div>
        </div>
      )}
    </div>
  );
};