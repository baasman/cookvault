import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recipeGroupsApi, type RecipeGroup } from '../../services/recipeGroupsApi';
import { useAuth } from '../../contexts/AuthContext';
import { Modal, Button, SearchBar } from '../ui';
import type { Recipe } from '../../types';
import toast from 'react-hot-toast';

interface AddToGroupModalProps {
  recipe: Recipe;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const AddToGroupModal: React.FC<AddToGroupModalProps> = ({
  recipe,
  isOpen,
  onClose,
  onSuccess
}) => {
  const { isAuthenticated, user } = useAuth();
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGroupIds, setSelectedGroupIds] = useState<Set<number>>(new Set());
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setSearchTerm('');
      setSelectedGroupIds(new Set());
      setShowCreateForm(false);
      setNewGroupName('');
    }
  }, [isOpen]);

  // Fetch user's recipe groups
  const { 
    data: groupsData, 
    isLoading: isLoadingGroups,
    error: groupsError 
  } = useQuery({
    queryKey: ['recipe-groups', user?.id],
    queryFn: () => recipeGroupsApi.getRecipeGroups(),
    enabled: isAuthenticated && isOpen,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Filter groups based on search term
  const filteredGroups = (groupsData?.groups || []).filter(group =>
    group.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (group.description && group.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Create new group mutation
  const createGroupMutation = useMutation({
    mutationFn: (name: string) => recipeGroupsApi.createRecipeGroup({ 
      name: name.trim(),
      description: `Group created for ${recipe.title}`,
      is_private: true 
    }),
    onSuccess: (response) => {
      // Add the new group to selected groups
      setSelectedGroupIds(prev => new Set([...prev, response.group.id]));
      setShowCreateForm(false);
      setNewGroupName('');
      queryClient.invalidateQueries({ queryKey: ['recipe-groups', user?.id] });
      toast.success(`Group "${response.group.name}" created!`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create group');
    },
  });

  // Add recipe to groups mutation
  const addToGroupsMutation = useMutation({
    mutationFn: async (groupIds: number[]) => {
      const promises = groupIds.map(groupId => 
        recipeGroupsApi.addRecipeToGroup(groupId, recipe.id)
      );
      return Promise.all(promises);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe-groups', user?.id] });
      queryClient.invalidateQueries({ queryKey: ['recipe-group'] });
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      
      const groupCount = selectedGroupIds.size;
      toast.success(`Recipe added to ${groupCount} group${groupCount !== 1 ? 's' : ''}!`);
      onSuccess?.();
      onClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add recipe to groups');
    },
  });

  const handleGroupToggle = (groupId: number) => {
    setSelectedGroupIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupId)) {
        newSet.delete(groupId);
      } else {
        newSet.add(groupId);
      }
      return newSet;
    });
  };

  const handleCreateGroup = () => {
    if (!newGroupName.trim()) {
      toast.error('Group name is required');
      return;
    }
    createGroupMutation.mutate(newGroupName);
  };

  const handleAddToGroups = () => {
    if (selectedGroupIds.size === 0) {
      toast.error('Please select at least one group');
      return;
    }
    addToGroupsMutation.mutate(Array.from(selectedGroupIds));
  };

  const isProcessing = createGroupMutation.isPending || addToGroupsMutation.isPending;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b" style={{ borderColor: '#e8d7cf' }}>
        <h2 id="modal-title" className="text-xl font-bold" style={{ color: '#1c120d' }}>
          Add "{recipe.title}" to Groups
        </h2>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
          disabled={isProcessing}
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Search Bar */}
        <div className="mb-6">
          <SearchBar
            value={searchTerm}
            onChange={setSearchTerm}
            placeholder="Search your recipe groups..."
            className="w-full"
          />
        </div>

        {/* Loading State */}
        {isLoadingGroups && (
          <div className="flex justify-center py-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 mx-auto mb-2" style={{ borderColor: '#f15f1c' }}></div>
              <p className="text-sm" style={{ color: '#9b644b' }}>Loading your groups...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {groupsError && (
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">Failed to load recipe groups</p>
            <Button onClick={() => queryClient.invalidateQueries({ queryKey: ['recipe-groups', user?.id] })}>
              Try Again
            </Button>
          </div>
        )}

        {/* Groups Grid */}
        {!isLoadingGroups && !groupsError && (
          <>
            {filteredGroups.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                {filteredGroups.map((group: RecipeGroup) => (
                  <div
                    key={group.id}
                    className={`
                      border rounded-lg p-4 cursor-pointer transition-all duration-200
                      ${selectedGroupIds.has(group.id)
                        ? 'border-accent bg-accent/5'
                        : 'border-gray-200 hover:border-accent/50'
                      }
                    `}
                    style={{
                      borderColor: selectedGroupIds.has(group.id) ? '#f15f1c' : undefined,
                      backgroundColor: selectedGroupIds.has(group.id) ? 'rgba(241, 95, 28, 0.05)' : undefined
                    }}
                    onClick={() => handleGroupToggle(group.id)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 mr-3">
                        <h3 className="font-medium text-text-primary mb-1">{group.name}</h3>
                        {group.description && (
                          <p className="text-sm text-text-secondary mb-2 line-clamp-2">
                            {group.description}
                          </p>
                        )}
                        <div className="flex items-center text-xs text-text-secondary">
                          <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                          </svg>
                          {group.recipe_count} recipe{group.recipe_count !== 1 ? 's' : ''}
                        </div>
                      </div>
                      <div className="flex-shrink-0">
                        <div className={`
                          w-5 h-5 rounded border-2 flex items-center justify-center
                          ${selectedGroupIds.has(group.id)
                            ? 'bg-accent border-accent'
                            : 'border-gray-300'
                          }
                        `}>
                          {selectedGroupIds.has(group.id) && (
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-text-primary mb-2">
                  {searchTerm ? 'No groups found' : 'No recipe groups yet'}
                </h3>
                <p className="text-text-secondary mb-4">
                  {searchTerm 
                    ? `No groups match "${searchTerm}". Try a different search term.`
                    : 'Create your first recipe group to organize your recipes.'
                  }
                </p>
              </div>
            )}

            {/* Create New Group Section */}
            <div className="border-t pt-6" style={{ borderColor: '#e8d7cf' }}>
              {!showCreateForm ? (
                <button
                  onClick={() => setShowCreateForm(true)}
                  className="w-full p-3 border-2 border-dashed border-accent/30 rounded-lg text-accent hover:border-accent/50 transition-colors flex items-center justify-center"
                  disabled={isProcessing}
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Create New Group
                </button>
              ) : (
                <div className="space-y-3">
                  <div>
                    <input
                      type="text"
                      value={newGroupName}
                      onChange={(e) => setNewGroupName(e.target.value)}
                      placeholder="Enter group name..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
                      maxLength={200}
                      disabled={isProcessing}
                      autoFocus
                    />
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      onClick={handleCreateGroup}
                      variant="primary"
                      disabled={!newGroupName.trim() || isProcessing}
                      size="sm"
                    >
                      {createGroupMutation.isPending ? 'Creating...' : 'Create Group'}
                    </Button>
                    <Button
                      onClick={() => {
                        setShowCreateForm(false);
                        setNewGroupName('');
                      }}
                      variant="secondary"
                      size="sm"
                      disabled={isProcessing}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between p-6 border-t bg-gray-50" style={{ borderColor: '#e8d7cf' }}>
        <div className="text-sm text-text-secondary">
          {selectedGroupIds.size > 0 && (
            <span>
              {selectedGroupIds.size} group{selectedGroupIds.size !== 1 ? 's' : ''} selected
            </span>
          )}
        </div>
        <div className="flex space-x-3">
          <Button
            onClick={onClose}
            variant="secondary"
            disabled={isProcessing}
          >
            Cancel
          </Button>
          <Button
            onClick={handleAddToGroups}
            variant="primary"
            disabled={selectedGroupIds.size === 0 || isProcessing}
          >
            {addToGroupsMutation.isPending ? 'Adding...' : 'Add to Groups'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export { AddToGroupModal };