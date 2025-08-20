import React, { useState } from 'react';
import type { Recipe } from '../../types';
import { recipesApi } from '../../services/recipesApi';
import { Button } from '../ui';
import { EditableIngredientsList } from './EditableIngredientsList';
import { EditableInstructionsList } from './EditableInstructionsList';
import { RecipeImageDisplay } from './RecipeImageDisplay';

type EditableIngredient = {
  name: string;
  quantity?: number;
  unit?: string;
  preparation?: string;
  optional: boolean;
};

interface RecipeEditFormProps {
  recipe: Recipe;
  onSave: (updatedRecipe: Recipe) => void;
  onCancel: () => void;
}

type TabType = 'metadata' | 'ingredients' | 'instructions' | 'tags';

export const RecipeEditForm: React.FC<RecipeEditFormProps> = ({
  recipe,
  onSave,
  onCancel,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('metadata');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state
  const [formData, setFormData] = useState({
    title: recipe.title || '',
    description: recipe.description || '',
    prep_time: recipe.prep_time || 0,
    cook_time: recipe.cook_time || 0,
    servings: recipe.servings || 0,
    difficulty: recipe.difficulty || '',
  });

  // State to control editing modes in child components
  const [ingredientsEditingIndex, setIngredientsEditingIndex] = useState<number | null>(null);
  const [instructionsEditingIndex, setInstructionsEditingIndex] = useState<number | null>(null);

  const [ingredients, setIngredients] = useState<EditableIngredient[]>(
    recipe.ingredients?.map(ing => ({
      name: ing.name,
      quantity: ing.quantity,
      unit: ing.unit,
      preparation: ing.preparation,
      optional: ing.optional
    })) || []
  );

  const [instructions, setInstructions] = useState(
    recipe.instructions?.map(inst => inst.text) || []
  );

  const [tags, setTags] = useState(
    recipe.tags?.map(tag => tag.name) || []
  );

  const handleInputChange = (field: string, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSaveMetadata = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const updatedRecipe = await recipesApi.updateRecipe(recipe.id, formData);
      onSave(updatedRecipe);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update recipe');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveIngredients = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const updatedRecipe = await recipesApi.updateRecipeIngredients(recipe.id, {
        ingredients
      });
      // Reset ingredients editing state on successful save
      setIngredientsEditingIndex(null);
      onSave(updatedRecipe);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update ingredients');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveInstructions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const updatedRecipe = await recipesApi.updateRecipeInstructions(recipe.id, {
        instructions
      });
      // Reset instructions editing state on successful save
      setInstructionsEditingIndex(null);
      onSave(updatedRecipe);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update instructions');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveTags = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const updatedRecipe = await recipesApi.updateRecipeTags(recipe.id, {
        tags
      });
      onSave(updatedRecipe);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update tags');
    } finally {
      setLoading(false);
    }
  };

  const getSaveHandler = () => {
    switch (activeTab) {
      case 'metadata': return handleSaveMetadata;
      case 'ingredients': return handleSaveIngredients;
      case 'instructions': return handleSaveInstructions;
      case 'tags': return handleSaveTags;
      default: return handleSaveMetadata;
    }
  };

  const tabs = [
    { id: 'metadata', label: 'Recipe Info' },
    { id: 'ingredients', label: 'Ingredients' },
    { id: 'instructions', label: 'Instructions' },
    { id: 'tags', label: 'Tags' }
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold" style={{color: '#1c120d'}}>
          Edit Recipe
        </h2>
        <div className="flex space-x-2">
          <Button
            onClick={onCancel}
            variant="secondary"
            size="sm"
          >
            Cancel
          </Button>
          <Button
            onClick={getSaveHandler()}
            disabled={loading}
            variant="secondary"
            size="sm"
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex space-x-1 mb-6 border-b" style={{borderColor: '#e8d7cf'}}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as TabType)}
            className={`px-4 py-2 font-medium text-sm rounded-t-lg transition-colors ${
              activeTab === tab.id
                ? 'bg-background-secondary text-text-primary border-b-2 border-accent'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === 'metadata' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Recipe Image
              </label>
              <div className="w-48">
                <RecipeImageDisplay 
                  recipe={recipe} 
                  canEdit={true}
                  isEditMode={true}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Recipe Title
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => handleInputChange('title', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                placeholder="Enter recipe title"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                rows={3}
                placeholder="Describe your recipe"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Prep Time (minutes)
                </label>
                <input
                  type="number"
                  value={formData.prep_time}
                  onChange={(e) => handleInputChange('prep_time', parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                  min="0"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Cook Time (minutes)
                </label>
                <input
                  type="number"
                  value={formData.cook_time}
                  onChange={(e) => handleInputChange('cook_time', parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                  min="0"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Servings
                </label>
                <input
                  type="number"
                  value={formData.servings}
                  onChange={(e) => handleInputChange('servings', parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                  min="1"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Difficulty
                </label>
                <select
                  value={formData.difficulty}
                  onChange={(e) => handleInputChange('difficulty', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                >
                  <option value="">Select difficulty</option>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ingredients' && (
          <EditableIngredientsList
            ingredients={ingredients}
            onChange={setIngredients}
            editingIndex={ingredientsEditingIndex}
            onEditingIndexChange={setIngredientsEditingIndex}
          />
        )}

        {activeTab === 'instructions' && (
          <EditableInstructionsList
            instructions={instructions}
            onChange={setInstructions}
            editingIndex={instructionsEditingIndex}
            onEditingIndexChange={setInstructionsEditingIndex}
          />
        )}

        {activeTab === 'tags' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                value={tags.join(', ')}
                onChange={(e) => setTags(e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent focus:border-transparent"
                placeholder="Enter tags separated by commas"
              />
            </div>
            
            <div>
              <p className="text-sm text-text-secondary mb-2">Current tags:</p>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 text-sm rounded-full bg-background-secondary text-text-secondary"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};