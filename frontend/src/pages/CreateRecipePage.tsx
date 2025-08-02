import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { recipesApi } from '../services/recipesApi';
import { RecipeForm } from '../components/recipe/RecipeForm';
import { Button, Input } from '../components/ui';
import { CookbookSearch } from '../components/cookbook/CookbookSearch';
import { GoogleBooksSearch } from '../components/cookbook/GoogleBooksSearch';
import { cookbooksApi, type GoogleBook } from '../services/cookbooksApi';
import type { Recipe } from '../types';

const CreateRecipePage: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<'initial' | 'form'>('initial');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  
  // Initial creation form state
  const [initialData, setInitialData] = useState({
    title: '',
    no_cookbook: true,
    create_new_cookbook: false,
    search_existing_cookbook: false,
    search_google_books: false,
    selected_existing_cookbook_id: undefined as number | undefined,
    selected_google_book: null as GoogleBook | null,
    cookbook_id: undefined as number | undefined,
    new_cookbook_title: '',
    new_cookbook_author: '',
    new_cookbook_description: '',
    new_cookbook_publisher: '',
    new_cookbook_isbn: '',
    new_cookbook_publication_date: '',
  });

  const handleInitialSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!initialData.title.trim()) {
      setError('Recipe title is required');
      return;
    }

    // Validate cookbook selection if required
    if (initialData.create_new_cookbook && !initialData.new_cookbook_title.trim()) {
      setError('Cookbook title is required');
      return;
    }

    if (initialData.search_existing_cookbook && !initialData.selected_existing_cookbook_id) {
      setError('Please select a cookbook');
      return;
    }

    if (initialData.search_google_books && !initialData.selected_google_book) {
      setError('Please select a cookbook from the online database');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      let cookbook_id = undefined;

      // Handle cookbook creation/selection
      if (initialData.create_new_cookbook) {
        // Create new cookbook first
        const cookbook = await cookbooksApi.createCookbook({
          title: initialData.new_cookbook_title,
          author: initialData.new_cookbook_author,
          description: initialData.new_cookbook_description,
          publisher: initialData.new_cookbook_publisher,
          isbn: initialData.new_cookbook_isbn,
          publication_date: initialData.new_cookbook_publication_date || undefined,
        });
        cookbook_id = cookbook.id;
      } else if (initialData.search_existing_cookbook && initialData.selected_existing_cookbook_id) {
        cookbook_id = initialData.selected_existing_cookbook_id;
      } else if (initialData.search_google_books && initialData.cookbook_id) {
        cookbook_id = initialData.cookbook_id;
      }

      // Create empty recipe
      const newRecipe = await recipesApi.createEmptyRecipe(initialData.title, cookbook_id);
      setRecipe(newRecipe);
      setStep('form');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create recipe');
    } finally {
      setLoading(false);
    }
  };

  const handleRecipeSave = (updatedRecipe: Recipe) => {
    setRecipe(updatedRecipe);
    // Could show a success message or auto-save indicator here
  };

  const handleCancel = () => {
    if (step === 'form') {
      // Ask if they want to go back to initial form or cancel entirely
      if (confirm('Do you want to go back to the recipe details, or cancel and lose your changes?')) {
        setStep('initial');
      }
    } else {
      navigate('/recipes');
    }
  };

  const handleComplete = () => {
    if (recipe) {
      navigate(`/recipes/${recipe.id}`);
    }
  };

  if (step === 'form' && recipe) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{color: '#1c120d'}}>
              Create Recipe: {recipe.title}
            </h1>
            <p className="text-text-secondary">
              Fill in the details for your new recipe
            </p>
          </div>
          <Button onClick={handleComplete} variant="primary">
            View Recipe
          </Button>
        </div>
        
        <RecipeForm
          recipe={recipe}
          mode="create"
          onSave={handleRecipeSave}
          onCancel={handleCancel}
        />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-page-title font-bold mb-4" style={{color: '#1c120d'}}>
          Create New Recipe
        </h1>
        <p className="text-lg" style={{color: '#9b644b'}}>
          Start by giving your recipe a title and optionally associating it with a cookbook
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
        <form onSubmit={handleInitialSubmit} className="space-y-6">
          {/* Recipe Title */}
          <div>
            <Input
              label="Recipe Title *"
              placeholder="Enter your recipe title"
              value={initialData.title}
              onChange={(value) => setInitialData(prev => ({ ...prev, title: value }))}
              required
            />
          </div>

          {/* Cookbook Options */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium" style={{color: '#1c120d'}}>
              Cookbook Association (Optional)
            </h3>
            
            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="cookbook_mode"
                  checked={initialData.no_cookbook}
                  onChange={() => setInitialData(prev => ({ 
                    ...prev, 
                    no_cookbook: true,
                    create_new_cookbook: false,
                    search_existing_cookbook: false,
                    search_google_books: false,
                    selected_existing_cookbook_id: undefined,
                    selected_google_book: null,
                    cookbook_id: undefined
                  }))}
                  className="mr-2 text-accent"
                />
                <span className="text-sm font-medium" style={{color: '#1c120d'}}>
                  No cookbook (standalone recipe)
                </span>
              </label>

              <label className="flex items-center">
                <input
                  type="radio"
                  name="cookbook_mode"
                  checked={initialData.search_google_books}
                  onChange={() => setInitialData(prev => ({ 
                    ...prev, 
                    no_cookbook: false,
                    create_new_cookbook: false,
                    search_existing_cookbook: false,
                    search_google_books: true,
                    selected_existing_cookbook_id: undefined,
                    selected_google_book: null,
                    cookbook_id: undefined
                  }))}
                  className="mr-2 text-accent"
                />
                <span className="text-sm font-medium" style={{color: '#1c120d'}}>
                  Search Online Database
                </span>
              </label>

              <label className="flex items-center">
                <input
                  type="radio"
                  name="cookbook_mode"
                  checked={initialData.search_existing_cookbook}
                  onChange={() => setInitialData(prev => ({ 
                    ...prev, 
                    no_cookbook: false,
                    create_new_cookbook: false,
                    search_existing_cookbook: true,
                    search_google_books: false,
                    selected_existing_cookbook_id: undefined,
                    selected_google_book: null,
                    cookbook_id: undefined
                  }))}
                  className="mr-2 text-accent"
                />
                <span className="text-sm font-medium" style={{color: '#1c120d'}}>
                  Add to existing cookbook
                </span>
              </label>

              <label className="flex items-center">
                <input
                  type="radio"
                  name="cookbook_mode"
                  checked={initialData.create_new_cookbook}
                  onChange={() => setInitialData(prev => ({ 
                    ...prev, 
                    no_cookbook: false,
                    create_new_cookbook: true,
                    search_existing_cookbook: false,
                    search_google_books: false,
                    selected_existing_cookbook_id: undefined,
                    selected_google_book: null,
                    cookbook_id: undefined
                  }))}
                  className="mr-2 text-accent"
                />
                <span className="text-sm font-medium" style={{color: '#1c120d'}}>
                  Create new cookbook
                </span>
              </label>
            </div>

            {/* Cookbook-specific forms */}
            {initialData.search_google_books && (
              <GoogleBooksSearch
                onBookSelect={async (book: GoogleBook) => {
                  try {
                    const cookbook = await cookbooksApi.createCookbookFromGoogleBooks(book.google_books_id);
                    setInitialData(prev => ({ 
                      ...prev, 
                      selected_google_book: book,
                      cookbook_id: cookbook.id
                    }));
                  } catch (error) {
                    console.error('Error creating cookbook from Google Books:', error);
                    setError('Failed to create cookbook from online database. Please try again.');
                  }
                }}
                onManualEntry={() => {
                  setInitialData(prev => ({ 
                    ...prev, 
                    create_new_cookbook: true,
                    search_google_books: false,
                    selected_google_book: null 
                  }));
                }}
                isLoading={loading}
              />
            )}

            {initialData.search_existing_cookbook && (
              <CookbookSearch
                onSelect={(cookbook) => {
                  setInitialData(prev => ({ 
                    ...prev, 
                    selected_existing_cookbook_id: cookbook.id
                  }));
                }}
                onCreateNew={() => {
                  setInitialData(prev => ({ 
                    ...prev, 
                    create_new_cookbook: true,
                    search_existing_cookbook: false
                  }));
                }}
              />
            )}

            {initialData.create_new_cookbook && (
              <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium" style={{color: '#1c120d'}}>
                  New Cookbook Details
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Cookbook Title *"
                    placeholder="Enter cookbook title"
                    value={initialData.new_cookbook_title}
                    onChange={(value) => setInitialData(prev => ({ ...prev, new_cookbook_title: value }))}
                    required
                  />
                  <Input
                    label="Author"
                    placeholder="Enter author name"
                    value={initialData.new_cookbook_author}
                    onChange={(value) => setInitialData(prev => ({ ...prev, new_cookbook_author: value }))}
                  />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Publisher"
                    placeholder="Enter publisher name"
                    value={initialData.new_cookbook_publisher}
                    onChange={(value) => setInitialData(prev => ({ ...prev, new_cookbook_publisher: value }))}
                  />
                  <Input
                    label="ISBN"
                    placeholder="Enter ISBN"
                    value={initialData.new_cookbook_isbn}
                    onChange={(value) => setInitialData(prev => ({ ...prev, new_cookbook_isbn: value }))}
                  />
                </div>
                
                <Input
                  label="Publication Date"
                  type="date"
                  value={initialData.new_cookbook_publication_date}
                  onChange={(value) => setInitialData(prev => ({ ...prev, new_cookbook_publication_date: value }))}
                />
                
                <div>
                  <label className="block text-sm font-medium mb-2" style={{color: '#1c120d'}}>
                    Description
                  </label>
                  <textarea
                    placeholder="Enter cookbook description (optional)"
                    value={initialData.new_cookbook_description}
                    onChange={(e) => setInitialData(prev => ({ ...prev, new_cookbook_description: e.target.value }))}
                    rows={3}
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent resize-none"
                    style={{borderColor: '#e8d7cf'}}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-4 rounded-xl" style={{backgroundColor: '#fee2e2', color: '#dc2626'}}>
              <p className="text-sm font-medium">{error}</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-center space-x-4 pt-4">
            <Button
              type="button"
              onClick={handleCancel}
              variant="secondary"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading || !initialData.title.trim()}
              variant="primary"
            >
              {loading ? 'Creating...' : 'Create Recipe'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export { CreateRecipePage };