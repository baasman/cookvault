import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { smartFoldersApi } from '../services/smartFoldersApi';
import type { SmartFolderRules } from '../services/smartFoldersApi';
import { useAuth } from '../contexts/AuthContext';
import { Button, SearchBar, Modal } from '../components/ui';
import { RecipeCard, RecipeCardSkeleton } from '../components/recipe';
import { SmartFolderRuleBuilder } from '../components/recipe/SmartFolderRuleBuilder';
import type { Recipe } from '../types';
import toast from 'react-hot-toast';

const SmartFolderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const folderId = id ? parseInt(id, 10) : null;

  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editRules, setEditRules] = useState<SmartFolderRules>({ match: 'all', conditions: [] });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const { data: folderData, isLoading: isLoadingFolder } = useQuery({
    queryKey: ['smart-folder', folderId],
    queryFn: () => folderId ? smartFoldersApi.getSmartFolder(folderId) : Promise.reject('No folder ID'),
    enabled: !!folderId && isAuthenticated,
  });

  const { data: recipesData, isLoading: isLoadingRecipes } = useQuery({
    queryKey: ['smart-folder-recipes', folderId, currentPage, searchTerm],
    queryFn: () =>
      folderId
        ? smartFoldersApi.getSmartFolderRecipes(folderId, {
            page: currentPage,
            per_page: 12,
            search: searchTerm,
          })
        : Promise.reject('No folder ID'),
    enabled: !!folderId && isAuthenticated,
  });

  // Preview count for rule editor
  const { data: previewData } = useQuery({
    queryKey: ['smart-folder-preview', editRules],
    queryFn: () => smartFoldersApi.previewSmartFolder(editRules),
    enabled: showEditModal && editRules.conditions.length > 0 && editRules.conditions.every(c => c.value !== ''),
    staleTime: 2000,
  });

  const updateMutation = useMutation({
    mutationFn: (params: { name: string; description?: string; rules: SmartFolderRules }) =>
      smartFoldersApi.updateSmartFolder(folderId!, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['smart-folder', folderId] });
      queryClient.invalidateQueries({ queryKey: ['smart-folder-recipes', folderId] });
      queryClient.invalidateQueries({ queryKey: ['smart-folders'] });
      toast.success('Smart folder updated');
      setShowEditModal(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update smart folder');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => smartFoldersApi.deleteSmartFolder(folderId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['smart-folders'] });
      toast.success('Smart folder deleted');
      navigate('/recipes');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete smart folder');
    },
  });

  const folder = folderData?.smart_folder;
  const recipes = recipesData?.recipes || [];

  const openEditModal = () => {
    if (folder) {
      setEditName(folder.name);
      setEditDescription(folder.description || '');
      setEditRules(folder.rules);
      setShowEditModal(true);
    }
  };

  const handleUpdate = () => {
    if (!editName.trim()) {
      toast.error('Name is required');
      return;
    }
    updateMutation.mutate({
      name: editName.trim(),
      description: editDescription.trim() || undefined,
      rules: editRules,
    });
  };

  if (!isAuthenticated) {
    navigate('/login');
    return null;
  }

  if (isLoadingFolder) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded w-1/3 animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => <RecipeCardSkeleton key={i} />)}
        </div>
      </div>
    );
  }

  if (!folder) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{ color: '#1c120d' }}>Smart folder not found</h2>
        <Button onClick={() => navigate('/recipes')} variant="primary">Back to Recipes</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <button onClick={() => navigate('/recipes')} className="text-text-secondary hover:text-text-primary transition-colors">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="px-2 py-0.5 text-xs font-medium bg-indigo-100 text-indigo-700 rounded-full flex items-center gap-1">
              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Smart Folder
            </div>
          </div>
          <h1 className="text-3xl font-bold" style={{ color: '#1c120d' }}>{folder.name}</h1>
          {folder.description && (
            <p className="text-text-secondary mt-1">{folder.description}</p>
          )}
          <p className="text-sm text-text-secondary mt-2">
            {folder.rules.conditions.length} rule{folder.rules.conditions.length !== 1 ? 's' : ''} ({folder.rules.match === 'all' ? 'match all' : 'match any'}) &middot; {folder.recipe_count ?? 0} recipe{folder.recipe_count !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={openEditModal}>Edit Rules</Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowDeleteConfirm(true)}
            className="text-red-600 border-red-300 hover:bg-red-50"
          >
            Delete
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="max-w-md">
        <SearchBar
          value={searchTerm}
          onChange={setSearchTerm}
          placeholder="Search recipes in this folder..."
          className="w-full"
        />
      </div>

      {/* Recipes */}
      {isLoadingRecipes ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => <RecipeCardSkeleton key={i} />)}
        </div>
      ) : recipes.length > 0 ? (
        <>
          <div className="text-sm text-text-secondary">
            Showing {recipes.length} of {recipesData?.total || 0} recipe{(recipesData?.total || 0) !== 1 ? 's' : ''}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {recipes.map((recipe: Recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} />
            ))}
          </div>

          {/* Pagination */}
          {recipesData && recipesData.pages > 1 && (
            <div className="flex justify-center mt-8">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => { setCurrentPage(p => p - 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                  disabled={currentPage === 1}
                  className="px-4 py-2 text-sm border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:bg-background-secondary"
                  style={{ borderColor: '#e8d7cf', color: '#9b644b' }}
                >
                  Previous
                </button>
                <span className="text-sm text-text-secondary">
                  Page {currentPage} of {recipesData.pages}
                </span>
                <button
                  onClick={() => { setCurrentPage(p => p + 1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                  disabled={currentPage === recipesData.pages}
                  className="px-4 py-2 text-sm border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:bg-background-secondary"
                  style={{ borderColor: '#e8d7cf', color: '#9b644b' }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-text-primary mb-2">No matching recipes</h3>
          <p className="text-text-secondary">
            {searchTerm
              ? `No recipes match your search within this smart folder.`
              : `No recipes match the current rules. Try editing the rules to broaden the criteria.`}
          </p>
        </div>
      )}

      {/* Edit Modal */}
      <Modal isOpen={showEditModal} onClose={() => setShowEditModal(false)} size="lg">
        <div className="p-6">
          <h2 className="text-lg font-bold text-text-primary mb-4">Edit Smart Folder</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Name</label>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
                maxLength={200}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Description (optional)</label>
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent resize-none"
                rows={2}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">Rules</label>
              <SmartFolderRuleBuilder
                rules={editRules}
                onChange={setEditRules}
                previewCount={previewData?.count ?? null}
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <Button variant="secondary" onClick={() => setShowEditModal(false)} disabled={updateMutation.isPending}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleUpdate}
              disabled={!editName.trim() || editRules.conditions.length === 0 || updateMutation.isPending}
            >
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation */}
      <Modal isOpen={showDeleteConfirm} onClose={() => setShowDeleteConfirm(false)} size="sm">
        <div className="p-6">
          <h2 className="text-lg font-bold text-text-primary mb-2">Delete Smart Folder?</h2>
          <p className="text-text-secondary mb-6">
            This will delete the smart folder "{folder.name}". Your recipes will not be affected.
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setShowDeleteConfirm(false)} disabled={deleteMutation.isPending}>
              Cancel
            </Button>
            <Button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="bg-red-600 hover:bg-red-700 text-white border-red-600"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export { SmartFolderDetailPage };
