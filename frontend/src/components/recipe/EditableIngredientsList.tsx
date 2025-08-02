import React, { useState } from 'react';
import { Button } from '../ui';

type EditableIngredient = {
  name: string;
  quantity?: number;
  unit?: string;
  preparation?: string;
  optional: boolean;
};

interface EditableIngredientsListProps {
  ingredients: EditableIngredient[];
  onChange: (ingredients: EditableIngredient[]) => void;
}

export const EditableIngredientsList: React.FC<EditableIngredientsListProps> = ({
  ingredients,
  onChange,
}) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const addIngredient = () => {
    const newIngredient: EditableIngredient = {
      name: '',
      quantity: undefined,
      unit: '',
      preparation: '',
      optional: false,
    };
    onChange([...ingredients, newIngredient]);
    setEditingIndex(ingredients.length);
  };

  const updateIngredient = (index: number, field: keyof EditableIngredient, value: string | number | boolean | undefined) => {
    const updated = [...ingredients];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
  };

  const removeIngredient = (index: number) => {
    const updated = ingredients.filter((_, i) => i !== index);
    onChange(updated);
    if (editingIndex === index) {
      setEditingIndex(null);
    }
  };

  const moveIngredient = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= ingredients.length) return;

    const updated = [...ingredients];
    [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
    onChange(updated);
    
    if (editingIndex === index) {
      setEditingIndex(newIndex);
    }
  };

  const commonUnits = [
    'cup', 'cups', 'tbsp', 'tsp', 'oz', 'lb', 'g', 'kg', 'ml', 'l',
    'pint', 'quart', 'gallon', 'piece', 'pieces', 'slice', 'slices',
    'clove', 'cloves', 'whole', 'medium', 'large', 'small'
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium" style={{color: '#1c120d'}}>
          Ingredients ({ingredients.length})
        </h3>
        <Button onClick={addIngredient} variant="primary" size="sm">
          Add Ingredient
        </Button>
      </div>

      <div className="space-y-3">
        {ingredients.map((ingredient, index) => (
          <div
            key={index}
            className="border rounded-lg p-4 bg-background-secondary"
            style={{borderColor: '#e8d7cf'}}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium text-text-secondary">
                  #{index + 1}
                </span>
                <div className="flex space-x-1">
                  <button
                    onClick={() => moveIngredient(index, 'up')}
                    disabled={index === 0}
                    className="p-1 text-text-secondary hover:text-text-primary disabled:opacity-50"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => moveIngredient(index, 'down')}
                    disabled={index === ingredients.length - 1}
                    className="p-1 text-text-secondary hover:text-text-primary disabled:opacity-50"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => setEditingIndex(editingIndex === index ? null : index)}
                  className="p-1 text-text-secondary hover:text-accent"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  onClick={() => removeIngredient(index)}
                  className="p-1 text-text-secondary hover:text-red-500"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            {editingIndex === index ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Ingredient Name *
                  </label>
                  <input
                    type="text"
                    value={ingredient.name}
                    onChange={(e) => updateIngredient(index, 'name', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                    placeholder="e.g., Flour"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-1">
                      Quantity
                    </label>
                    <input
                      type="number"
                      value={ingredient.quantity || ''}
                      onChange={(e) => updateIngredient(index, 'quantity', parseFloat(e.target.value) || undefined)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                      placeholder="2"
                      step="0.1"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-1">
                      Unit
                    </label>
                    <select
                      value={ingredient.unit || ''}
                      onChange={(e) => updateIngredient(index, 'unit', e.target.value || undefined)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                    >
                      <option value="">Select unit</option>
                      {commonUnits.map(unit => (
                        <option key={unit} value={unit}>{unit}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Preparation
                  </label>
                  <input
                    type="text"
                    value={ingredient.preparation || ''}
                    onChange={(e) => updateIngredient(index, 'preparation', e.target.value || undefined)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                    placeholder="e.g., chopped, diced, minced"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={ingredient.optional || false}
                      onChange={(e) => updateIngredient(index, 'optional', e.target.checked)}
                      className="rounded border-gray-300 text-accent focus:ring-accent"
                    />
                    <span className="text-sm text-text-secondary">Optional</span>
                  </label>
                </div>
              </div>
            ) : (
              <div className="text-text-primary">
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-accent rounded-full mt-2 flex-shrink-0"></div>
                  <div>
                    <span>
                      {ingredient.quantity && ingredient.unit ? (
                        <span className="font-medium">
                          {ingredient.quantity} {ingredient.unit}{' '}
                        </span>
                      ) : ingredient.quantity ? (
                        <span className="font-medium">{ingredient.quantity} </span>
                      ) : null}
                      {ingredient.name}
                      {ingredient.preparation && (
                        <span className="text-text-secondary">, {ingredient.preparation}</span>
                      )}
                      {ingredient.optional && (
                        <span className="text-text-secondary italic"> (optional)</span>
                      )}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {ingredients.length === 0 && (
        <div className="text-center py-8">
          <p className="text-text-secondary mb-4">No ingredients added yet</p>
          <Button onClick={addIngredient} variant="primary" size="sm">
            Add First Ingredient
          </Button>
        </div>
      )}
    </div>
  );
};