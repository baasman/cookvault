import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sourcesApi } from '../services/sourcesApi';
import { useAuth } from '../contexts/AuthContext';
import { Button, SearchBar } from '../components/ui';
import { RecipeCard } from '../components/recipe/RecipeCard';
import type { Recipe } from '../types';
import toast from 'react-hot-toast';

const SourceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const sourceId = id ? parseInt(id, 10) : null;

  // Local state
  const [isEditingName, setIsEditingName] = useState(false);
  const [editName, setEditName] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Reset to page 1 when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  // Fetch source details with recipes
  const {
    data: sourceData,
    isLoading,
    error
  } = useQuery({
    queryKey: ['source', sourceId, currentPage, searchTerm],
    queryFn: () => sourceId ? sourcesApi.getSource(sourceId, {
      page: currentPage,
      per_page: 12,
      search: searchTerm
    }) : Promise.reject('No source ID'),
    enabled: isAuthenticated && !!sourceId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const source = sourceData?.source;
  const recipes = sourceData?.recipes || [];
  const pagination = sourceData?.pagination;

  // Initialize edit name when source data loads
  useEffect(() => {
    if (source && !isEditingName) {
      setEditName(source.name || '');
    }
  }, [source, isEditingName]);

  // Update source name mutation
  const updateNameMutation = useMutation({
    mutationFn: (name: string | null) =>
      sourcesApi.updateSource(sourceId!, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['source', sourceId] });
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      setIsEditingName(false);
      toast.success('Source name updated');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update source name');
    },
  });

  const handleSaveName = () => {
    const trimmedName = editName.trim();
    updateNameMutation.mutate(trimmedName || null);
  };

  const handleCancelEdit = () => {
    setEditName(source?.name || '');
    setIsEditingName(false);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Redirect if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Please log in to view this source
        </h2>
        <Button onClick={() => navigate('/login')}>
          Sign In
        </Button>
      </div>
    );
  }

  if (!sourceId) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Invalid source
        </h2>
        <Button onClick={() => navigate('/sources')}>
          Back to All Sources
        </Button>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
          <p style={{color: '#9b644b'}}>Loading source...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !source) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Source Not Found
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          The source you're looking for doesn't exist or you don't have permission to view it.
        </p>
        <Button onClick={() => navigate('/sources')}>
          Back to All Sources
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Back Navigation */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/sources')}
          className="flex items-center space-x-2 text-text-secondary hover:text-accent transition-colors"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to All Sources</span>
        </button>
      </div>

      {/* Source Header */}
      <div className="bg-white rounded-xl shadow-sm border p-8 mb-6" style={{borderColor: '#e8d7cf'}}>
        <div className="flex flex-col md:flex-row md:items-start gap-6">
          {/* Favicon */}
          <div className="flex-shrink-0">
            {source.favicon_url ? (
              <img
                src={source.favicon_url}
                alt={source.display_name}
                className="w-16 h-16 rounded-lg"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  const sibling = target.nextElementSibling;
                  if (sibling) {
                    sibling.classList.remove('hidden');
                  }
                }}
              />
            ) : null}
            <div className={`w-16 h-16 rounded-lg bg-primary-100 flex items-center justify-center ${source.favicon_url ? 'hidden' : ''}`}>
              <svg className="h-8 w-8 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
            </div>
          </div>

          {/* Source Info */}
          <div className="flex-1">
            {isEditingName ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
                    placeholder={`Enter a custom name for ${source.domain}...`}
                    maxLength={200}
                  />
                  <p className="text-xs text-text-secondary mt-1">
                    Leave empty to use the domain name: {source.domain}
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <Button
                    onClick={handleCancelEdit}
                    variant="secondary"
                    size="sm"
                    disabled={updateNameMutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSaveName}
                    size="sm"
                    disabled={updateNameMutation.isPending}
                  >
                    {updateNameMutation.isPending ? 'Saving...' : 'Save'}
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-3xl font-bold" style={{color: '#1c120d'}}>
                    {source.display_name}
                  </h1>
                  <button
                    onClick={() => setIsEditingName(true)}
                    className="p-1 text-text-secondary hover:text-accent transition-colors"
                    title="Edit display name"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                </div>

                {source.name && source.name !== source.domain && (
                  <p className="text-text-secondary mb-4">
                    {source.domain}
                  </p>
                )}

                {/* Source Metadata */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-6">
                  <div className="text-center p-3 bg-background-secondary rounded-lg">
                    <div className="text-sm text-text-secondary mb-1">Total Recipes</div>
                    <div className="text-2xl font-bold text-accent">{source.recipe_count}</div>
                  </div>

                  <div className="text-center p-3 bg-background-secondary rounded-lg">
                    <div className="text-sm text-text-secondary mb-1">First Import</div>
                    <div className="font-medium text-text-primary">
                      {new Date(source.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="text-center p-3 bg-background-secondary rounded-lg">
                    <div className="text-sm text-text-secondary mb-1">Last Updated</div>
                    <div className="font-medium text-text-primary">
                      {new Date(source.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>

                {/* Visit website link */}
                <div className="mt-4">
                  <a
                    href={`https://${source.domain}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-sm text-accent hover:underline"
                  >
                    Visit {source.domain}
                    <svg className="ml-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Search Bar */}
      {!isEditingName && (
        <div className="flex justify-center mb-8">
          <SearchBar
            value={searchTerm}
            onChange={setSearchTerm}
            placeholder="Search recipes from this source..."
            className="w-full max-w-2xl"
          />
        </div>
      )}

      {/* Recipes Section */}
      {!isEditingName && (
        <>
          {recipes.length > 0 ? (
            <>
              {/* Results count */}
              <div className="text-sm text-text-secondary mb-4">
                {searchTerm ? (
                  <p>
                    Found {recipes.length} recipe{recipes.length !== 1 ? 's' : ''}
                    {searchTerm && ` matching "${searchTerm}"`}
                  </p>
                ) : (
                  <p>
                    Showing {recipes.length} of {pagination?.total || 0} recipes
                  </p>
                )}
              </div>

              {/* Recipe Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
                {recipes.map((recipe: Recipe) => (
                  <RecipeCard
                    key={recipe.id}
                    recipe={recipe}
                    showPrivacyControls={true}
                  />
                ))}
              </div>

              {/* Pagination */}
              {pagination && pagination.pages > 1 && (
                <div className="flex justify-center">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={!pagination.has_prev}
                      className="px-3 py-2 text-sm text-text-secondary hover:text-accent disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>

                    {Array.from({ length: Math.min(pagination.pages, 5) }, (_, i) => i + 1).map((page) => (
                      <button
                        key={page}
                        onClick={() => handlePageChange(page)}
                        className={`px-3 py-2 text-sm rounded-md transition-colors ${
                          page === currentPage
                            ? 'bg-accent text-white'
                            : 'text-text-secondary hover:text-accent hover:bg-background-secondary'
                        }`}
                      >
                        {page}
                      </button>
                    ))}

                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={!pagination.has_next}
                      className="px-3 py-2 text-sm text-text-secondary hover:text-accent disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            /* Empty State */
            <div className="text-center py-12">
              <div className="max-w-md mx-auto">
                <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-text-primary mb-2">
                  {searchTerm ? 'No recipes found' : 'No recipes from this source'}
                </h3>
                <p className="text-text-secondary mb-4">
                  {searchTerm
                    ? `No recipes match "${searchTerm}". Try a different search term.`
                    : `Import more recipes from ${source.domain} to see them here.`
                  }
                </p>
                {!searchTerm && (
                  <Button onClick={() => navigate('/upload?mode=url')} variant="primary">
                    Import from URL
                  </Button>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export { SourceDetailPage };
