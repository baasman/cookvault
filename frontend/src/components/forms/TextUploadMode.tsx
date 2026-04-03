import React from 'react';

interface TextUploadModeProps {
  recipeText: string;
  onTextChange: (text: string) => void;
}

const TextUploadMode: React.FC<TextUploadModeProps> = ({
  recipeText,
  onTextChange,
}) => {
  return (
    <div className="flex flex-col">
      <div className="pb-2">
        <label className="block text-base font-medium leading-normal" style={{color: '#1c120d'}}>
          Recipe Text *
        </label>
        <p className="text-sm mt-1" style={{color: '#9b644b'}}>
          Paste or type your recipe below. Include title, ingredients, and instructions.
        </p>
      </div>
      <textarea
        value={recipeText}
        onChange={(e) => onTextChange(e.target.value)}
        placeholder="Example:\n\nChocolate Chip Cookies\n\nIngredients:\n- 2 cups flour\n- 1 cup butter\n- 1 cup sugar\n...\n\nInstructions:\n1. Preheat oven to 350°F\n2. Mix dry ingredients\n..."
        className="w-full px-4 py-3 border rounded-lg resize-y font-mono text-sm"
        style={{
          borderColor: '#e8d7cf',
          backgroundColor: '#fcf9f8',
          minHeight: '300px',
          maxHeight: '600px'
        }}
        required
      />
      <div className="flex justify-between mt-2">
        <span className="text-xs" style={{color: '#9b644b'}}>
          {recipeText.length} / 50,000 characters
        </span>
        {recipeText.length > 45000 && (
          <span className="text-xs text-orange-600">
            Approaching character limit
          </span>
        )}
      </div>
    </div>
  );
};

export { TextUploadMode };
