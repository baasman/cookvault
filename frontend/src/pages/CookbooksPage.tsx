import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { SearchBar } from '../components/ui';
import { CookbookCard } from '../components/cookbook';
import { cookbooksApi } from '../services/cookbooksApi';
import { useAuth } from '../contexts/AuthContext';
import type { Cookbook } from '../types';

const CookbooksPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState<'title' | 'author' | 'created_at' | 'recipe_count'>('title');
  const cookbooksPerPage = 12;

  // Fetch cookbooks using React Query
  const { 
    data: cookbooksData, 
    isLoading, 
    error, 
    refetch 
  } = useQuery({
    queryKey: ['cookbooks', currentPage, searchTerm, sortBy],
    queryFn: () => cookbooksApi.fetchCookbooks({ 
      page: currentPage, 
      per_page: cookbooksPerPage,
      search: searchTerm,
      sort_by: sortBy
    }),
    enabled: isAuthenticated, // Only fetch if user is authenticated
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Reset to page 1 when search term or sort changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, sortBy]);

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleSortChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSortBy(event.target.value as typeof sortBy);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Please log in to view your cookbooks
        </h2>
        <p style={{color: '#9b644b'}}>
          Sign in to access your cookbook collection.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Unable to load cookbooks
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          There was an error loading your cookbooks. Please try again.
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
          Cookbooks
        </h1>
        <p style={{color: '#9b644b'}}>
          Discover and browse cookbook collections from the community
        </p>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        <div className="flex-1">
          <SearchBar
            value={searchTerm}
            onChange={handleSearch}
            placeholder="Search cookbooks by title, author, or description..."
            className="w-full"
          />
        </div>
        
        <div className="sm:w-48">
          <select
            value={sortBy}
            onChange={handleSortChange}
            className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
            style={{borderColor: '#e8d7cf'}}
          >
            <option value="title">Sort by Title</option>
            <option value="author">Sort by Author</option>
            <option value="recipe_count">Sort by Recipe Count</option>
            <option value="created_at">Sort by Date Added</option>
          </select>
        </div>
      </div>

      {/* Add Cookbook Button */}
      <div className="flex justify-end mb-6">
        <button
          className="px-4 py-2 bg-accent text-white rounded-lg hover:opacity-90 transition-opacity font-medium"
          onClick={() => {
            // TODO: Open create cookbook modal
            console.log('Create cookbook modal would open here');
          }}
        >
          + Add Cookbook
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
            <p style={{color: '#9b644b'}}>Loading your cookbooks...</p>
          </div>
        </div>
      )}

      {/* Cookbook Grid */}
      {!isLoading && (
        <>
          {cookbooksData && cookbooksData.cookbooks.length > 0 ? (
            <>
              {/* Results count */}
              <div className="text-sm text-text-secondary mb-4">
                {searchTerm ? (
                  <p>
                    Found {cookbooksData.cookbooks.length} cookbook{cookbooksData.cookbooks.length !== 1 ? 's' : ''} 
                    {searchTerm && ` matching "${searchTerm}"`}
                  </p>
                ) : (
                  <p>
                    Showing {cookbooksData.cookbooks.length} of {cookbooksData.total || 0} cookbooks
                  </p>
                )}
              </div>

              {/* Cookbook Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {cookbooksData.cookbooks.map((cookbook: Cookbook) => (
                  <CookbookCard
                    key={cookbook.id}
                    cookbook={cookbook}
                  />
                ))}
              </div>

              {/* Pagination */}
              {cookbooksData && cookbooksData.pages > 1 && (
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
                      {Array.from({ length: Math.min(cookbooksData.pages, 5) }, (_, i) => {
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
                      disabled={currentPage === cookbooksData.pages}
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
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" 
                  />
                </svg>
              </div>
              
              {searchTerm ? (
                <>
                  <h3 className="text-xl font-semibold mb-2" style={{color: '#1c120d'}}>
                    No cookbooks found
                  </h3>
                  <p className="mb-4" style={{color: '#9b644b'}}>
                    No cookbooks match your search for "{searchTerm}". Try different keywords or browse all cookbooks.
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
                    No cookbooks yet
                  </h3>
                  <p className="mb-6" style={{color: '#9b644b'}}>
                    Start organizing your recipes by creating your first cookbook!
                  </p>
                  <button
                    onClick={() => {
                      // TODO: Open create cookbook modal
                      console.log('Create cookbook modal would open here');
                    }}
                    className="inline-block px-6 py-3 bg-accent text-white rounded-lg hover:opacity-90 transition-opacity font-medium"
                  >
                    Create Your First Cookbook
                  </button>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export { CookbooksPage };