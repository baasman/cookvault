import React from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { cookbooksApi } from '../services/cookbooksApi';
import { recipesApi } from '../services/recipesApi';
import { Button } from '../components/ui';
import { useAuth } from '../contexts/AuthContext';

const CookbookPurchaseSuccessPage: React.FC = () => {
  const { cookbookId } = useParams<{ cookbookId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const { data: cookbook, isLoading: cookbookLoading } = useQuery({
    queryKey: ['cookbook', cookbookId],
    queryFn: () => cookbookId ? cookbooksApi.fetchCookbook(parseInt(cookbookId)) : Promise.reject('No cookbook ID'),
    enabled: !!cookbookId && isAuthenticated,
  });

  const { data: recipesData, isLoading: recipesLoading } = useQuery({
    queryKey: ['cookbook-recipes', cookbookId],
    queryFn: () => cookbookId ? recipesApi.fetchRecipesByCookbook(parseInt(cookbookId)) : Promise.reject('No cookbook ID'),
    enabled: !!cookbookId && !!cookbook && isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Access Denied
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          Please log in to view your purchase confirmation.
        </p>
        <Button onClick={() => navigate('/login')}>
          Sign In
        </Button>
      </div>
    );
  }

  if (!cookbookId || isNaN(parseInt(cookbookId))) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Invalid Purchase
        </h2>
        <Button onClick={() => navigate('/cookbooks')}>
          Browse Cookbooks
        </Button>
      </div>
    );
  }

  if (cookbookLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
          <p style={{color: '#9b644b'}}>Loading your purchase details...</p>
        </div>
      </div>
    );
  }

  if (!cookbook) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Cookbook Not Found
        </h2>
        <Button onClick={() => navigate('/cookbooks')}>
          Browse Cookbooks
        </Button>
      </div>
    );
  }

  const recipes = recipesData?.recipes || [];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Success Header */}
      <div className="text-center mb-8">
        <div className="mb-6">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-green-800 mb-2">
            Purchase Successful!
          </h1>
          <p className="text-lg text-gray-600">
            You now have full access to "{cookbook.title}"
          </p>
        </div>
      </div>

      {/* Cookbook Details */}
      <div className="bg-white rounded-xl shadow-sm border p-8 mb-8" style={{borderColor: '#e8d7cf'}}>
        <div className="flex flex-col md:flex-row md:items-start md:space-x-6">
          {cookbook.cover_image_url && (
            <div className="w-full md:w-48 mb-6 md:mb-0 flex-shrink-0">
              <img
                src={cookbook.cover_image_url}
                alt={cookbook.title}
                className="w-full h-64 md:h-72 object-cover rounded-lg shadow-md"
              />
            </div>
          )}
          
          <div className="flex-1">
            <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
              {cookbook.title}
            </h2>
            
            {cookbook.author && (
              <p className="text-lg text-gray-600 mb-2">
                by {cookbook.author}
              </p>
            )}
            
            {cookbook.description && (
              <p className="text-gray-700 mb-4 leading-relaxed">
                {cookbook.description}
              </p>
            )}
            
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
              <h3 className="font-semibold text-green-800 mb-2">
                What you now have access to:
              </h3>
              <ul className="text-green-700 space-y-1">
                <li className="flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Full ingredient lists for all {cookbook.recipe_count} recipes
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Complete step-by-step instructions
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Recipes automatically added to your collection
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Permanent access - no expiration
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Recipe Preview */}
      {!recipesLoading && recipes.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-8 mb-8" style={{borderColor: '#e8d7cf'}}>
          <h3 className="text-xl font-bold mb-6" style={{color: '#1c120d'}}>
            Featured Recipes ({recipes.length} total)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recipes.slice(0, 6).map((recipe) => (
              <Link
                key={recipe.id}
                to={`/recipes/${recipe.id}`}
                className="block p-4 border rounded-lg hover:shadow-md transition-shadow"
                style={{borderColor: '#e8d7cf'}}
              >
                <h4 className="font-medium text-gray-900 mb-2 line-clamp-2">
                  {recipe.title}
                </h4>
                {recipe.description && (
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {recipe.description}
                  </p>
                )}
                <div className="flex items-center mt-2 text-xs text-gray-500">
                  {recipe.prep_time && (
                    <span className="mr-3">
                      Prep: {recipe.prep_time}min
                    </span>
                  )}
                  {recipe.difficulty && (
                    <span className="capitalize">
                      {recipe.difficulty}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
          {recipes.length > 6 && (
            <div className="text-center mt-6">
              <Link
                to={`/cookbooks/${cookbook.id}`}
                className="inline-flex items-center text-accent hover:text-accent/80 font-medium"
              >
                View all {recipes.length} recipes →
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <Button
          onClick={() => navigate(`/cookbooks/${cookbook.id}`)}
          className="bg-accent text-white hover:opacity-90"
        >
          Explore Cookbook
        </Button>
        <Button
          variant="secondary"
          onClick={() => navigate('/my-collection')}
        >
          View My Collection
        </Button>
        <Button
          variant="secondary"
          onClick={() => navigate('/cookbooks')}
        >
          Browse More Cookbooks
        </Button>
      </div>

      {/* Receipt Info */}
      <div className="mt-8 text-center">
        <p className="text-sm text-gray-500 mb-2">
          A receipt has been sent to your email address.
        </p>
        <p className="text-xs text-gray-400">
          Purchase completed on {new Date().toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </p>
      </div>
    </div>
  );
};

export { CookbookPurchaseSuccessPage };