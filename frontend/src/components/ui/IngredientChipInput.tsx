import React, { useState, useCallback, useRef, useEffect } from 'react';
import { recipesApi } from '../../services/recipesApi';

interface IngredientSuggestion {
  id: number;
  name: string;
}

interface IngredientChipInputProps {
  selectedIngredients: string[];
  onIngredientsChange: (ingredients: string[]) => void;
  matchMode: 'any' | 'all';
  onMatchModeChange: (mode: 'any' | 'all') => void;
}

export const IngredientChipInput: React.FC<IngredientChipInputProps> = ({
  selectedIngredients,
  onIngredientsChange,
  matchMode,
  onMatchModeChange,
}) => {
  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<IngredientSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Debounced search for ingredient suggestions
  const searchIngredients = useCallback(async (query: string) => {
    if (query.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setIsLoading(true);
    try {
      const result = await recipesApi.searchIngredients(query);
      // Filter out already selected ingredients
      const filtered = result.ingredients.filter(
        (ing) => !selectedIngredients.some(
          (selected) => selected.toLowerCase() === ing.name.toLowerCase()
        )
      );
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
      setHighlightedIndex(-1);
    } catch (error) {
      console.error('Error searching ingredients:', error);
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedIngredients]);

  // Handle input change with debounce
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInputValue(value);

    // Clear previous debounce
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Debounce the search
    debounceRef.current = setTimeout(() => {
      searchIngredients(value);
    }, 300);
  };

  // Add ingredient to selected list
  const addIngredient = (ingredientName: string) => {
    const trimmed = ingredientName.trim();
    if (trimmed && !selectedIngredients.some(
      (ing) => ing.toLowerCase() === trimmed.toLowerCase()
    )) {
      onIngredientsChange([...selectedIngredients, trimmed]);
    }
    setInputValue('');
    setSuggestions([]);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  // Remove ingredient from selected list
  const removeIngredient = (index: number) => {
    onIngredientsChange(selectedIngredients.filter((_, i) => i !== index));
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
        addIngredient(suggestions[highlightedIndex].name);
      } else if (inputValue.trim()) {
        addIngredient(inputValue);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev < suggestions.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setHighlightedIndex(-1);
    } else if (e.key === 'Backspace' && !inputValue && selectedIngredients.length > 0) {
      removeIngredient(selectedIngredients.length - 1);
    }
  };

  // Click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return (
    <div className="space-y-3">
      {/* Match mode toggle */}
      <div className="flex items-center gap-4">
        <span className="text-sm text-text-secondary">Match:</span>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              name="matchMode"
              value="any"
              checked={matchMode === 'any'}
              onChange={() => onMatchModeChange('any')}
              className="w-4 h-4 text-accent focus:ring-accent border-gray-300"
            />
            <span className="text-sm text-text-primary">Any ingredient</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              name="matchMode"
              value="all"
              checked={matchMode === 'all'}
              onChange={() => onMatchModeChange('all')}
              className="w-4 h-4 text-accent focus:ring-accent border-gray-300"
            />
            <span className="text-sm text-text-primary">All ingredients</span>
          </label>
        </div>
      </div>

      {/* Input area with chips */}
      <div className="relative">
        <div
          className="flex flex-wrap gap-2 p-2 min-h-[44px] border border-gray-300 rounded-lg bg-white focus-within:ring-2 focus-within:ring-accent/20 focus-within:border-accent cursor-text"
          onClick={() => inputRef.current?.focus()}
        >
          {/* Selected ingredient chips */}
          {selectedIngredients.map((ingredient, index) => (
            <span
              key={index}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-accent/10 text-accent rounded-full text-sm font-medium"
            >
              {ingredient}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  removeIngredient(index);
                }}
                className="ml-0.5 p-0.5 rounded-full hover:bg-accent/20 transition-colors"
                aria-label={`Remove ${ingredient}`}
              >
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </span>
          ))}

          {/* Text input */}
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (suggestions.length > 0) {
                setShowSuggestions(true);
              }
            }}
            placeholder={
              selectedIngredients.length === 0
                ? "Type ingredient name..."
                : ""
            }
            className="flex-1 min-w-[120px] outline-none border-none bg-transparent text-sm"
          />

          {/* Loading indicator */}
          {isLoading && (
            <div className="absolute right-2 top-1/2 -translate-y-1/2">
              <svg
                className="animate-spin w-4 h-4 text-accent"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
          )}
        </div>

        {/* Autocomplete suggestions dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <div
            ref={suggestionsRef}
            className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto"
          >
            {suggestions.map((suggestion, index) => (
              <button
                key={suggestion.id}
                type="button"
                onClick={() => addIngredient(suggestion.name)}
                className={`w-full px-3 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                  index === highlightedIndex ? 'bg-accent/10 text-accent' : 'text-text-primary'
                }`}
              >
                {suggestion.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Helper text */}
      {selectedIngredients.length > 0 && (
        <p className="text-xs text-text-secondary">
          {matchMode === 'any'
            ? 'Showing recipes with at least one of these ingredients'
            : 'Showing recipes with all of these ingredients'}
        </p>
      )}
    </div>
  );
};
