import React, { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { SearchBar } from '../components/ui';
import { RecipeCard } from '../components/recipe';
import { recipesApi } from '../services/recipesApi';
import { useAuth } from '../contexts/AuthContext';
import type { Recipe } from '../types';

type RecipeFilter = 'collection' | 'discover' | 'mine';

const RecipesPage: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [activeFilter, setActiveFilter] = useState<RecipeFilter>('collection');
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
      filter: activeFilter
    }),
    enabled: isAuthenticated, // Only fetch if user is authenticated
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Reset to page 1 when search term or filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, activeFilter]);

  // Recipes are now filtered on the backend, so just use them directly
  const filteredRecipes = recipesData?.recipes || [];

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

  if (error) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Unable to load recipes
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          There was an error loading your recipes. Please try again.
        </p>
        <button
          onClick={() => refetch()}
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
            { key: 'collection', label: 'My Collection' },
            { key: 'discover', label: 'Discover' },
            { key: 'mine', label: 'My Uploads' }
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
      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
            <p style={{color: '#9b644b'}}>Loading your recipes...</p>
          </div>
        </div>
      )}

      {/* Recipe Grid */}
      {!isLoading && (
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
                    Start discovering recipes
                  </h3>
                  <p className="mb-6" style={{color: '#9b644b'}}>
                    Use the search bar above to find recipes from the community that you can add to your collection.
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
    </div>
  );
};

export { RecipesPage };