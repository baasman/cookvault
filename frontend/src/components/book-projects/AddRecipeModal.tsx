import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { bookProjectsApi } from '../../services/bookProjectsApi';

type Mode = 'photo' | 'text' | 'url';

interface Props {
  projectId: number;
  isOpen: boolean;
  onClose: () => void;
  onSubmitted: () => void;
}

export const AddRecipeModal: React.FC<Props> = ({
  projectId,
  isOpen,
  onClose,
  onSubmitted,
}) => {
  const [mode, setMode] = useState<Mode>('text');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setText('');
    setUrl('');
    setFile(null);
    setError(null);
  };

  const close = () => {
    reset();
    onClose();
  };

  const textMutation = useMutation({
    mutationFn: () => bookProjectsApi.submitTextAsOrganizer(projectId, text),
    onSuccess: () => {
      reset();
      onSubmitted();
    },
    onError: (err: Error) => setError(err.message),
  });

  const urlMutation = useMutation({
    mutationFn: () => bookProjectsApi.submitUrlAsOrganizer(projectId, url),
    onSuccess: () => {
      reset();
      onSubmitted();
    },
    onError: (err: Error) => setError(err.message),
  });

  const imageMutation = useMutation({
    mutationFn: () => bookProjectsApi.submitImageAsOrganizer(projectId, file as File),
    onSuccess: () => {
      reset();
      onSubmitted();
    },
    onError: (err: Error) => setError(err.message),
  });

  if (!isOpen) return null;

  const submitting =
    textMutation.isPending || urlMutation.isPending || imageMutation.isPending;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(28, 18, 13, 0.55)' }}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div
        className="max-w-md w-full rounded-lg p-6"
        style={{ backgroundColor: '#fcf9f8' }}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold" style={{ color: '#1c120d' }}>
              Add a recipe
            </h2>
            <p className="text-xs mt-1" style={{ color: '#9b644b' }}>
              This one's from you — it'll appear in the book under your name.
            </p>
          </div>
          <button
            onClick={close}
            className="text-sm hover:opacity-70"
            style={{ color: '#6b5a52' }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="flex gap-1 mb-4 p-1 rounded-lg" style={{ backgroundColor: '#f6efe6' }}>
          {(['text', 'url', 'photo'] as Mode[]).map((m) => {
            const active = mode === m;
            return (
              <button
                key={m}
                onClick={() => {
                  setMode(m);
                  setError(null);
                }}
                className="flex-1 py-2 text-sm rounded-md transition-colors capitalize"
                style={{
                  backgroundColor: active ? '#fffbf5' : 'transparent',
                  color: active ? '#1c120d' : '#6b5a52',
                  fontWeight: active ? 600 : 400,
                  border: active ? '1px solid #e8dccf' : '1px solid transparent',
                }}
              >
                {m}
              </button>
            );
          })}
        </div>

        {mode === 'text' && (
          <div>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              placeholder="Paste or type the recipe here…"
              className="w-full px-3 py-2 rounded border text-sm mb-3"
              style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
            />
            <button
              onClick={() => {
                if (!text.trim()) {
                  setError('Please enter some recipe text.');
                  return;
                }
                setError(null);
                textMutation.mutate();
              }}
              disabled={submitting}
              className="w-full py-2.5 text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
              style={{ backgroundColor: '#f15f1c' }}
            >
              {textMutation.isPending ? 'Submitting…' : 'Add recipe'}
            </button>
          </div>
        )}

        {mode === 'url' && (
          <div>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/recipe"
              className="w-full px-3 py-2 rounded border text-sm mb-3"
              style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
            />
            <button
              onClick={() => {
                if (!url.trim()) {
                  setError('Please paste a URL.');
                  return;
                }
                setError(null);
                urlMutation.mutate();
              }}
              disabled={submitting}
              className="w-full py-2.5 text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
              style={{ backgroundColor: '#f15f1c' }}
            >
              {urlMutation.isPending ? 'Submitting…' : 'Add recipe'}
            </button>
          </div>
        )}

        {mode === 'photo' && (
          <div>
            <label
              className="block w-full px-3 py-6 rounded-lg border-2 border-dashed text-center cursor-pointer mb-3"
              style={{ borderColor: '#d4c2b3', backgroundColor: '#fffbf5' }}
            >
              <input
                type="file"
                accept="image/*"
                capture="environment"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setError(null);
                }}
                className="hidden"
              />
              <div className="text-sm" style={{ color: file ? '#1c120d' : '#9b644b' }}>
                {file ? file.name : 'Tap to choose a photo'}
              </div>
            </label>
            <button
              onClick={() => {
                if (!file) {
                  setError('Please choose a file first.');
                  return;
                }
                setError(null);
                imageMutation.mutate();
              }}
              disabled={!file || submitting}
              className="w-full py-2.5 text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
              style={{ backgroundColor: '#f15f1c' }}
            >
              {imageMutation.isPending ? 'Uploading…' : 'Add recipe'}
            </button>
          </div>
        )}

        {error && (
          <div
            className="mt-3 px-3 py-2 rounded text-sm"
            style={{ backgroundColor: '#fef0ea', color: '#9b3a1c' }}
          >
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default AddRecipeModal;
