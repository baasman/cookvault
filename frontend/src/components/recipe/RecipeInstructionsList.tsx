import React from 'react';
import { PaywallMessage } from './PaywallMessage';
import type { Recipe } from '../../types';

interface RecipeInstructionsListProps {
  recipe: Recipe;
  showOriginalText: boolean;
  isEditing: boolean;
}

const RecipeInstructionsList: React.FC<RecipeInstructionsListProps> = ({
  recipe,
  showOriginalText,
  isEditing: _isEditing,
}) => {
  return (
    <div className="lg:col-span-2">
      <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
        <h2 className="text-xl font-bold mb-4" style={{color: '#1c120d'}}>
          Instructions
        </h2>
        {recipe.has_full_access === false ? (
          <PaywallMessage
            type="instructions"
            cookbook={recipe.cookbook}
            message={recipe.paywall_message}
          />
        ) : recipe.instructions && recipe.instructions.length > 0 ? (
          <ol className="space-y-4">
            {recipe.instructions
              .sort((a, b) => a.step_number - b.step_number)
              .map((instruction) => {
                // Determine which text to display based on toggle
                const displayText = showOriginalText && instruction.original_text
                  ? instruction.original_text
                  : instruction.text;

                return (
                  <li key={instruction.id} className="flex space-x-4">
                    <div className="flex-shrink-0 w-8 h-8 bg-accent text-black rounded-full flex items-center justify-center font-medium">
                      {instruction.step_number}
                    </div>
                    <div className="flex-1 pt-1">
                      <p className="text-text-primary leading-relaxed mb-3">{displayText}</p>

                      {/* Step image if available */}
                      {(instruction.cloudinary_thumbnail_url || instruction.image_url) && (
                        <div className="mt-3">
                          <img
                            src={instruction.cloudinary_thumbnail_url || instruction.image_url || undefined}
                            alt={`Step ${instruction.step_number} illustration`}
                            className="max-w-sm h-48 object-cover rounded-lg border border-gray-200 cursor-pointer hover:opacity-90 transition-opacity"
                            onClick={() => {
                              // Open larger image in new tab/window
                              const fullImageUrl = instruction.cloudinary_url || instruction.image_url;
                              if (fullImageUrl) {
                                window.open(fullImageUrl, '_blank');
                              }
                            }}
                          />
                        </div>
                      )}

                      {/* User's step note */}
                      {instruction.user_note && (
                        <div className="mt-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
                          <p className="text-sm text-amber-800 flex items-start gap-1.5">
                            <svg className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            {instruction.user_note}
                          </p>
                        </div>
                      )}
                    </div>
                  </li>
                );
              })}
          </ol>
        ) : (
          <p className="text-text-secondary">No instructions provided</p>
        )}
      </div>
    </div>
  );
};

export { RecipeInstructionsList };
