import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getApiUrl } from '../../utils/getApiUrl';
import type { Recipe } from '../../types';

interface FeaturedRecipesResponse {
  recipes: Recipe[];
}

const fetchFeaturedRecipes = async (): Promise<FeaturedRecipesResponse> => {
  const baseUrl = getApiUrl();
  const response = await fetch(`${baseUrl}/public/recipes/featured`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch featured recipes');
  }

  return await response.json();
};

export const FeaturedRecipes: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['featured-recipes'],
    queryFn: fetchFeaturedRecipes,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <section className="py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center mb-8" style={{color: '#1c120d'}}>
            Featured Recipes
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-xl shadow-sm border animate-pulse" style={{borderColor: '#e8d7cf'}}>
                <div className="w-full h-48 bg-gray-300 rounded-t-xl"></div>
                <div className="p-6">
                  <div className="h-6 bg-gray-300 rounded mb-2"></div>
                  <div className="h-4 bg-gray-200 rounded mb-4"></div>
                  <div className="flex justify-between items-center">
                    <div className="h-4 bg-gray-200 rounded w-20"></div>
                    <div className="h-4 bg-gray-200 rounded w-16"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    console.error('Featured recipes error:', error);
    return (
      <section className="py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-red-600">Failed to load featured recipes: {error.message}</p>
        </div>
      </section>
    );
  }

  if (!data?.recipes || data.recipes.length === 0) {
    return null; // Don't show section if no featured recipes
  }

  return (
    <section className="py-12 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold mb-4" style={{color: '#1c120d'}}>
            Featured Recipes
          </h2>
          <p className="text-lg" style={{color: '#9b644b'}}>
            Handpicked recipes from our community
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {data.recipes.map((recipe) => (
            <Link
              key={recipe.id}
              to={`/recipes/${recipe.id}`}
              className="bg-white rounded-xl shadow-sm border hover:shadow-md transition-shadow group"
              style={{borderColor: '#e8d7cf'}}
            >
              {/* Recipe Image */}
              <div className="relative w-full h-48 bg-gray-100 rounded-t-xl overflow-hidden">
                {recipe.images && recipe.images.length > 0 ? (
                  <img
                    src={recipe.images[0].cloudinary_thumbnail_url || recipe.images[0].display_url}
                    alt={recipe.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-orange-100 to-red-100">
                    <svg className="w-12 h-12 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                )}
                
                {/* Featured badge */}
                <div className="absolute top-3 right-3 bg-yellow-400 text-yellow-900 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                  <span>⭐</span>
                  <span>Featured</span>
                </div>
              </div>

              {/* Recipe Info */}
              <div className="p-6">
                <h3 className="text-xl font-semibold mb-2 line-clamp-2 group-hover:text-orange-600 transition-colors" style={{color: '#1c120d'}}>
                  {recipe.title}
                </h3>
                
                {recipe.description && (
                  <p className="text-sm mb-4 line-clamp-2" style={{color: '#9b644b'}}>
                    {recipe.description}
                  </p>
                )}

                <div className="flex justify-between items-center">
                  <div className="flex items-center space-x-4 text-sm" style={{color: '#9b644b'}}>
                    {recipe.cook_time && (
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        {recipe.cook_time < 60 ? `${recipe.cook_time}m` : `${Math.floor(recipe.cook_time / 60)}h${recipe.cook_time % 60 ? ` ${recipe.cook_time % 60}m` : ''}`}
                      </span>
                    )}
                    
                    {recipe.servings && (
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                        {recipe.servings} servings
                      </span>
                    )}
                  </div>

                  {recipe.user && (
                    <span className="text-xs px-2 py-1 bg-gray-100 rounded" style={{color: '#9b644b'}}>
                      by {recipe.user.first_name || recipe.user.username}
                    </span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Browse all recipes link */}
        <div className="text-center mt-8">
          <Link
            to="/recipes"
            className="inline-flex items-center px-6 py-3 rounded-lg font-medium transition-colors"
            style={{
              backgroundColor: '#f15f1c',
              color: 'white'
            }}
          >
            Browse All Recipes
            <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </Link>
        </div>
      </div>
    </section>
  );
};