import React, { useState, useCallback, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { recipesApi } from '../../services/recipesApi';
import { useAuth } from '../../contexts/AuthContext';
import type { Recipe } from '../../types';
import toast from 'react-hot-toast';

interface NotesSectionProps {
  recipe: Recipe;
}

const NotesSection: React.FC<NotesSectionProps> = ({ recipe }) => {
  const { user } = useAuth();
  
  // Check if current user owns the recipe (for editing permissions)
  const isOwnRecipe = Boolean(user && recipe.user_id && user.id && recipe.user_id === parseInt(user.id));
  
  const [isExpanded, setIsExpanded] = useState(false);
  const [noteContent, setNoteContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const queryClient = useQueryClient();

  // Initialize note content from recipe data
  useEffect(() => {
    if (recipe.user_note) {
      setNoteContent(recipe.user_note.content);
      setIsExpanded(true); // Auto-expand if user has a note
    }
  }, [recipe.user_note]);

  // Save note mutation
  const saveNoteMutation = useMutation({
    mutationFn: (content: string) => recipesApi.saveUserNote(recipe.id, content),
    onMutate: () => setIsSaving(true),
    onSuccess: (data) => {
      // Update the recipe cache with the new note
      queryClient.setQueryData(['recipe', recipe.id], (oldData: Recipe | undefined) => {
        if (oldData) {
          return { ...oldData, user_note: data.note };
        }
        return oldData;
      });
      setHasUnsavedChanges(false);
      toast.success('Note saved');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to save note');
    },
    onSettled: () => setIsSaving(false),
  });

  // Delete note mutation
  const deleteNoteMutation = useMutation({
    mutationFn: () => recipesApi.deleteUserNote(recipe.id),
    onMutate: () => setIsSaving(true),
    onSuccess: () => {
      // Update the recipe cache to remove the note
      queryClient.setQueryData(['recipe', recipe.id], (oldData: Recipe | undefined) => {
        if (oldData) {
          return { ...oldData, user_note: null };
        }
        return oldData;
      });
      setNoteContent('');
      setHasUnsavedChanges(false);
      toast.success('Note deleted');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete note');
    },
    onSettled: () => setIsSaving(false),
  });

  // Auto-save functionality with debounce
  const debouncedSave = useCallback(
    debounce((content: string) => {
      if (content.trim() && hasUnsavedChanges) {
        saveNoteMutation.mutate(content.trim());
      }
    }, 2000), // Save 2 seconds after user stops typing
    [hasUnsavedChanges]
  );

  useEffect(() => {
    if (hasUnsavedChanges && noteContent.trim()) {
      debouncedSave(noteContent);
    }
    return () => {
      debouncedSave.cancel();
    };
  }, [noteContent, hasUnsavedChanges, debouncedSave]);

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const content = e.target.value;
    setNoteContent(content);
    
    // Check if content has actually changed from saved version
    const savedContent = recipe.user_note?.content || '';
    setHasUnsavedChanges(content !== savedContent);
  };

  const handleSaveClick = () => {
    if (noteContent.trim()) {
      saveNoteMutation.mutate(noteContent.trim());
    }
  };

  const handleDeleteClick = () => {
    if (window.confirm('Are you sure you want to delete this note?')) {
      deleteNoteMutation.mutate();
    }
  };

  const handleClearClick = () => {
    setNoteContent('');
    setHasUnsavedChanges(recipe.user_note?.content ? true : false);
  };

  const characterCount = noteContent.length;
  const characterLimit = 1000;
  const isOverLimit = characterCount > characterLimit;

  return (
    <div className="bg-white rounded-xl shadow-sm border mb-6" style={{borderColor: '#e8d7cf'}}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-6 text-left flex items-center justify-between hover:bg-gray-50 rounded-t-xl transition-colors"
      >
        <div className="flex items-center space-x-3">
          <svg className="h-5 w-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          <h3 className="text-xl font-bold text-text-primary">{isOwnRecipe ? 'My Notes' : 'Author Notes'}</h3>
          {recipe.user_note && (
            <span className="px-2 py-1 text-xs bg-accent/10 text-accent rounded-full">
              Has note
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {hasUnsavedChanges && (
            <span className="text-xs text-amber-600 font-medium">Unsaved changes</span>
          )}
          {isSaving && (
            <svg className="animate-spin h-4 w-4 text-accent" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          )}
          <svg 
            className={`h-5 w-5 text-text-secondary transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="px-6 pb-6">
          <div className="space-y-4">
            {isOwnRecipe ? (
              // Owner view: Editable textarea
              <>
                <div>
                  <textarea
                    value={noteContent}
                    onChange={handleContentChange}
                    placeholder="Add your personal notes about this recipe... cooking tips, modifications, memories, or anything else you'd like to remember."
                    rows={6}
                    className={`w-full px-4 py-3 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent transition-colors ${
                      isOverLimit ? 'border-red-300 focus:border-red-500 focus:ring-red-200' : 'border-gray-300'
                    }`}
                    style={{borderColor: isOverLimit ? '#ef4444' : '#e8d7cf'}}
                    disabled={isSaving}
                  />
                  
                  {/* Character counter */}
                  <div className="flex justify-between items-center mt-2">
                    <div className="text-xs text-text-secondary">
                      Auto-saves as you type
                    </div>
                    <div className={`text-xs ${isOverLimit ? 'text-red-500 font-medium' : 'text-text-secondary'}`}>
                      {characterCount}/{characterLimit} characters
                    </div>
                  </div>
                  
                  {isOverLimit && (
                    <p className="text-xs text-red-500 mt-1">
                      Note is too long. Please reduce by {characterCount - characterLimit} characters.
                    </p>
                  )}
                </div>

                {/* Action buttons for owners */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={handleSaveClick}
                      disabled={isSaving || !noteContent.trim() || isOverLimit || !hasUnsavedChanges}
                      className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium transition-colors hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSaving ? 'Saving...' : 'Save Note'}
                    </button>
                    
                    {noteContent && (
                      <button
                        onClick={handleClearClick}
                        disabled={isSaving}
                        className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium transition-colors hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  {recipe.user_note && (
                    <button
                      onClick={handleDeleteClick}
                      disabled={isSaving}
                      className="px-4 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium transition-colors hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Delete Note
                    </button>
                  )}
                </div>
              </>
            ) : (
              // Non-owner view: Read-only display
              <div className="bg-gray-50 rounded-lg p-4 border" style={{borderColor: '#e8d7cf'}}>
                <div className="text-text-primary whitespace-pre-wrap">
                  {recipe.user_note?.content || 'No notes from the recipe author.'}
                </div>
                <div className="text-xs text-text-secondary mt-2">
                  Author's notes
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Debounce utility function
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): T & { cancel: () => void } {
  let timeout: NodeJS.Timeout | null = null;
  
  const debounced = ((...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => func(...args), wait);
  }) as T & { cancel: () => void };
  
  debounced.cancel = () => {
    if (timeout) {
      clearTimeout(timeout);
      timeout = null;
    }
  };
  
  return debounced;
}

export { NotesSection };