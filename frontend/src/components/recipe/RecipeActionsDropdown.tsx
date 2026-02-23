import React, { useState, useRef, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { recipesApi } from '../../services/recipesApi';
import { recipeGroupsApi } from '../../services/recipeGroupsApi';
import { shareRecipe } from '../../services/shareService';
import { CopyrightConsentModal } from '../ui/CopyrightConsentModal';
import { ExportButton } from '../export/ExportButton';
import { useAuth } from '../../contexts/AuthContext';
import type { Recipe } from '../../types';

interface RecipeActionsDropdownProps {
  recipe: Recipe;
  isOwnRecipe: boolean;
  canEdit: boolean;
  onEditClick: () => void;
  onDeleteClick: () => void;
  onRecipeUpdate?: (recipe: Recipe) => void;
}

const RecipeActionsDropdown: React.FC<RecipeActionsDropdownProps> = ({
  recipe,
  isOwnRecipe,
  canEdit,
  onEditClick,
  onDeleteClick,
  onRecipeUpdate
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showCopyrightModal, setShowCopyrightModal] = useState(false);
  const [showGroupSelector, setShowGroupSelector] = useState(false);
  const [isSharing, setIsSharing] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Add to Collection mutation
  const addToCollectionMutation = useMutation({
    mutationFn: () => recipesApi.addToCollection(recipe.id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      toast.success(data.message || 'Recipe added to collection!');
      setIsOpen(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add recipe to collection');
    },
  });

  const removeFromCollectionMutation = useMutation({
    mutationFn: () => recipesApi.removeFromCollection(recipe.id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      toast.success(data.message || 'Recipe removed from collection');
      setIsOpen(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to remove recipe from collection');
    },
  });

  // Copy Recipe mutation
  const copyRecipeMutation = useMutation({
    mutationFn: () => recipesApi.copyRecipe(recipe.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      toast.success('Recipe copied to your collection!');
      setIsOpen(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to copy recipe');
    },
  });

  // Toggle Privacy mutation
  const togglePrivacyMutation = useMutation({
    mutationFn: (params: { isPublic: boolean; consents?: Record<string, boolean> }) =>
      recipesApi.toggleRecipePrivacy(recipe.id, params.isPublic, params.consents),
    onSuccess: (updatedRecipe: Recipe) => {
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      const message = updatedRecipe.is_public ? 'Recipe made public!' : 'Recipe made private!';
      toast.success(message);
      setIsOpen(false);
      onRecipeUpdate?.(updatedRecipe);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update recipe privacy');
    },
  });

  // Feature Recipe mutation
  const featureMutation = useMutation({
    mutationFn: () => recipesApi.featureRecipe(recipe.id),
    onSuccess: (updatedRecipe: Recipe) => {
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      toast.success('Recipe featured!');
      setIsOpen(false);
      onRecipeUpdate?.(updatedRecipe);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to feature recipe');
    },
  });

  const unfeatureMutation = useMutation({
    mutationFn: () => recipesApi.unfeatureRecipe(recipe.id),
    onSuccess: (updatedRecipe: Recipe) => {
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      toast.success('Recipe unfeatured');
      setIsOpen(false);
      onRecipeUpdate?.(updatedRecipe);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to unfeature recipe');
    },
  });

  // Handlers
  const handleCollectionToggle = () => {
    if (recipe.is_in_collection) {
      removeFromCollectionMutation.mutate();
    } else {
      addToCollectionMutation.mutate();
    }
  };

  const handlePrivacyToggle = () => {
    if (!recipe.is_public) {
      setShowCopyrightModal(true);
      setIsOpen(false);
    } else {
      togglePrivacyMutation.mutate({ isPublic: false });
    }
  };

  const handleCopyrightConsent = (consents: Record<string, boolean>) => {
    setShowCopyrightModal(false);
    togglePrivacyMutation.mutate({ isPublic: true, consents });
  };

  const handleFeatureToggle = () => {
    if (recipe.is_featured) {
      unfeatureMutation.mutate();
    } else {
      featureMutation.mutate();
    }
  };

  const handleShare = async () => {
    if (isSharing) return;
    setIsSharing(true);
    try {
      const result = await shareRecipe(recipe);
      if (result?.activityType === 'clipboard') {
        toast.success('Link copied to clipboard!');
      } else if (result) {
        toast.success('Recipe shared!');
      }
      setIsOpen(false);
    } catch (error) {
      console.error('Share failed:', error);
      toast.error('Failed to share recipe');
    } finally {
      setIsSharing(false);
    }
  };

  const handleAddToGroup = () => {
    setShowGroupSelector(true);
    setIsOpen(false);
  };

  // Determine which user context we're in for showing appropriate options
  const showAddToCollection = !isOwnRecipe && recipe.is_public;
  const showCopyRecipe = !isOwnRecipe && recipe.is_public;
  const showPrivacyToggle = isOwnRecipe;
  const showFeature = isAdmin && recipe.is_public; // Admin-only
  const showShare = recipe.is_public;
  const showExport = recipe.has_full_access;
  const showDelete = canEdit;

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium rounded-md
            bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200
            transition-all duration-200"
          aria-label="More actions"
        >
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
          </svg>
          More
        </button>

        {isOpen && (
          <div className="absolute right-0 top-full mt-2 bg-white rounded-lg shadow-lg border z-50 min-w-[200px] py-1"
            style={{ borderColor: '#e8d7cf' }}>

            {/* Add to Group - using native browser dialog through AddToGroupButton */}
            <button
              onClick={handleAddToGroup}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
            >
              <svg className="w-4 h-4 mr-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              Add to Group
            </button>

            {showAddToCollection && (
              <button
                onClick={handleCollectionToggle}
                disabled={addToCollectionMutation.isPending || removeFromCollectionMutation.isPending}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center disabled:opacity-50"
              >
                <svg className={`w-4 h-4 mr-3 ${recipe.is_in_collection ? 'text-green-600' : 'text-gray-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {recipe.is_in_collection ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  )}
                </svg>
                {recipe.is_in_collection ? 'In Collection' : 'Add to Collection'}
              </button>
            )}

            {showCopyRecipe && (
              <button
                onClick={() => copyRecipeMutation.mutate()}
                disabled={copyRecipeMutation.isPending}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center disabled:opacity-50"
              >
                <svg className="w-4 h-4 mr-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy Recipe
              </button>
            )}

            <div className="border-t my-1" style={{ borderColor: '#e8d7cf' }} />

            {showPrivacyToggle && (
              <button
                onClick={handlePrivacyToggle}
                disabled={togglePrivacyMutation.isPending}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center disabled:opacity-50"
              >
                <svg className={`w-4 h-4 mr-3 ${recipe.is_public ? 'text-green-600' : 'text-gray-500'}`} fill="currentColor" viewBox="0 0 20 20">
                  {recipe.is_public ? (
                    <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                  ) : (
                    <>
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                      <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                    </>
                  )}
                </svg>
                {recipe.is_public ? 'Make Private' : 'Make Public'}
              </button>
            )}

            {showFeature && (
              <button
                onClick={handleFeatureToggle}
                disabled={featureMutation.isPending || unfeatureMutation.isPending}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center disabled:opacity-50"
              >
                <svg className={`w-4 h-4 mr-3 ${recipe.is_featured ? 'text-yellow-500' : 'text-gray-500'}`} fill={recipe.is_featured ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                </svg>
                {recipe.is_featured ? 'Unfeature' : 'Feature Recipe'}
              </button>
            )}

            {showExport && (
              <div className="px-4 py-2 hover:bg-gray-50" onClick={(e) => e.stopPropagation()}>
                <ExportButton
                  type="recipe"
                  recipeId={recipe.id}
                  buttonText="Download"
                  showOptions={true}
                  size="sm"
                />
              </div>
            )}

            {showShare && (
              <button
                onClick={handleShare}
                disabled={isSharing}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center disabled:opacity-50"
              >
                <svg className="w-4 h-4 mr-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
                Share
              </button>
            )}

            {canEdit && (
              <>
                <div className="border-t my-1" style={{ borderColor: '#e8d7cf' }} />
                <button
                  onClick={() => { onEditClick(); setIsOpen(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
                >
                  <svg className="w-4 h-4 mr-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Edit Recipe
                </button>
              </>
            )}

            {showDelete && (
              <>
                <div className="border-t my-1" style={{ borderColor: '#e8d7cf' }} />
                <button
                  onClick={() => { onDeleteClick(); setIsOpen(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center"
                >
                  <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Delete Recipe
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Copyright Consent Modal */}
      <CopyrightConsentModal
        isOpen={showCopyrightModal}
        onClose={() => setShowCopyrightModal(false)}
        onConfirm={handleCopyrightConsent}
        recipeName={recipe.title}
        isLoading={togglePrivacyMutation.isPending}
      />

      {/* Add to Group Modal - trigger the existing AddToGroupButton functionality */}
      {showGroupSelector && (
        <div className="fixed inset-0 z-50">
          <div className="fixed inset-0 bg-black/50" onClick={() => setShowGroupSelector(false)} />
          <div className="fixed inset-0 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6" onClick={e => e.stopPropagation()}>
              <h3 className="text-lg font-semibold mb-4">Add to Group</h3>
              <AddToGroupContent recipe={recipe} onClose={() => setShowGroupSelector(false)} />
            </div>
          </div>
        </div>
      )}
    </>
  );
};

// Extracted Add to Group content for the modal
const AddToGroupContent: React.FC<{ recipe: Recipe; onClose: () => void }> = ({ recipe, onClose }) => {
  const queryClient = useQueryClient();
  const [groups, setGroups] = useState<Array<{ id: number; name: string; is_system?: boolean }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchGroups = async () => {
      try {
        const response = await recipeGroupsApi.getRecipeGroups();
        // Filter out system groups since they have their own buttons
        setGroups(response.groups.filter(g => !g.is_system));
      } catch (error) {
        console.error('Error fetching groups:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchGroups();
  }, []);

  const addToGroupMutation = useMutation({
    mutationFn: (groupId: number) => recipeGroupsApi.addRecipeToGroup(groupId, recipe.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe', recipe.id] });
      queryClient.invalidateQueries({ queryKey: ['recipe-groups'] });
      toast.success('Recipe added to group!');
      onClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add recipe to group');
    },
  });

  if (loading) {
    return <div className="text-center py-4">Loading groups...</div>;
  }

  if (groups.length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-gray-500 mb-4">You don't have any custom groups yet.</p>
        <button onClick={onClose} className="text-accent hover:underline">Close</button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {groups.map(group => {
        const isInGroup = recipe.groups?.some(g => g.id === group.id);
        return (
          <button
            key={group.id}
            onClick={() => !isInGroup && addToGroupMutation.mutate(group.id)}
            disabled={isInGroup || addToGroupMutation.isPending}
            className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
              isInGroup
                ? 'bg-green-50 border-green-200 text-green-700'
                : 'border-gray-200 hover:border-accent hover:bg-accent/5'
            } disabled:opacity-50`}
          >
            <div className="flex items-center justify-between">
              <span>{group.name}</span>
              {isInGroup && (
                <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </div>
          </button>
        );
      })}
      <div className="pt-4 border-t mt-4">
        <button onClick={onClose} className="w-full py-2 text-gray-500 hover:text-gray-700">
          Cancel
        </button>
      </div>
    </div>
  );
};

export { RecipeActionsDropdown };
