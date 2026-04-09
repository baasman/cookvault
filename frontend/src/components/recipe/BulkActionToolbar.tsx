import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { isIOS, isNativePlatform } from '../../utils/platform';
import { recipesApi } from '../../services/recipesApi';
import { recipeGroupsApi } from '../../services/recipeGroupsApi';
import { useAuth } from '../../contexts/AuthContext';
import { BulkDeleteModal } from './BulkDeleteModal';
import { BulkTagModal } from './BulkTagModal';
import { Modal, Button, SearchBar, CopyrightConsentModal } from '../ui';
import toast from 'react-hot-toast';

interface BulkActionToolbarProps {
  selectedIds: Set<number>;
  allVisibleIds: number[];
  onSelectAll: (ids: number[]) => void;
  onClearSelection: () => void;
  onExitSelectionMode: () => void;
}

const BulkActionToolbar: React.FC<BulkActionToolbarProps> = ({
  selectedIds,
  allVisibleIds,
  onSelectAll,
  onClearSelection,
  onExitSelectionMode,
}) => {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showTagModal, setShowTagModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showPrivacyModal, setShowPrivacyModal] = useState(false);

  const count = selectedIds.size;
  const selectedArray = Array.from(selectedIds);
  const allSelected = allVisibleIds.length > 0 && allVisibleIds.every(id => selectedIds.has(id));

  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [groupSearchTerm, setGroupSearchTerm] = useState('');
  const [showNewGroupInput, setShowNewGroupInput] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');

  const { data: groupsData } = useQuery({
    queryKey: ['recipe-groups', user?.id],
    queryFn: () => recipeGroupsApi.getRecipeGroups(),
    enabled: showGroupModal,
    staleTime: 5 * 60 * 1000,
  });

  const filteredGroups = (groupsData?.groups || []).filter(g =>
    g.name.toLowerCase().includes(groupSearchTerm.toLowerCase())
  );

  const createGroupMutation = useMutation({
    mutationFn: (name: string) => recipeGroupsApi.createRecipeGroup({ name, is_private: true }),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['recipe-groups', user?.id] });
      setSelectedGroupId(response.group.id);
      setShowNewGroupInput(false);
      setNewGroupName('');
      toast.success(`Group "${response.group.name}" created!`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create group');
    },
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['recipes'] });
    queryClient.invalidateQueries({ queryKey: ['recipe-groups', user?.id] });
  };

  const bulkDeleteMutation = useMutation({
    mutationFn: () => recipesApi.bulkDelete(selectedArray),
    onSuccess: (result) => {
      invalidateAll();
      const deleted = result.deleted.length;
      const errors = result.errors.length;
      if (deleted > 0) toast.success(`Deleted ${deleted} recipe${deleted !== 1 ? 's' : ''}`);
      if (errors > 0) toast.error(`${errors} recipe${errors !== 1 ? 's' : ''} could not be deleted`);
      setShowDeleteModal(false);
      onExitSelectionMode();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete recipes');
      setShowDeleteModal(false);
    },
  });

  const bulkTagMutation = useMutation({
    mutationFn: ({ tags, action }: { tags: string[]; action: 'add' | 'remove' | 'set' }) =>
      recipesApi.bulkUpdateTags(selectedArray, tags, action),
    onSuccess: (result) => {
      invalidateAll();
      toast.success(`Updated tags on ${result.updated.length} recipe${result.updated.length !== 1 ? 's' : ''}`);
      setShowTagModal(false);
      onClearSelection();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update tags');
      setShowTagModal(false);
    },
  });

  const bulkPrivacyMutation = useMutation({
    mutationFn: (consents: Record<string, boolean>) =>
      recipesApi.bulkTogglePrivacy(selectedArray, true, consents),
    onSuccess: (result) => {
      invalidateAll();
      const updated = result.updated.length;
      const errors = result.errors.length;
      if (updated > 0) toast.success(`Published ${updated} recipe${updated !== 1 ? 's' : ''}`);
      if (errors > 0) toast.error(`${errors} recipe${errors !== 1 ? 's' : ''} could not be published`);
      setShowPrivacyModal(false);
      onClearSelection();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update privacy');
      setShowPrivacyModal(false);
    },
  });

  const bulkAddToGroupMutation = useMutation({
    mutationFn: (groupId: number) => recipesApi.bulkAddToGroup(selectedArray, groupId),
    onSuccess: (result) => {
      invalidateAll();
      const added = result.added.length;
      const already = result.already_in_group.length;
      if (added > 0) toast.success(`Added ${added} recipe${added !== 1 ? 's' : ''} to group`);
      if (already > 0) toast(`${already} recipe${already !== 1 ? 's were' : ' was'} already in the group`);
      setShowGroupModal(false);
      setSelectedGroupId(null);
      setGroupSearchTerm('');
      onClearSelection();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add recipes to group');
    },
  });

  const handleAddToGroupConfirm = () => {
    if (selectedGroupId) {
      bulkAddToGroupMutation.mutate(selectedGroupId);
    }
  };

  if (count === 0) return null;

  return (
    <>
      {/* Fixed bottom toolbar — sits above iOS tab bar */}
      <div
        className="fixed left-0 right-0 z-[60] bg-white border-t shadow-lg"
        style={{
          borderColor: '#e8d7cf',
          bottom: isIOS() && isNativePlatform() ? 'calc(49px + env(safe-area-inset-bottom))' : '0',
        }}
      >
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          {/* Left: selection info */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-text-primary">
              {count} selected
            </span>
            <button
              onClick={() => allSelected ? onClearSelection() : onSelectAll(allVisibleIds)}
              className="text-sm text-accent hover:text-accent/80 transition-colors"
            >
              {allSelected ? 'Deselect All' : 'Select All'}
            </button>
          </div>

          {/* Right: action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowGroupModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:border-accent/50 hover:bg-accent/5 transition-colors text-text-primary"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span className="hidden sm:inline">Group</span>
            </button>

            <button
              onClick={() => setShowTagModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:border-accent/50 hover:bg-accent/5 transition-colors text-text-primary"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              <span className="hidden sm:inline">Tag</span>
            </button>

            <button
              onClick={() => setShowPrivacyModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:border-accent/50 hover:bg-accent/5 transition-colors text-text-primary"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <span className="hidden sm:inline">Publish</span>
            </button>

            <button
              onClick={() => setShowDeleteModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-red-300 hover:bg-red-50 transition-colors text-red-600"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              <span className="hidden sm:inline">Delete</span>
            </button>

            <div className="w-px h-6 bg-gray-300 mx-1" />

            <button
              onClick={onExitSelectionMode}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg text-text-secondary hover:text-text-primary transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span className="hidden sm:inline">Done</span>
            </button>
          </div>
        </div>
      </div>

      {/* Modals */}
      <BulkDeleteModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={() => bulkDeleteMutation.mutate()}
        count={count}
        isDeleting={bulkDeleteMutation.isPending}
      />

      <BulkTagModal
        isOpen={showTagModal}
        onClose={() => setShowTagModal(false)}
        onConfirm={(tags, action) => bulkTagMutation.mutate({ tags, action })}
        count={count}
        isUpdating={bulkTagMutation.isPending}
      />

      <Modal isOpen={showGroupModal} onClose={() => { setShowGroupModal(false); setSelectedGroupId(null); setGroupSearchTerm(''); }} size="md">
        <div className="p-6">
          <h2 className="text-lg font-bold text-text-primary mb-4">
            Add {count} Recipe{count !== 1 ? 's' : ''} to Group
          </h2>
          <SearchBar
            value={groupSearchTerm}
            onChange={setGroupSearchTerm}
            placeholder="Search groups..."
            className="w-full mb-4"
          />
          <div className="max-h-64 overflow-y-auto space-y-2 mb-4">
            {filteredGroups.map((group) => (
              <button
                key={group.id}
                onClick={() => setSelectedGroupId(group.id)}
                className={`w-full text-left p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                  selectedGroupId === group.id
                    ? 'border-accent bg-accent/5'
                    : 'border-gray-200 bg-white hover:border-accent/50 hover:bg-gray-50'
                }`}
                style={selectedGroupId === group.id ? { borderColor: '#f15f1c' } : undefined}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-text-primary">{group.name}</div>
                    <div className="text-xs text-text-secondary">{group.recipe_count} recipe{group.recipe_count !== 1 ? 's' : ''}</div>
                  </div>
                  <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                    selectedGroupId === group.id ? 'bg-accent border-accent' : 'border-gray-300'
                  }`}>
                    {selectedGroupId === group.id && (
                      <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                </div>
              </button>
            ))}
            {filteredGroups.length === 0 && (
              <p className="text-center text-text-secondary py-4">No groups found</p>
            )}
          </div>

          {/* Create new group inline */}
          {!showNewGroupInput ? (
            <button
              onClick={() => setShowNewGroupInput(true)}
              className="w-full p-3 border-2 border-dashed border-accent/30 rounded-lg text-accent hover:border-accent/50 transition-colors flex items-center justify-center text-sm mb-4"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Create New Group
            </button>
          ) : (
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                placeholder="Group name..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
                autoFocus
              />
              <Button
                variant="primary"
                size="sm"
                disabled={!newGroupName.trim() || createGroupMutation.isPending}
                onClick={() => createGroupMutation.mutate(newGroupName.trim())}
              >
                {createGroupMutation.isPending ? '...' : 'Create'}
              </Button>
              <Button variant="secondary" size="sm" onClick={() => { setShowNewGroupInput(false); setNewGroupName(''); }}>
                Cancel
              </Button>
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => { setShowGroupModal(false); setSelectedGroupId(null); setGroupSearchTerm(''); setShowNewGroupInput(false); setNewGroupName(''); }}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleAddToGroupConfirm}
              disabled={!selectedGroupId || bulkAddToGroupMutation.isPending}
            >
              {bulkAddToGroupMutation.isPending ? 'Adding...' : 'Add to Group'}
            </Button>
          </div>
        </div>
      </Modal>

      <CopyrightConsentModal
        isOpen={showPrivacyModal}
        onClose={() => setShowPrivacyModal(false)}
        onConfirm={(consents) => bulkPrivacyMutation.mutate(consents)}
        recipeName={`${count} recipe${count !== 1 ? 's' : ''}`}
        isLoading={bulkPrivacyMutation.isPending}
      />
    </>
  );
};

export { BulkActionToolbar };
