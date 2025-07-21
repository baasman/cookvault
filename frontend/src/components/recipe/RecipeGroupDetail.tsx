import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recipeGroupsApi } from '../../services/recipeGroupsApi';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../ui';
import { SearchBar } from '../ui';
import { RecipeCard } from './RecipeCard';
import type { Recipe } from '../../types';
import toast from 'react-hot-toast';

interface RecipeGroupDetailProps {
  groupId?: number; // Optional prop for direct usage, otherwise uses URL param
}

const RecipeGroupDetail: React.FC<RecipeGroupDetailProps> = ({ groupId: propGroupId }) => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const queryClient = useQueryClient();
  
  // Get group ID from props or URL param
  const groupId = propGroupId || (id ? parseInt(id, 10) : null);
  
  // Local state
  const [isEditing, setIsEditing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [editFormData, setEditFormData] = useState({
    name: '',
    description: ''
  });

  // Reset to page 1 when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  // Fetch group details with recipes
  const { 
    data: groupData, 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['recipe-group', groupId, currentPage, searchTerm],
    queryFn: () => groupId ? recipeGroupsApi.getRecipeGroup(groupId, { 
      page: currentPage, 
      per_page: 12,
      search: searchTerm 
    }) : Promise.reject('No group ID'),
    enabled: isAuthenticated && !!groupId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const group = groupData?.group;
  const recipes = groupData?.recipes || [];
  const pagination = groupData?.pagination;

  // Initialize edit form when group data loads
  useEffect(() => {
    if (group && !isEditing) {
      setEditFormData({
        name: group.name,
        description: group.description || ''
      });
    }
  }, [group, isEditing]);

  // Update group mutation
  const updateGroupMutation = useMutation({
    mutationFn: ({ name, description }: { name: string; description: string }) => 
      recipeGroupsApi.updateRecipeGroup(groupId!, { name, description }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe-group', groupId] });
      queryClient.invalidateQueries({ queryKey: ['recipe-groups', user?.id] });
      setIsEditing(false);
      toast.success('Group updated successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update group');
    },
  });

  // Delete group mutation
  const deleteGroupMutation = useMutation({
    mutationFn: () => recipeGroupsApi.deleteRecipeGroup(groupId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe-groups', user?.id] });
      toast.success('Group deleted successfully');
      navigate('/recipes?filter=groups');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete group');
    },
  });

  // Remove recipe from group mutation
  const removeRecipeMutation = useMutation({
    mutationFn: (recipeId: number) => recipeGroupsApi.removeRecipeFromGroup(groupId!, recipeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe-group', groupId] });
      queryClient.invalidateQueries({ queryKey: ['recipe-groups', user?.id] });
      toast.success('Recipe removed from group');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to remove recipe from group');
    },
  });

  // Check if current user owns this group
  const canEdit = Boolean(
    group && 
    user && 
    (user.role === 'admin' || group.user_id === parseInt(user.id))
  );

  // Event handlers
  const handleEditSave = () => {
    if (!editFormData.name.trim()) {
      toast.error('Group name is required');
      return;
    }
    updateGroupMutation.mutate({
      name: editFormData.name.trim(),
      description: editFormData.description.trim()
    });
  };

  const handleEditCancel = () => {
    setEditFormData({
      name: group?.name || '',
      description: group?.description || ''
    });
    setIsEditing(false);
  };

  const handleDeleteGroup = () => {
    if (window.confirm(`Are you sure you want to delete "${group?.name}"? This action cannot be undone.`)) {
      deleteGroupMutation.mutate();
    }
  };

  const handleRemoveRecipe = (recipeId: number, recipeTitle: string) => {
    if (window.confirm(`Remove "${recipeTitle}" from this group?`)) {
      removeRecipeMutation.mutate(recipeId);
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{borderColor: '#f15f1c'}}></div>
          <p style={{color: '#9b644b'}}>Loading recipe group...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !group) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Recipe Group Not Found
        </h2>
        <p className="mb-4" style={{color: '#9b644b'}}>
          The recipe group you're looking for doesn't exist or you don't have permission to view it.
        </p>
        <Button onClick={() => navigate('/recipes?filter=groups')}>
          Back to All Groups
        </Button>
      </div>
    );
  }

  // Authentication check
  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Please log in to view this recipe group
        </h2>
        <Button onClick={() => navigate('/login')}>
          Sign In
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Back Navigation and Action Buttons */}
      <div className="mb-6 flex justify-between items-center">
        <button
          onClick={() => navigate('/recipes?filter=groups')}
          className="flex items-center space-x-2 text-text-secondary hover:text-accent transition-colors"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Back to All Groups</span>
        </button>
        
        {canEdit && !isEditing && (
          <div className="flex items-center space-x-3">
            <Button onClick={() => setIsEditing(true)} variant="secondary" size="sm">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit Group
            </Button>
            <Button 
              onClick={handleDeleteGroup} 
              variant="secondary" 
              size="sm"
              className="text-red-600 hover:text-red-700"
              disabled={deleteGroupMutation.isPending}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              {deleteGroupMutation.isPending ? 'Deleting...' : 'Delete Group'}
            </Button>
          </div>
        )}
        
        {isEditing && (
          <div className="flex items-center space-x-3">
            <Button 
              onClick={handleEditCancel} 
              variant="secondary" 
              size="sm"
              disabled={updateGroupMutation.isPending}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleEditSave} 
              size="sm"
              disabled={updateGroupMutation.isPending}
            >
              {updateGroupMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        )}
      </div>

      {/* Group Header */}
      <div className="bg-white rounded-xl shadow-sm border p-8 mb-6" style={{borderColor: '#e8d7cf'}}>
        <div className="flex flex-col lg:flex-row lg:items-start lg:space-x-8">
          {/* Group Cover Image */}
          <div className="w-full lg:w-1/3 mb-6 lg:mb-0">
            <div className="aspect-video bg-gradient-to-br from-background-secondary to-primary-200 rounded-lg overflow-hidden">
              {group.cover_image_url ? (
                <img
                  src={group.cover_image_url}
                  alt={group.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <div className="text-center">
                    <svg className="h-16 w-16 text-primary-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                    <p className="text-sm text-primary-400 font-medium">Recipe Group</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Group Info */}
          <div className="flex-1">
            {isEditing ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">Group Name</label>
                  <input
                    type="text"
                    value={editFormData.name}
                    onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
                    placeholder="Enter group name..."
                    maxLength={200}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">Description</label>
                  <textarea
                    value={editFormData.description}
                    onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent resize-none"
                    rows={3}
                    placeholder="Enter group description..."
                  />
                </div>
              </div>
            ) : (
              <>
                <h1 className="text-3xl font-bold mb-4" style={{color: '#1c120d'}}>
                  {group.name}
                </h1>

                {group.description && (
                  <p className="text-lg text-text-secondary mb-6">
                    {group.description}
                  </p>
                )}

                {/* Group Metadata */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                  <div className="text-center p-3 bg-background-secondary rounded-lg">
                    <div className="text-sm text-text-secondary mb-1">Recipes</div>
                    <div className="font-medium text-text-primary">{group.recipe_count}</div>
                  </div>

                  <div className="text-center p-3 bg-background-secondary rounded-lg">
                    <div className="text-sm text-text-secondary mb-1">Created</div>
                    <div className="font-medium text-text-primary">
                      {new Date(group.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="text-center p-3 bg-background-secondary rounded-lg">
                    <div className="text-sm text-text-secondary mb-1">Updated</div>
                    <div className="font-medium text-text-primary">
                      {new Date(group.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Search Bar */}
      {!isEditing && (
        <div className="flex justify-center mb-8">
          <SearchBar
            value={searchTerm}
            onChange={setSearchTerm}
            placeholder="Search recipes in this group..."
            className="w-full max-w-2xl"
          />
        </div>
      )}

      {/* Recipes Section */}
      {!isEditing && (
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
                  <div key={recipe.id} className="relative group">
                    <RecipeCard
                      recipe={recipe}
                      showPrivacyControls={false}
                      showAddToCollection={false}
                    />
                    {canEdit && (
                      <button
                        onClick={() => handleRemoveRecipe(recipe.id, recipe.title)}
                        className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition-opacity bg-red-500 hover:bg-red-600 text-white p-1 rounded-full shadow-lg"
                        title="Remove from group"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
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
                    
                    {Array.from({ length: pagination.pages }, (_, i) => i + 1).map((page) => (
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
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-text-primary mb-2">
                  {searchTerm ? 'No recipes found' : 'No recipes in this group'}
                </h3>
                <p className="text-text-secondary mb-4">
                  {searchTerm 
                    ? `No recipes match "${searchTerm}". Try a different search term.`
                    : 'Start building your recipe collection by adding recipes to this group.'
                  }
                </p>
                {!searchTerm && canEdit && (
                  <Button onClick={() => navigate('/recipes')} variant="primary">
                    Browse Recipes to Add
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

export { RecipeGroupDetail };