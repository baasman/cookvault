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
    is_purchasable: false,
    price: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const createCookbookMutation = useMutation({
    mutationFn: (data: any) => cookbooksApi.createCookbook(data),
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

      {/* User Profile Section - Shows cookbook ownership */}
      <div className="mb-6 bg-white rounded-xl shadow-sm border p-4" style={{borderColor: '#e8d7cf'}}>
        <div className="flex items-center space-x-3">
          {/* User Avatar */}
          <div className="w-12 h-12 rounded-full flex-shrink-0 overflow-hidden" style={{backgroundColor: '#f1ece9'}}>
            <div className="w-full h-full flex items-center justify-center">
              <svg className="w-6 h-6" style={{color: '#f15f1c'}} fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
              </svg>
            </div>
          </div>

          {/* User Info */}
          <div className="flex-grow">
            <div className="flex items-center space-x-2">
              <p className="text-sm font-medium" style={{color: '#9b644b'}}>
                Created by
              </p>
              <span className="px-2 py-0.5 text-xs font-medium rounded-full" style={{backgroundColor: '#f1ece9', color: '#f15f1c'}}>
                Owner
              </span>
            </div>
            <p className="text-base font-semibold" style={{color: '#1c120d'}}>
              {user?.name || 'Unknown User'}
            </p>
          </div>
        </div>
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
                label="Title"
                placeholder="Enter cookbook title"
                value={formData.title}
                onChange={(value) => handleInputChange('title', value)}
                error={errors.title}
              />
            </div>

            <div>
              <Input
                label="Author Display Name (optional)"
                placeholder={user?.name || "Enter author name"}
                value={formData.author}
                onChange={(value) => handleInputChange('author', value)}
              />
              <p className="text-xs mt-1" style={{color: '#9b644b'}}>
                Leave empty to use your username, or enter a custom author name for display
              </p>
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

          </div>
        </div>

        {/* Access & Pricing Settings - Coming Soon */}
        <div className="bg-white rounded-xl shadow-sm border p-6" style={{borderColor: '#e8d7cf'}}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold" style={{color: '#1c120d'}}>
              Access & Pricing
            </h2>
            <span className="px-3 py-1 text-xs font-medium bg-amber-100 text-amber-800 rounded-full">
              Coming Soon
            </span>
          </div>

          <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 mt-0.5">
                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-gray-600">
                  We're working on features that will let you sell access to your cookbooks and monetize your recipes. Stay tuned!
                </p>
              </div>
            </div>
          </div>
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