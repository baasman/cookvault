import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Input } from '../components/ui';
import { cookbooksApi } from '../services/cookbooksApi';
import { useAuth } from '../contexts/AuthContext';

const CreateCookbookPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const queryClient = useQueryClient();
  
  const isAdmin = user?.role === 'admin';

  const [formData, setFormData] = useState({
    title: '',
    author: '',
    description: '',
    isbn: '',
    publisher: '',
    publication_date: '',
    is_purchasable: false,
    price: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const createCookbookMutation = useMutation({
    mutationFn: cookbooksApi.createCookbook,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['cookbooks'] });
      navigate(`/cookbooks/${data.id}`);
    },
    onError: (error: any) => {
      const errorMessage = error?.message || 'Failed to create cookbook';
      setErrors({ general: errorMessage });
    },
  });

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Please Sign In
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          You need to be signed in to create cookbooks.
        </p>
        <Button onClick={() => navigate('/login')}>
          Sign In
        </Button>
      </div>
    );
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (formData.is_purchasable) {
      if (!isAdmin) {
        newErrors.general = 'Only administrators can create purchasable cookbooks';
        return false;
      }
      
      const price = parseFloat(formData.price);
      if (!formData.price || isNaN(price) || price <= 0) {
        newErrors.price = 'Valid price greater than $0 is required for purchasable cookbooks';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    const submitData = {
      title: formData.title.trim(),
      author: formData.author.trim() || undefined,
      description: formData.description.trim() || undefined,
      isbn: formData.isbn.trim() || undefined,
      publisher: formData.publisher.trim() || undefined,
      publication_date: formData.publication_date || undefined,
      is_purchasable: isAdmin ? formData.is_purchasable : false,
      price: isAdmin && formData.is_purchasable ? parseFloat(formData.price) : undefined,
    };

    createCookbookMutation.mutate(submitData);
  };

  const handleInputChange = (field: string, value: string | boolean) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear errors for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <button
          onClick={() => navigate('/cookbooks')}
          className="flex items-center space-x-2 text-text-secondary hover:text-accent transition-colors mb-4"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to Cookbooks</span>
        </button>
        
        <h1 className="text-3xl font-bold mb-2" style={{color: '#1c120d'}}>
          Create New Cookbook
        </h1>
        <p className="text-text-secondary">
          Create a new cookbook to organize your recipes.
        </p>
      </div>

      {errors.general && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {errors.general}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
          <h2 className="text-xl font-semibold mb-4" style={{color: '#1c120d'}}>
            Basic Information
          </h2>
          
          <div className="space-y-4">
            <div>
              <Input
                label="Title *"
                placeholder="Enter cookbook title"
                value={formData.title}
                onChange={(value) => handleInputChange('title', value)}
                error={errors.title}
                required
              />
            </div>

            <div>
              <Input
                label="Author"
                placeholder="Enter author name"
                value={formData.author}
                onChange={(value) => handleInputChange('author', value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Enter a description of this cookbook"
                rows={4}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
                style={{borderColor: '#e8d7cf'}}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="ISBN"
                placeholder="Enter ISBN"
                value={formData.isbn}
                onChange={(value) => handleInputChange('isbn', value)}
              />
              
              <Input
                label="Publisher"
                placeholder="Enter publisher"
                value={formData.publisher}
                onChange={(value) => handleInputChange('publisher', value)}
              />
            </div>

            <div>
              <Input
                label="Publication Date"
                type="date"
                value={formData.publication_date}
                onChange={(value) => handleInputChange('publication_date', value)}
              />
            </div>
          </div>
        </div>

        {/* Access & Pricing Settings */}
        <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
          <h2 className="text-xl font-semibold mb-4" style={{color: '#1c120d'}}>
            Access & Pricing
          </h2>
          
          {isAdmin ? (
            // Admin-only paywall settings
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  id="is_purchasable"
                  checked={formData.is_purchasable}
                  onChange={(e) => handleInputChange('is_purchasable', e.target.checked)}
                  className="mt-1"
                />
                <div>
                  <label htmlFor="is_purchasable" className="text-sm font-medium text-text-primary cursor-pointer">
                    Make this cookbook purchasable (Paywall)
                  </label>
                  <p className="text-xs text-text-secondary mt-1">
                    When enabled, users will need to purchase this cookbook to view full recipe ingredients and instructions
                  </p>
                </div>
              </div>

              {formData.is_purchasable && (
                <div className="ml-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="text-sm font-semibold text-blue-900 mb-3">
                    Paywall Configuration
                  </h3>
                  
                  <div className="space-y-3">
                    <div>
                      <Input
                        label="Price (USD) *"
                        type="number"
                        step="0.01"
                        min="0.01"
                        placeholder="9.99"
                        value={formData.price}
                        onChange={(value) => handleInputChange('price', value)}
                        error={errors.price}
                        required={formData.is_purchasable}
                      />
                      <p className="text-xs text-blue-600 mt-1">
                        Set a fair price for your cookbook content
                      </p>
                    </div>

                    <div className="text-sm text-blue-700 bg-blue-100 rounded p-3">
                      <p className="font-medium mb-2">What happens with paywall:</p>
                      <ul className="space-y-1 text-xs">
                        <li>• Users can see recipe titles and basic info</li>
                        <li>• Ingredients and instructions are hidden behind paywall</li>
                        <li>• Purchased recipes are automatically added to user's collection</li>
                        <li>• Revenue is tracked through Stripe</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            // Regular user - show contact information
            <div className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <svg className="h-12 w-12 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-blue-900 mb-2">
                    Interested in Selling Your Cookbook?
                  </h3>
                  <p className="text-blue-800 mb-4 leading-relaxed">
                    Want to monetize your recipes and create a premium cookbook experience? 
                    We offer cookbook paywall features for qualified creators who want to sell their content through Cookle.
                  </p>
                  
                  <div className="space-y-3">
                    <div className="flex items-center space-x-2 text-blue-700">
                      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M2.94 6.412A2 2 0 002 8.108V16a2 2 0 002 2h12a2 2 0 002-2V8.108a2 2 0 00-.94-1.696l-6-3.75a2 2 0 00-2.12 0l-6 3.75zm3.14 8.654l2.12-1.327a2 2 0 012.12 0l2.12 1.327A.7.7 0 0013 14.7V9a.7.7 0 00-.35-.606L10 6.882 7.35 8.394A.7.7 0 007 9v5.7a.7.7 0 00.08.366z" clipRule="evenodd" />
                      </svg>
                      <span className="font-medium">Contact us to get started:</span>
                    </div>
                    
                    <div className="bg-white rounded-lg p-4 border border-blue-300">
                      <a 
                        href="mailto:admin@cookle.food?subject=Interest in Cookbook Paywall Features"
                        className="flex items-center space-x-2 text-blue-600 hover:text-blue-800 font-medium"
                      >
                        <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                          <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                        </svg>
                        <span>admin@cookle.food</span>
                      </a>
                    </div>
                    
                    <div className="text-sm text-blue-600 bg-blue-100 rounded p-3">
                      <p className="font-medium mb-1">What to include in your email:</p>
                      <ul className="space-y-1 text-xs">
                        <li>• Brief description of your cookbook concept</li>
                        <li>• Your experience with cooking/recipe creation</li>
                        <li>• Expected number of recipes</li>
                        <li>• Target audience and pricing ideas</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Submit Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-end">
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate('/cookbooks')}
            disabled={createCookbookMutation.isPending}
          >
            Cancel
          </Button>
          
          <Button
            type="submit"
            disabled={createCookbookMutation.isPending}
            className="bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-400"
          >
            {createCookbookMutation.isPending ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Creating...
              </div>
            ) : (
              'Create Cookbook'
            )}
          </Button>
        </div>
      </form>

      {/* Help Section */}
      <div className="mt-8 p-6 bg-gray-50 rounded-xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          💡 Tips for Creating Cookbooks
        </h3>
        <div className="space-y-2 text-sm text-gray-700">
          <p><strong>Free Cookbooks:</strong> Perfect for sharing recipes with the community and building your reputation</p>
          <p><strong>Recipe Organization:</strong> Group related recipes together and use clear, descriptive titles</p>
          <p><strong>After Creation:</strong> You can upload recipe images and they'll be processed automatically using OCR</p>
          <p><strong>Quality Content:</strong> Well-tested recipes with clear instructions perform best with users</p>
          {isAdmin && (
            <>
              <p><strong>Paywall Cookbooks:</strong> Great for premium content, specialized techniques, or professional recipes</p>
              <p><strong>Pricing Strategy:</strong> Consider your content quality, uniqueness, and target audience when setting prices</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export { CreateCookbookPage };