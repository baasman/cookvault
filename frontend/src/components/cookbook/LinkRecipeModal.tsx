import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recipesApi } from '../../services/recipesApi';
import { Modal, Button, SearchBar } from '../ui';

interface LinkRecipeModalProps {
  isOpen: boolean;
  onClose: () => void;
  cookbookId: number;
  cookbookTitle: string;
  currentRecipeIds: number[];
}

const LinkRecipeModal: React.FC<LinkRecipeModalProps> = ({
  isOpen,
  onClose,
  cookbookId,
  cookbookTitle,
  currentRecipeIds,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRecipeId, setSelectedRecipeId] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<string>('');
  const queryClient = useQueryClient();

  // Fetch user's recipes (filter=mine)
  const { data: recipesData, isLoading } = useQuery({
    queryKey: ['user-recipes', searchTerm],
    queryFn: () => recipesApi.fetchRecipes({ filter: 'mine', search: searchTerm, per_page: 100 }),
    enabled: isOpen,
  });

  // Filter out recipes that are already in this cookbook
  const availableRecipes = recipesData?.recipes?.filter(
    recipe => !currentRecipeIds.includes(recipe.id)
  ) || [];

  // Mutation to link recipe to cookbook
  const linkMutation = useMutation({
    mutationFn: ({ recipeId, pageNum }: { recipeId: number; pageNum?: number }) =>
      recipesApi.linkRecipeToCookbook(recipeId, cookbookId, pageNum),
    onSuccess: () => {
      // Invalidate and refetch cookbook data
      queryClient.invalidateQueries({ queryKey: ['cookbook', cookbookId] });
      queryClient.invalidateQueries({ queryKey: ['user-recipes'] });

      // Reset form and close modal
      setSelectedRecipeId(null);
      setPageNumber('');
      setSearchTerm('');
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRecipeId) return;

    const pageNum = pageNumber ? parseInt(pageNumber, 10) : undefined;
    linkMutation.mutate({ recipeId: selectedRecipeId, pageNum });
  };

  const handleClose = () => {
    setSelectedRecipeId(null);
    setPageNumber('');
    setSearchTerm('');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="lg">
      <div className="p-6">
        <h2 id="modal-title" className="text-2xl font-bold mb-4 text-text-primary">
          Link Recipe to "{cookbookTitle}"
        </h2>

        {/* Search Bar */}
        <div className="mb-4">
          <SearchBar
            value={searchTerm}
            onChange={setSearchTerm}
            placeholder="Search your recipes..."
            className="w-full"
          />
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2" style={{borderColor: '#f15f1c'}}></div>
          </div>
        )}

        {/* No Recipes Available */}
        {!isLoading && availableRecipes.length === 0 && (
          <div className="text-center py-12">
            <p className="text-text-secondary mb-4">
              {searchTerm
                ? `No recipes found matching "${searchTerm}"`
                : "You don't have any recipes available to link to this cookbook."
              }
            </p>
            {searchTerm && (
              <Button onClick={() => setSearchTerm('')}>
                Clear Search
              </Button>
            )}
          </div>
        )}

        {/* Recipe List */}
        {!isLoading && availableRecipes.length > 0 && (
          <form onSubmit={handleSubmit}>
            <div className="max-h-96 overflow-y-auto mb-4 space-y-2">
              {availableRecipes.map((recipe) => (
                <div
                  key={recipe.id}
                  onClick={() => setSelectedRecipeId(recipe.id)}
                  className={`
                    p-4 border rounded-lg cursor-pointer transition-all
                    ${selectedRecipeId === recipe.id
                      ? 'border-accent bg-primary-50'
                      : 'border-border-light hover:border-accent/50 hover:bg-gray-50'
                    }
                  `}
                >
                  <div className="flex items-start space-x-3">
                    {/* Radio Button */}
                    <input
                      type="radio"
                      name="recipe"
                      checked={selectedRecipeId === recipe.id}
                      onChange={() => setSelectedRecipeId(recipe.id)}
                      className="mt-1"
                      style={{ accentColor: '#f15f1c' }}
                    />

                    {/* Recipe Info */}
                    <div className="flex-1">
                      <h3 className="font-semibold text-text-primary">
                        {recipe.title}
                      </h3>
                      {recipe.description && (
                        <p className="text-sm text-text-secondary line-clamp-2 mt-1">
                          {recipe.description}
                        </p>
                      )}
                      {recipe.cookbook && (
                        <p className="text-xs text-text-secondary mt-1">
                          Currently in: {recipe.cookbook.title}
                          {recipe.page_number && ` (Page ${recipe.page_number})`}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Page Number Input */}
            {selectedRecipeId && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Page Number (Optional)
                </label>
                <input
                  type="number"
                  min="1"
                  value={pageNumber}
                  onChange={(e) => setPageNumber(e.target.value)}
                  placeholder="Enter page number..."
                  className="w-full px-4 py-2 border border-border-light rounded-lg focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                />
              </div>
            )}

            {/* Error Message */}
            {linkMutation.isError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">
                  {linkMutation.error instanceof Error
                    ? linkMutation.error.message
                    : 'Failed to link recipe to cookbook'}
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3">
              <Button
                type="button"
                variant="secondary"
                onClick={handleClose}
                disabled={linkMutation.isPending}
                className="border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!selectedRecipeId || linkMutation.isPending}
                style={{
                  backgroundColor: selectedRecipeId && !linkMutation.isPending ? '#f15f1c' : '#9ca3af',
                  color: 'white',
                }}
                className="hover:opacity-90 transition-opacity"
              >
                {linkMutation.isPending ? 'Linking...' : 'Link Recipe'}
              </Button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
};

export { LinkRecipeModal };
