import React from 'react';
import type { Ingredient } from '../../types';
import { scaleQuantity, isScalableQuantity } from '../../utils/recipeScaling';

interface CookingModeIngredientsProps {
  ingredients: Ingredient[];
  scaleFactor: number;
  servings?: number;
}

const CookingModeIngredients: React.FC<CookingModeIngredientsProps> = ({
  ingredients,
  scaleFactor,
  servings,
}) => {
  const sorted = [...ingredients].sort((a, b) => a.order - b.order);

  return (
    <div className="px-6 py-4">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: '#f15f1c' }}>
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <div>
          <h2 className="text-2xl font-bold" style={{ color: '#1c120d' }}>Ingredients</h2>
          {servings && (
            <p className="text-sm text-gray-500">
              {scaleFactor !== 1 ? `${Math.round(servings * scaleFactor)} servings (scaled)` : `${servings} servings`}
            </p>
          )}
        </div>
      </div>

      <ul className="space-y-4">
        {sorted.map((ingredient) => {
          const scaledQuantity = ingredient.quantity && isScalableQuantity(ingredient.quantity)
            ? scaleQuantity(ingredient.quantity, scaleFactor)
            : ingredient.quantity?.toString();

          return (
            <li key={ingredient.id} className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full mt-2.5 flex-shrink-0" style={{ backgroundColor: '#f15f1c' }} />
              <span className="text-lg leading-relaxed" style={{ color: '#1c120d' }}>
                {scaledQuantity && ingredient.unit ? (
                  <span className="font-semibold">{scaledQuantity} {ingredient.unit} </span>
                ) : scaledQuantity ? (
                  <span className="font-semibold">{scaledQuantity} </span>
                ) : null}
                {ingredient.name}
                {ingredient.preparation && (
                  <span className="text-gray-500">, {ingredient.preparation}</span>
                )}
                {Boolean(ingredient.optional) && (
                  <span className="text-gray-400 italic"> (optional)</span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export { CookingModeIngredients };
