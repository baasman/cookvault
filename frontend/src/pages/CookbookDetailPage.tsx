import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { cookbooksApi } from '../services/cookbooksApi';
import { useAuth } from '../contexts/AuthContext';
import { Button, SearchBar, AuthenticatedImage } from '../components/ui';
import { CookbookImageDisplay } from '../components/cookbook/CookbookImageDisplay';
import { formatTextForDisplay, decodeHtmlEntities } from '../utils/textUtils';
import type { Recipe } from '../types';

const CookbookDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const cookbookId = id ? parseInt(id, 10) : null;
  const [searchTerm, setSearchTerm] = useState('');

  const { 
    data: cookbook, 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['cookbook', cookbookId, searchTerm, isAuthenticated],
    queryFn: async () => {
      if (!cookbookId) throw new Error('No cookbook ID');
      
      if (isAuthenticated) {
        // Authenticated users can see all cookbooks they have access to
        return cookbooksApi.fetchCookbook(cookbookId, searchTerm);
      } else {
        // Unauthenticated users can only see public cookbook with public recipes
        const cookbookData = await cookbooksApi.fetchPublicCookbook(cookbookId);
        const recipesData = await cookbooksApi.fetchPublicCookbookRecipes(cookbookId, { search: searchTerm });
        return {
          ...cookbookData,
          recipes: recipesData.recipes
        };
      }
    },
    enabled: !!cookbookId,
  });

  const formatTime = (minutes: number | undefined) => {
    if (!minutes) return 'Not specified';
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.getFullYear().toString();
    } catch {
      return '';
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };


  // Cookbooks are now publicly viewable for unauthenticated users (showing only public recipes)

  if (!cookbookId) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Invalid cookbook
        </h2>
        <Button onClick={() => navigate('/cookbooks')}>
          Back to Cookbooks
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
          <p style={{color: '#9b644b'}}>Loading cookbook...</p>
        </div>
      </div>
    );
  }

  if (error || !cookbook) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Cookbook not found
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          {isAuthenticated 
            ? "The cookbook you're looking for doesn't exist or you don't have permission to view it."
            : "This cookbook doesn't exist or has no public recipes available."
          }
        </p>
        <Button onClick={() => navigate('/cookbooks')}>
          Back to Cookbooks
        </Button>
      </div>
    );
  }

  const recipes = (cookbook as any).recipes as Recipe[] || [];

  return (
    <div className="max-w-6xl mx-auto">
      {/* Back Navigation */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/cookbooks')}
          className="flex items-center space-x-2 text-text-secondary hover:text-accent transition-colors"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to Cookbooks</span>
        </button>
      </div>

      {/* Cookbook Header */}
      <div className="bg-white rounded-xl shadow-sm border p-8 mb-8" style={{borderColor: '#e8d7cf'}}>
        <div className="flex flex-col lg:flex-row lg:items-start lg:space-x-8">
          {/* Cookbook Cover */}
          <div className="w-full lg:w-1/4 mb-6 lg:mb-0">
            <CookbookImageDisplay 
              cookbook={cookbook} 
              canEdit={!!(user?.role === 'admin' || (user && cookbook.user_id === parseInt(user.id)))}
            />
          </div>

          {/* Cookbook Info */}
          <div className="flex-1">
            <h1 className="text-4xl font-bold mb-4" style={{color: '#1c120d'}}>
              {cookbook.title}
            </h1>

            {cookbook.author && (
              <p className="text-xl text-text-secondary mb-4">
                by {cookbook.author}
              </p>
            )}

            {cookbook.description && (
              <div className="text-sm text-text-secondary mb-6 description-text preserve-newlines">
                {formatTextForDisplay(cookbook.description)}
              </div>
            )}

            {/* Cookbook Metadata */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="p-4 bg-background-secondary rounded-lg">
                <div className="text-sm text-text-secondary mb-1">Recipes</div>
                <div className="text-2xl font-bold text-accent">{recipes.length}</div>
              </div>

              {cookbook.publisher && (
                <div className="p-4 bg-background-secondary rounded-lg">
                  <div className="text-sm text-text-secondary mb-1">Publisher</div>
                  <div className="font-medium text-text-primary">{cookbook.publisher}</div>
                </div>
              )}

              {cookbook.publication_date && (
                <div className="p-4 bg-background-secondary rounded-lg">
                  <div className="text-sm text-text-secondary mb-1">Published</div>
                  <div className="font-medium text-text-primary">{formatDate(cookbook.publication_date)}</div>
                </div>
              )}

              {cookbook.isbn && (
                <div className="p-4 bg-background-secondary rounded-lg">
                  <div className="text-sm text-text-secondary mb-1">ISBN</div>
                  <div className="font-medium text-text-primary">{cookbook.isbn}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Login prompt for unauthenticated users */}
      {!isAuthenticated && (
        <div className="mb-8 bg-blue-50 border border-blue-200 rounded-xl p-6 text-center">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            Enjoying this cookbook?
          </h3>
          <p className="text-blue-700 mb-4">
            Create an account to save recipes to your collection, add personal notes, and access your own recipe management tools!
          </p>
          <div className="flex justify-center gap-3">
            <Button 
              onClick={() => navigate('/register')}
              className="bg-blue-700 text-white hover:bg-blue-800 border-blue-700"
            >
              Create Free Account
            </Button>
            <Button 
              variant="secondary" 
              onClick={() => navigate('/login')}
              className="bg-white text-blue-700 border-white hover:bg-blue-50"
            >
              Sign In
            </Button>
          </div>
        </div>
      )}

      {/* Recipes Section */}
      <div className="bg-white rounded-xl shadow-sm border p-8" style={{borderColor: '#e8d7cf'}}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold" style={{color: '#1c120d'}}>
            Recipes ({recipes.length})
            {!isAuthenticated && recipes.length > 0 && (
              <span className="text-sm font-normal text-blue-600 ml-2">
                (showing public recipes only)
              </span>
            )}
          </h2>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <SearchBar
            value={searchTerm}
            onChange={handleSearch}
            placeholder="Search recipes in this cookbook..."
            className="w-full max-w-md"
          />
          {searchTerm && (
            <p className="text-sm text-text-secondary mt-2">
              {recipes.length === 0 
                ? `No recipes found matching "${searchTerm}"`
                : recipes.length === 1
                ? `1 recipe found matching "${searchTerm}"`
                : `${recipes.length} recipes found matching "${searchTerm}"`
              }
            </p>
          )}
        </div>

        {recipes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recipes
              .sort((a, b) => {
                // Sort by page number (nulls last), then by title
                if (a.page_number === null && b.page_number === null) return a.title.localeCompare(b.title);
                if (a.page_number === null) return 1;
                if (b.page_number === null) return -1;
                return (a.page_number || 0) - (b.page_number || 0);
              })
              .map((recipe) => (
                <Link key={recipe.id} to={`/recipes/${recipe.id}`}>
                  <div className="group bg-white rounded-lg border shadow-sm transition-all duration-200 hover:shadow-md hover:border-accent/20 overflow-hidden" style={{borderColor: '#e8d7cf'}}>
                    {/* Recipe Image */}
                    <div className="aspect-[4/3] bg-gradient-to-br from-background-secondary to-primary-200 relative overflow-hidden">
                      <AuthenticatedImage
                        filename={recipe.images && recipe.images.length > 0 ? recipe.images[0].filename : null}
                        alt={recipe.title}
                        className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
                        fallback={
                          <div className="w-full h-full flex items-center justify-center">
                            <svg className="h-12 w-12 text-primary-300" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                            </svg>
                          </div>
                        }
                      />
                      
                      {/* Page Number Badge */}
                      {recipe.page_number && (
                        <div className="absolute top-3 left-3">
                          <span className="px-2 py-1 text-xs font-medium text-white rounded-full bg-accent">
                            Page {recipe.page_number}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Recipe Info */}
                    <div className="p-4">
                      <h3 className="text-lg font-semibold text-text-primary group-hover:text-accent transition-colors line-clamp-2 mb-2">
                        {recipe.title}
                      </h3>

                      {recipe.description && (
                        <p className="text-xs text-text-secondary line-clamp-4 mb-3 description-text-compact">
                          {decodeHtmlEntities(recipe.description)}
                        </p>
                      )}

                      {/* Recipe Metadata */}
                      <div className="flex items-center justify-between text-xs text-text-secondary">
                        <div className="flex items-center space-x-3">
                          {recipe.prep_time && (
                            <div className="flex items-center">
                              <svg className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              <span>{formatTime(recipe.prep_time)}</span>
                            </div>
                          )}
                          
                          {recipe.cook_time && (
                            <div className="flex items-center">
                              <svg className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
                              </svg>
                              <span>{formatTime(recipe.cook_time)}</span>
                            </div>
                          )}
                        </div>

                        {recipe.difficulty && (
                          <span className="text-text-secondary">
                            {recipe.difficulty.charAt(0).toUpperCase() + recipe.difficulty.slice(1)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <svg className="h-16 w-16 mx-auto text-text-secondary mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H7m5 0v-9a2 2 0 00-2-2H7a2 2 0 00-2 2v9m14 0h2" />
            </svg>
            <h3 className="text-lg font-medium text-text-primary mb-2">
              {searchTerm ? 'No matching recipes found' : 'No recipes available'}
            </h3>
            <p className="text-text-secondary mb-4">
              {searchTerm 
                ? `No recipes match "${searchTerm}" in this cookbook.`
                : isAuthenticated 
                ? "This cookbook doesn't have any recipes yet."
                : "This cookbook has no public recipes available."
              }
            </p>
            {searchTerm ? (
              <Button onClick={() => setSearchTerm('')}>
                Clear Search
              </Button>
            ) : isAuthenticated ? (
              <Button onClick={() => navigate('/upload')}>
                Import Recipes
              </Button>
            ) : (
              <div className="flex justify-center gap-3">
                <Button 
                  onClick={() => navigate('/register')}
                  className="bg-blue-700 text-white hover:bg-blue-800 border-blue-700"
                >
                  Create Free Account
                </Button>
                <Button 
                  variant="secondary" 
                  onClick={() => navigate('/login')}
                  className="bg-white text-blue-700 border-white hover:bg-blue-50"
                >
                  Sign In
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export { CookbookDetailPage };