import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { SearchBar } from '../components/ui';
import { SourceCard, SourceCardSkeleton } from '../components/source';
import { sourcesApi } from '../services/sourcesApi';
import { useAuth } from '../contexts/AuthContext';
import type { Source } from '../types';

const SourcesPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState<'recipe_count' | 'domain' | 'name' | 'created_at'>('recipe_count');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const sourcesPerPage = 12;

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  // Fetch sources using React Query
  const {
    data: sourcesData,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['sources', currentPage, searchTerm, sortBy, sortOrder],
    queryFn: () => sourcesApi.getSources({
      page: currentPage,
      per_page: sourcesPerPage,
      search: searchTerm,
      sort: sortBy,
      order: sortOrder,
    }),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: isAuthenticated,
  });

  // Reset to page 1 when search term or sort changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, sortBy, sortOrder]);

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleSortChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    if (value.includes('-')) {
      const [field, order] = value.split('-');
      setSortBy(field as typeof sortBy);
      setSortOrder(order as typeof sortOrder);
    } else {
      setSortBy(value as typeof sortBy);
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (!isAuthenticated) {
    return null;
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Unable to load sources
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          There was an error loading your sources. Please try again.
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
          Recipe Sources
        </h1>
        <p style={{color: '#9b644b'}}>
          Browse recipes by the websites they were imported from
        </p>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        <div className="flex-1">
          <SearchBar
            value={searchTerm}
            onChange={handleSearch}
            placeholder="Search sources by domain or name..."
            className="w-full"
          />
        </div>

        <div className="sm:w-56">
          <select
            value={`${sortBy}-${sortOrder}`}
            onChange={handleSortChange}
            className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
            style={{borderColor: '#e8d7cf'}}
          >
            <option value="recipe_count-desc">Most Recipes</option>
            <option value="recipe_count-asc">Fewest Recipes</option>
            <option value="domain-asc">Domain A-Z</option>
            <option value="domain-desc">Domain Z-A</option>
            <option value="created_at-desc">Recently Added</option>
            <option value="created_at-asc">Oldest First</option>
          </select>
        </div>
      </div>

      {/* Loading State - Show skeletons */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <SourceCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Sources Grid */}
      {!isLoading && (
        <>
          {sourcesData && sourcesData.sources.length > 0 ? (
            <>
              {/* Results count */}
              <div className="text-sm text-text-secondary mb-4">
                {searchTerm ? (
                  <p>
                    Found {sourcesData.sources.length} source{sourcesData.sources.length !== 1 ? 's' : ''}
                    {searchTerm && ` matching "${searchTerm}"`}
                  </p>
                ) : (
                  <p>
                    Showing {sourcesData.sources.length} of {sourcesData.pagination.total || 0} sources
                  </p>
                )}
              </div>

              {/* Sources Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {sourcesData.sources.map((source: Source) => (
                  <SourceCard
                    key={source.id}
                    source={source}
                  />
                ))}
              </div>

              {/* Pagination */}
              {sourcesData.pagination && sourcesData.pagination.pages > 1 && (
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
                      {Array.from({ length: Math.min(sourcesData.pagination.pages, 5) }, (_, i) => {
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
                      disabled={currentPage === sourcesData.pagination.pages}
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
                    d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
                  />
                </svg>
              </div>

              {searchTerm ? (
                <>
                  <h3 className="text-xl font-semibold mb-2" style={{color: '#1c120d'}}>
                    No sources found
                  </h3>
                  <p className="mb-4" style={{color: '#9b644b'}}>
                    No sources match your search for "{searchTerm}". Try different keywords or browse all sources.
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
                    No sources yet
                  </h3>
                  <p className="mb-6" style={{color: '#9b644b'}}>
                    Import recipes from websites to start building your sources collection!
                  </p>
                  <button
                    onClick={() => navigate('/upload?mode=url')}
                    className="inline-block px-6 py-3 bg-accent text-white rounded-lg hover:opacity-90 transition-opacity font-medium"
                  >
                    Import from URL
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

export { SourcesPage };
