import React, { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SearchBar, Button, Modal } from '../components/ui';
import { RecipeCard } from '../components/recipe';
import { RecipeGroupCard } from '../components/recipe/RecipeGroupCard';
import { recipesApi } from '../services/recipesApi';
import { recipeGroupsApi } from '../services/recipeGroupsApi';
import { useAuth } from '../contexts/AuthContext';
import type { Recipe } from '../types';
import toast from 'react-hot-toast';

type RecipeFilter = 'collection' | 'discover' | 'mine' | 'groups';

const RecipesPage: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [activeFilter, setActiveFilter] = useState<RecipeFilter>('discover');
  const [showCreateGroupForm, setShowCreateGroupForm] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');
  const recipesPerPage = 12;

  // Fetch recipes using React Query
  const { 
    data: recipesData, 
    isLoading, 
    error, 
    refetch 
  } = useQuery({
    queryKey: ['recipes', currentPage, searchTerm, activeFilter],
    queryFn: () => recipesApi.fetchRecipes({ 
      page: currentPage, 
      per_page: recipesPerPage,
      search: searchTerm,
      filter: activeFilter === 'groups' ? 'mine' : activeFilter
    }),
    enabled: isAuthenticated && activeFilter !== 'groups', // Only fetch if user is authenticated and not viewing groups
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch recipe groups using React Query
  const { 
    data: groupsData, 
    isLoading: isLoadingGroups, 
    error: groupsError, 
    refetch: refetchGroups 
  } = useQuery({
    queryKey: ['recipe-groups', user?.id],
    queryFn: () => recipeGroupsApi.getRecipeGroups(),
    enabled: isAuthenticated && activeFilter === 'groups', // Only fetch when viewing groups
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Reset to page 1 when search term or filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, activeFilter]);

  // Recipes are now filtered on the backend, so just use them directly
  const filteredRecipes = recipesData?.recipes || [];

  // Filter groups based on search term
  const filteredGroups = useMemo(() => {
    if (!groupsData?.groups) return [];
    
    if (!searchTerm) return groupsData.groups;
    
    const lowerSearchTerm = searchTerm.toLowerCase();
    return groupsData.groups.filter(group => 
      group.name.toLowerCase().includes(lowerSearchTerm) ||
      (group.description && group.description.toLowerCase().includes(lowerSearchTerm))
    );
  }, [groupsData?.groups, searchTerm]);

  // Create group mutation
  const createGroupMutation = useMutation({
    mutationFn: (params: { name: string; description?: string }) => 
      recipeGroupsApi.createRecipeGroup({ 
        name: params.name.trim(),
        description: params.description?.trim() || undefined,
        is_private: true 
      }),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['recipe-groups', user?.id] });
      toast.success(`Group "${response.group.name}" created successfully!`);
      setShowCreateGroupForm(false);
      setNewGroupName('');
      setNewGroupDescription('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create group');
    },
  });

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleFilterChange = (filter: RecipeFilter) => {
    setActiveFilter(filter);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCreateGroup = () => {
    if (!newGroupName.trim()) {
      toast.error('Group name is required');
      return;
    }
    createGroupMutation.mutate({
      name: newGroupName,
      description: newGroupDescription
    });
  };

  const handleCancelCreateGroup = () => {
    setShowCreateGroupForm(false);
    setNewGroupName('');
    setNewGroupDescription('');
  };

  // Get page content based on active filter
  const getPageContent = () => {
    switch (activeFilter) {
      case 'mine':
        return {
          title: 'My Uploads',
          description: 'Recipes you have uploaded and created',
          searchPlaceholder: 'Search your uploaded recipes...'
        };
      case 'discover':
        return {
          title: 'Discover Recipes',
          description: 'Browse and search all public recipes',
          searchPlaceholder: 'Search all public recipes...'
        };
      case 'groups':
        return {
          title: 'Recipe Groups',
          description: 'Your organized recipe collections',
          searchPlaceholder: 'Search your groups...'
        };
      case 'collection':
      default:
        return {
          title: 'My Collection',
          description: 'Your curated collection of recipes',
          searchPlaceholder: 'Search your collection...'
        };
    }
  };

  const pageContent = getPageContent();

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Please log in to view your recipes
        </h2>
        <p style={{color: '#9b644b'}}>
          Sign in to access your personalized recipe collection.
        </p>
      </div>
    );
  }

  if (error || groupsError) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Unable to load {activeFilter === 'groups' ? 'recipe groups' : 'recipes'}
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          There was an error loading your {activeFilter === 'groups' ? 'recipe groups' : 'recipes'}. Please try again.
        </p>
        <button
          onClick={() => activeFilter === 'groups' ? refetchGroups() : refetch()}
          className="px-4 py-2 bg-accent text-white rounded-lg hover:opacity-90 transition-opacity"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2" style={{color: '#1c120d'}}>
          {pageContent.title}
        </h1>
        <p style={{color: '#9b644b'}}>
          {pageContent.description}
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex justify-center mb-6">
        <div className="flex bg-background-secondary rounded-lg p-1">
          {([
            { key: 'discover', label: 'Discover' },
            { key: 'collection', label: 'My Collection' },
            { key: 'mine', label: 'My Uploads' },
            { key: 'groups', label: 'Recipe Groups' }
          ] as const).map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handleFilterChange(key)}
              className={`px-6 py-2 text-sm font-medium rounded-md transition-colors ${
                activeFilter === key
                  ? 'bg-white text-text-primary shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex justify-center mb-8">
        <SearchBar
          value={searchTerm}
          onChange={handleSearch}
          placeholder={pageContent.searchPlaceholder}
          className="w-full max-w-2xl"
        />
      </div>

      {/* Loading State */}
      {(isLoading || isLoadingGroups) && (
        <div className="flex justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
            <p style={{color: '#9b644b'}}>Loading your {activeFilter === 'groups' ? 'recipe groups' : 'recipes'}...</p>
          </div>
        </div>
      )}

      {/* Recipe Groups Content */}
      {activeFilter === 'groups' && !isLoadingGroups && (
        <>
          {/* Create Group Button */}
          <div className="flex justify-center mb-8">
            <Button
              onClick={() => setShowCreateGroupForm(true)}
              variant="primary"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Create New Group
            </Button>
          </div>

          {filteredGroups.length > 0 ? (
            <>
              {/* Results count */}
              <div className="text-sm text-text-secondary mb-4">
                {searchTerm ? (
                  <p>
                    Found {filteredGroups.length} group{filteredGroups.length !== 1 ? 's' : ''} 
                    matching "{searchTerm}"
                  </p>
                ) : (
                  <p>
                    Showing {filteredGroups.length} recipe group{filteredGroups.length !== 1 ? 's' : ''}
                  </p>
                )}
              </div>

              {/* Groups Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredGroups.map((group) => (
                  <RecipeGroupCard key={group.id} group={group} />
                ))}
              </div>
            </>
          ) : (
            /* Empty State */
            <div className="text-center py-12">
              <div className="max-w-md mx-auto">
                <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-text-primary mb-2">
                  {searchTerm ? 'No groups found' : 'No recipe groups yet'}
                </h3>
                <p className="text-text-secondary mb-4">
                  {searchTerm 
                    ? `No groups match "${searchTerm}". Try a different search term.`
                    : 'Create your first recipe group to organize your recipes like "Italian Favorites", "Quick Weeknight Meals", or "Holiday Specials".'
                  }
                </p>
                {!searchTerm && (
                  <Button
                    onClick={() => setShowCreateGroupForm(true)}
                    variant="primary"
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    Create Your First Group
                  </Button>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Recipe Grid */}
      {activeFilter !== 'groups' && !isLoading && (
        <>
          {filteredRecipes.length > 0 ? (
            <>
              {/* Results count */}
              <div className="text-sm text-text-secondary mb-4">
                {searchTerm ? (
                  <p>
                    Found {filteredRecipes.length} recipe{filteredRecipes.length !== 1 ? 's' : ''} 
                    {activeFilter === 'mine' ? ' in your uploaded recipes' : 
                     activeFilter === 'collection' ? ' in your collection' : 
                     activeFilter === 'discover' ? ' in public recipes' : ''}
                    {searchTerm && ` matching "${searchTerm}"`}
                  </p>
                ) : (
                  <p>
                    Showing {filteredRecipes.length} 
                    {activeFilter === 'mine' ? ' of your uploaded recipes' : 
                     activeFilter === 'collection' ? ' recipes in your collection' : 
                     activeFilter === 'discover' ? ` of ${recipesData?.total || 0} public recipes` :
                     ` of ${recipesData?.total || 0} recipes`}
                  </p>
                )}
              </div>

              {/* Recipe Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredRecipes.map((recipe: Recipe) => (
                  <RecipeCard
                    key={recipe.id}
                    recipe={recipe}
                    showAddToCollection={activeFilter === 'discover'}
                  />
                ))}
              </div>

              {/* Pagination */}
              {recipesData && recipesData.pages > 1 && !searchTerm && (
                <div className="flex justify-center mt-8">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="px-4 py-2 text-sm border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:bg-background-secondary"
                      style={{borderColor: '#e8d7cf', color: '#9b644b'}}
                    >
                      Previous
                    </button>
                    
                    <div className="flex items-center space-x-1">
                      {Array.from({ length: Math.min(recipesData.pages, 5) }, (_, i) => {
                        const pageNum = i + 1;
                        return (
                          <button
                            key={pageNum}
                            onClick={() => handlePageChange(pageNum)}
                            className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                              currentPage === pageNum
                                ? 'bg-accent text-white'
                                : 'text-text-secondary hover:bg-background-secondary'
                            }`}
                          >
                            {pageNum}
                          </button>
                        );
                      })}
                    </div>

                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === recipesData.pages}
                      className="px-4 py-2 text-sm border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:bg-background-secondary"
                      style={{borderColor: '#e8d7cf', color: '#9b644b'}}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            /* Empty State */
            <div className="text-center py-16">
              <div className="mb-6">
                <svg 
                  className="h-16 w-16 mx-auto text-primary-300 mb-4" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={1} 
                    d={activeFilter === 'discover' ? "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" : "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"}
                  />
                </svg>
              </div>
              
              {activeFilter === 'discover' && !searchTerm ? (
                <>
                  <h3 className="text-xl font-semibold mb-2" style={{color: '#1c120d'}}>
                    No recipes to discover yet
                  </h3>
                  <p className="mb-6" style={{color: '#9b644b'}}>
                    There are no public recipes available to discover at the moment. Check back later or use the search bar to find specific recipes.
                  </p>
                </>
              ) : searchTerm ? (
                <>
                  <h3 className="text-xl font-semibold mb-2" style={{color: '#1c120d'}}>
                    No recipes found
                  </h3>
                  <p className="mb-4" style={{color: '#9b644b'}}>
                    No recipes match your search for "{searchTerm}". Try different keywords.
                  </p>
                  <button
                    onClick={() => setSearchTerm('')}
                    className="px-4 py-2 bg-accent text-white rounded-lg hover:opacity-90 transition-opacity"
                  >
                    Clear search
                  </button>
                </>
              ) : (
                <>
                  <h3 className="text-xl font-semibold mb-2" style={{color: '#1c120d'}}>
                    {activeFilter === 'collection' ? 'No recipes in your collection yet' : 'No recipes yet'}
                  </h3>
                  <p className="mb-6" style={{color: '#9b644b'}}>
                    {activeFilter === 'collection' 
                      ? 'Discover recipes or upload your own to start building your collection!'
                      : 'Start building your recipe collection by uploading your first recipe!'
                    }
                  </p>
                  {activeFilter === 'collection' ? (
                    <div className="flex gap-4 justify-center">
                      <button
                        onClick={() => handleFilterChange('discover')}
                        className="px-6 py-3 bg-accent text-white rounded-lg hover:opacity-90 transition-opacity font-medium"
                      >
                        Discover Recipes
                      </button>
                      <a 
                        href="/upload" 
                        className="inline-block px-6 py-3 border border-accent text-accent rounded-lg hover:bg-accent hover:text-white transition-colors font-medium"
                      >
                        Upload Recipe
                      </a>
                    </div>
                  ) : (
                    <a 
                      href="/upload" 
                      className="inline-block px-6 py-3 bg-accent text-white rounded-lg hover:opacity-90 transition-opacity font-medium"
                    >
                      Upload Your First Recipe
                    </a>
                  )}
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* Create Group Modal */}
      <Modal
        isOpen={showCreateGroupForm}
        onClose={handleCancelCreateGroup}
        size="md"
      >
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4" style={{ color: '#1c120d' }}>
            Create New Recipe Group
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Group Name *
              </label>
              <input
                type="text"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                placeholder="e.g., Italian Favorites, Quick Weeknight Meals..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
                maxLength={200}
                disabled={createGroupMutation.isPending}
                autoFocus
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Description (optional)
              </label>
              <textarea
                value={newGroupDescription}
                onChange={(e) => setNewGroupDescription(e.target.value)}
                placeholder="Describe what recipes belong in this group..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent resize-none"
                rows={3}
                disabled={createGroupMutation.isPending}
              />
            </div>
          </div>
          
          <div className="flex justify-end space-x-3 mt-6">
            <Button
              onClick={handleCancelCreateGroup}
              variant="secondary"
              disabled={createGroupMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateGroup}
              variant="primary"
              disabled={!newGroupName.trim() || createGroupMutation.isPending}
            >
              {createGroupMutation.isPending ? 'Creating...' : 'Create Group'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export { RecipesPage };