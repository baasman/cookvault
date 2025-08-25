import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recipesApi } from '../../services/recipesApi';
import { useAuth } from '../../contexts/AuthContext';
import type { Recipe, RecipeComment } from '../../types';
import toast from 'react-hot-toast';

interface CommentsSectionProps {
  recipe: Recipe;
}

interface CommentItemProps {
  comment: RecipeComment;
  recipeId: number;
  currentUserId?: string;
  onEdit: (commentId: number, content: string) => void;
  onDelete: (commentId: number) => void;
}

const CommentItem: React.FC<CommentItemProps> = ({ 
  comment, 
  currentUserId, 
  onEdit, 
  onDelete 
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);
  const [isLoading, setIsLoading] = useState(false);

  const isOwnComment = currentUserId && comment.user_id === parseInt(currentUserId);
  const displayName = comment.user 
    ? `${comment.user.first_name || comment.user.username} ${comment.user.last_name || ''}`.trim()
    : 'Unknown User';

  const handleSave = async () => {
    if (editContent.trim() === comment.content) {
      setIsEditing(false);
      return;
    }

    setIsLoading(true);
    try {
      await onEdit(comment.id, editContent.trim());
      setIsEditing(false);
      toast.success('Comment updated');
    } catch (error) {
      toast.error('Failed to update comment');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setEditContent(comment.content);
    setIsEditing(false);
  };

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this comment?')) {
      try {
        await onDelete(comment.id);
        toast.success('Comment deleted');
      } catch (error) {
        toast.error('Failed to delete comment');
      }
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${diffInHours}h ago`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      if (diffInDays < 7) {
        return `${diffInDays}d ago`;
      } else {
        return date.toLocaleDateString();
      }
    }
  };

  return (
    <div className="border-b border-gray-200 pb-4 mb-4 last:border-b-0 last:mb-0">
      <div className="flex items-start space-x-3">
        {/* Avatar placeholder */}
        <div className="w-10 h-10 bg-accent rounded-full flex items-center justify-center flex-shrink-0">
          <span className="text-white text-sm font-semibold">
            {displayName.charAt(0).toUpperCase()}
          </span>
        </div>
        
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs text-text-secondary">Posted by</span>
              <span className="font-semibold text-text-primary">{displayName}</span>
              <span className="text-xs text-text-secondary">•</span>
              <span 
                className="text-xs text-text-secondary hover:text-text-primary cursor-help" 
                title={new Date(comment.created_at).toLocaleString()}
              >
                {formatDate(comment.created_at)}
              </span>
              {comment.updated_at !== comment.created_at && (
                <span className="text-xs text-text-secondary">(edited)</span>
              )}
            </div>
            {isOwnComment && !isEditing && (
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setIsEditing(true)}
                  className="text-xs text-accent hover:text-accent-hover transition-colors"
                >
                  Edit
                </button>
                <span className="text-gray-300">•</span>
                <button
                  onClick={handleDelete}
                  className="text-xs text-red-600 hover:text-red-700 transition-colors"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
          
          {/* Content */}
          {isEditing ? (
            <div className="space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent text-sm"
                rows={3}
                maxLength={500}
                disabled={isLoading}
              />
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary">
                  {editContent.length}/500 characters
                </span>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleCancel}
                    className="px-3 py-1 text-xs text-gray-600 hover:text-gray-800 transition-colors"
                    disabled={isLoading}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    className="px-3 py-1 bg-accent text-white rounded text-xs font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
                    disabled={isLoading || !editContent.trim() || editContent.length > 500}
                  >
                    {isLoading ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg p-3 mt-1">
              <p className="text-text-primary text-sm leading-relaxed whitespace-pre-wrap">
                {comment.content}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const CommentsSection: React.FC<CommentsSectionProps> = ({ recipe }) => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [isExpanded, setIsExpanded] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Only fetch comments if user is authenticated
  const { data: commentsData, isLoading } = useQuery({
    queryKey: ['recipe-comments', recipe.id, currentPage],
    queryFn: () => recipesApi.getRecipeComments(recipe.id, { page: currentPage }),
    enabled: !!user, // Only run query when user is authenticated
  });

  // Auto-expand if there are comments (but allow manual collapse)
  React.useEffect(() => {
    if (commentsData && commentsData.total > 0 && !isExpanded) {
      setIsExpanded(true);
    }
  }, [commentsData, isExpanded]);

  // Create comment mutation
  const createCommentMutation = useMutation({
    mutationFn: (content: string) => recipesApi.createComment(recipe.id, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe-comments', recipe.id] });
      setNewComment('');
      toast.success('Comment added');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to add comment');
    },
  });

  // Update comment mutation
  const updateCommentMutation = useMutation({
    mutationFn: ({ commentId, content }: { commentId: number; content: string }) => 
      recipesApi.updateComment(recipe.id, commentId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe-comments', recipe.id] });
    },
  });

  // Delete comment mutation
  const deleteCommentMutation = useMutation({
    mutationFn: (commentId: number) => recipesApi.deleteComment(recipe.id, commentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipe-comments', recipe.id] });
    },
  });

  const handleSubmitComment = async () => {
    if (!newComment.trim()) return;
    createCommentMutation.mutate(newComment.trim());
  };

  const handleEditComment = async (commentId: number, content: string) => {
    updateCommentMutation.mutate({ commentId, content });
  };

  const handleDeleteComment = async (commentId: number) => {
    deleteCommentMutation.mutate(commentId);
  };

  const handleLoadMore = () => {
    if (commentsData?.has_next) {
      setCurrentPage(prev => prev + 1);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border mb-6" style={{borderColor: '#e8d7cf'}}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-6 text-left flex items-center justify-between hover:bg-gray-50 rounded-t-xl transition-colors"
      >
        <div className="flex items-center space-x-3">
          <svg className="h-5 w-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <h3 className="text-xl font-bold text-text-primary">Comments</h3>
          {commentsData && commentsData.total > 0 && (
            <span className="px-2 py-1 text-xs bg-accent/10 text-accent rounded-full">
              {commentsData.total}
            </span>
          )}
        </div>
        <svg 
          className={`h-5 w-5 text-text-secondary transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="px-6 pb-6">
          {/* New comment form - only for authenticated users */}
          {user && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center space-x-2 mb-3">
                <div className="w-8 h-8 bg-accent rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-sm font-semibold">
                    {user.name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <span className="text-sm text-text-secondary">
                  Commenting as <span className="font-medium text-text-primary">{user.name}</span>
                </span>
              </div>
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Share your thoughts about this recipe..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
                maxLength={500}
                disabled={createCommentMutation.isPending}
              />
              <div className="flex items-center justify-between mt-3">
                <span className="text-xs text-text-secondary">
                  {newComment.length}/500 characters
                </span>
                <button
                  onClick={handleSubmitComment}
                  className="px-4 py-2 bg-accent text-black rounded-lg text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={createCommentMutation.isPending || !newComment.trim() || newComment.length > 500}
                >
                  {createCommentMutation.isPending ? 'Posting...' : 'Post Comment'}
                </button>
              </div>
            </div>
          )}

          {/* Login prompt for unauthenticated users */}
          {!user && (
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg text-center">
              <p className="text-blue-700 mb-3">
                <a href="/login" className="font-medium text-blue-800 hover:underline">
                  Sign in
                </a> or <a href="/register" className="font-medium text-blue-800 hover:underline">
                  create an account
                </a> to join the conversation!
              </p>
            </div>
          )}

          {/* Comments list */}
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
            </div>
          ) : commentsData && commentsData.comments.length > 0 ? (
            <div className="space-y-4">
              {commentsData.comments.map((comment) => (
                <CommentItem
                  key={comment.id}
                  comment={comment}
                  recipeId={recipe.id}
                  currentUserId={user?.id}
                  onEdit={handleEditComment}
                  onDelete={handleDeleteComment}
                />
              ))}
              
              {/* Load more button */}
              {commentsData.has_next && (
                <div className="text-center pt-4">
                  <button
                    onClick={handleLoadMore}
                    className="px-4 py-2 text-sm text-accent hover:text-accent-hover transition-colors"
                  >
                    Load more comments
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-text-secondary">
              <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p>No comments yet</p>
              {user && <p className="text-sm mt-1">Be the first to share your thoughts!</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export { CommentsSection };