import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useAuth } from '../contexts/AuthContext';
import { bookProjectsApi } from '../services/bookProjectsApi';
import type { ProjectType } from '../types';

const PROJECT_TYPES: { value: ProjectType; label: string; eyebrow: string }[] = [
  { value: 'wedding', label: 'Wedding gift', eyebrow: 'A gift from the guests' },
  { value: 'anniversary', label: 'Anniversary', eyebrow: 'Marking the milestone' },
  { value: 'heirloom', label: 'Family heirloom', eyebrow: 'Preserve the recipes' },
  { value: 'memorial', label: 'In memory', eyebrow: 'A tribute cookbook' },
  { value: 'holiday', label: 'Holiday', eyebrow: 'Recipes from the season' },
  { value: 'general', label: 'Something else', eyebrow: 'A general collection' },
];

export const CreateProjectPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [projectType, setProjectType] = useState<ProjectType>('wedding');
  const [title, setTitle] = useState('');
  const [subtitle, setSubtitle] = useState('');
  const [honoreesRaw, setHonoreesRaw] = useState('');
  const [occasionDate, setOccasionDate] = useState('');
  const [submissionDeadline, setSubmissionDeadline] = useState('');
  const [dedication, setDedication] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => {
      const honorees = honoreesRaw
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      return bookProjectsApi.create({
        title: title.trim(),
        project_type: projectType,
        subtitle: subtitle.trim() || undefined,
        dedication: dedication.trim() || undefined,
        honorees,
        occasion_date: occasionDate || undefined,
        submission_deadline: submissionDeadline || undefined,
      });
    },
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['book-projects'] });
      navigate(`/projects/${project.id}`);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create book');
    },
  });

  if (authLoading) return null;
  if (!isAuthenticated) {
    navigate('/login');
    return null;
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    mutation.mutate();
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <button
        onClick={() => navigate('/projects')}
        className="text-sm mb-4 hover:underline"
        style={{ color: '#9b644b' }}
      >
        ← Back to Books
      </button>
      <h1 className="text-3xl font-bold mb-1" style={{ color: '#1c120d' }}>
        New book
      </h1>
      <p className="text-sm mb-6" style={{ color: '#6b5a52' }}>
        Pick a book type. You can always tweak the cover and copy later.
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section>
          <h2 className="text-sm font-medium mb-2" style={{ color: '#1c120d' }}>
            Book type
          </h2>
          <div className="grid grid-cols-2 gap-2">
            {PROJECT_TYPES.map((opt) => (
              <button
                type="button"
                key={opt.value}
                onClick={() => setProjectType(opt.value)}
                className="text-left px-3 py-3 rounded-lg border transition-colors"
                style={{
                  borderColor: projectType === opt.value ? '#f15f1c' : '#e8dccf',
                  backgroundColor: projectType === opt.value ? '#fff4ed' : '#fffbf5',
                }}
              >
                <div className="font-medium text-sm" style={{ color: '#1c120d' }}>
                  {opt.label}
                </div>
                <div className="text-xs" style={{ color: '#9b644b' }}>
                  {opt.eyebrow}
                </div>
              </button>
            ))}
          </div>
        </section>

        <Field label="Title" required>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Sarah & Maya's Recipe Book"
            className="w-full px-3 py-2 rounded-lg border"
            style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
            required
          />
        </Field>

        <Field label="Subtitle">
          <input
            type="text"
            value={subtitle}
            onChange={(e) => setSubtitle(e.target.value)}
            placeholder="A gift from your guests"
            className="w-full px-3 py-2 rounded-lg border"
            style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
          />
        </Field>

        <Field
          label="Honorees"
          hint="Comma-separated. Used on the cover and in the contributor link copy."
        >
          <input
            type="text"
            value={honoreesRaw}
            onChange={(e) => setHonoreesRaw(e.target.value)}
            placeholder="Sarah, Maya"
            className="w-full px-3 py-2 rounded-lg border"
            style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Occasion date">
            <input
              type="date"
              value={occasionDate}
              onChange={(e) => setOccasionDate(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border"
              style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
            />
          </Field>
          <Field label="Submission deadline">
            <input
              type="date"
              value={submissionDeadline}
              onChange={(e) => setSubmissionDeadline(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border"
              style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
            />
          </Field>
        </div>

        <Field
          label="Dedication"
          hint="Optional. Appears on the inside cover of the printed book."
        >
          <textarea
            value={dedication}
            onChange={(e) => setDedication(e.target.value)}
            rows={3}
            placeholder="For Sarah and Maya — may your kitchen always smell of garlic."
            className="w-full px-3 py-2 rounded-lg border"
            style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
          />
        </Field>

        {error && (
          <div
            className="px-3 py-2 rounded text-sm"
            style={{ backgroundColor: '#fef0ea', color: '#9b3a1c' }}
          >
            {error}
          </div>
        )}

        <div className="flex items-center gap-3 justify-end">
          <button
            type="button"
            onClick={() => navigate('/projects')}
            className="px-4 py-2 rounded-lg hover:underline"
            style={{ color: '#6b5a52' }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="px-5 py-2 text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
            style={{ backgroundColor: '#f15f1c' }}
          >
            {mutation.isPending ? 'Creating…' : 'Create book'}
          </button>
        </div>
      </form>
    </div>
  );
};

const Field: React.FC<{
  label: string;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}> = ({ label, required, hint, children }) => (
  <label className="block">
    <span className="block text-sm font-medium mb-1" style={{ color: '#1c120d' }}>
      {label}
      {required && <span style={{ color: '#f15f1c' }}> *</span>}
    </span>
    {hint && (
      <span className="block text-xs mb-2" style={{ color: '#9b644b' }}>
        {hint}
      </span>
    )}
    {children}
  </label>
);

export default CreateProjectPage;
