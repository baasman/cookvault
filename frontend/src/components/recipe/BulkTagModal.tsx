import React, { useState } from 'react';
import { Modal, Button } from '../ui';

type TagAction = 'add' | 'remove' | 'set';

interface BulkTagModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (tags: string[], action: TagAction) => void;
  count: number;
  isUpdating: boolean;
}

const BulkTagModal: React.FC<BulkTagModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  count,
  isUpdating,
}) => {
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [action, setAction] = useState<TagAction>('add');

  const handleAddTag = () => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) {
      setTags(prev => [...prev, trimmed]);
      setTagInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(prev => prev.filter(t => t !== tag));
  };

  const handleConfirm = () => {
    if (tags.length > 0) {
      onConfirm(tags, action);
      setTags([]);
      setTagInput('');
      setAction('add');
    }
  };

  const handleClose = () => {
    setTags([]);
    setTagInput('');
    setAction('add');
    onClose();
  };

  const actionLabels: Record<TagAction, string> = {
    add: 'Add tags to',
    remove: 'Remove tags from',
    set: 'Replace all tags on',
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="md">
      <div className="p-6">
        <h2 className="text-lg font-bold text-text-primary mb-4">
          Update Tags on {count} Recipe{count !== 1 ? 's' : ''}
        </h2>

        {/* Action selection */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-text-primary mb-2">Action</label>
          <div className="flex gap-2">
            {(['add', 'remove', 'set'] as const).map((a) => (
              <button
                key={a}
                onClick={() => setAction(a)}
                className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                  action === a
                    ? 'bg-accent text-white border-accent'
                    : 'bg-white text-text-secondary border-gray-300 hover:border-accent/50'
                }`}
              >
                {a === 'add' ? 'Add' : a === 'remove' ? 'Remove' : 'Replace All'}
              </button>
            ))}
          </div>
        </div>

        {/* Tag input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-text-primary mb-2">Tags</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a tag and press Enter..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
              disabled={isUpdating}
              autoFocus
            />
            <Button
              onClick={handleAddTag}
              variant="secondary"
              size="sm"
              disabled={!tagInput.trim() || isUpdating}
            >
              Add
            </Button>
          </div>
        </div>

        {/* Tag chips */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-sm rounded-full bg-accent/10 text-accent"
              >
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="hover:text-red-600 transition-colors"
                  disabled={isUpdating}
                >
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Summary */}
        {tags.length > 0 && (
          <p className="text-sm text-text-secondary mb-4">
            {actionLabels[action]} {count} recipe{count !== 1 ? 's' : ''}: {tags.join(', ')}
            {action === 'set' && (
              <span className="text-amber-600 block mt-1">
                Warning: This will replace all existing tags on the selected recipes.
              </span>
            )}
          </p>
        )}

        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={handleClose} disabled={isUpdating}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            variant="primary"
            disabled={tags.length === 0 || isUpdating}
          >
            {isUpdating ? 'Updating...' : 'Apply Tags'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export { BulkTagModal };
