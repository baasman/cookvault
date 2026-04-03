import React from 'react';
import { RecipeScaler } from './RecipeScaler';
import { PaywallMessage } from './PaywallMessage';
import { scaleQuantity, isScalableQuantity } from '../../utils/recipeScaling';
import type { Recipe } from '../../types';

interface RecipeIngredientsListProps {
  recipe: Recipe;
  scaleFactor: number;
  isEditing: boolean;
  onScaleChange: (newScaleFactor: number, newDesiredServings: number) => void;
}

const RecipeIngredientsList: React.FC<RecipeIngredientsListProps> = ({
  recipe,
  scaleFactor,
  isEditing,
  onScaleChange,
}) => {
  return (
    <div className="lg:col-span-1">
      <div className="bg-white rounded-xl shadow-sm border p-6 overflow-hidden" style={{borderColor: '#e8d7cf'}}>
        <h2 className="text-xl font-bold mb-4" style={{color: '#1c120d'}}>
          Ingredients
          {scaleFactor !== 1 && (
            <span className="ml-2 text-sm font-normal text-blue-600">
              (Scaled)
            </span>
          )}
        </h2>

        {/* Recipe Scaler Component */}
        {recipe.has_full_access !== false && !isEditing && (
          <RecipeScaler
            originalServings={recipe.servings}
            onScaleChange={onScaleChange}
          />
        )}

        {recipe.has_full_access === false ? (
          <PaywallMessage
            type="ingredients"
            cookbook={recipe.cookbook}
            message={recipe.paywall_message}
          />
        ) : recipe.ingredients && recipe.ingredients.length > 0 ? (
          <ul className="space-y-3">
            {recipe.ingredients
              .sort((a, b) => a.order - b.order)
              .map((ingredient) => {
                const scaledQuantity = ingredient.quantity && isScalableQuantity(ingredient.quantity)
                  ? scaleQuantity(ingredient.quantity, scaleFactor)
                  : ingredient.quantity?.toString();

                return (
                  <li key={ingredient.id} className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-accent rounded-full mt-2 flex-shrink-0"></div>
                    <div className="flex-1">
                      <span className="text-text-primary">
                        {scaledQuantity && ingredient.unit ? (
                          <span className="font-medium">
                            {scaledQuantity} {ingredient.unit}{' '}
                          </span>
                        ) : scaledQuantity ? (
                          <span className="font-medium">{scaledQuantity} </span>
                        ) : null}
                        {ingredient.name}
                        {ingredient.preparation && (
                          <span className="text-text-secondary">, {ingredient.preparation}</span>
                        )}
                        {Boolean(ingredient.optional) && (
                          <span className="text-text-secondary italic"> (optional)</span>
                        )}
                    </span>
                  </div>
                </li>
                );
              })}
          </ul>
        ) : (
          <p className="text-text-secondary">No ingredients listed</p>
        )}
      </div>
    </div>
  );
};

export { RecipeIngredientsList };
