import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';

import { bookProjectsApi } from '../services/bookProjectsApi';
import type { ProjectType } from '../types';

type Mode = 'photo' | 'text' | 'url';

interface CopyVariant {
  eyebrow: string;
  intro: (honoreesJoined: string, fallback: string) => string;
}

const PROJECT_TYPE_COPY: Record<ProjectType, CopyVariant> = {
  wedding: {
    eyebrow: 'A wedding cookbook',
    intro: (honorees, fallback) =>
      honorees
        ? `${honorees} are getting married! Submit a favorite recipe — it'll become part of a cookbook gift from everyone they love.`
        : fallback,
  },
  anniversary: {
    eyebrow: 'An anniversary cookbook',
    intro: (honorees, fallback) =>
      honorees
        ? `${honorees} are celebrating an anniversary. Add a recipe to their book.`
        : fallback,
  },
  heirloom: {
    eyebrow: 'A family heirloom',
    intro: (honorees, fallback) =>
      honorees
        ? `Preserving ${honorees}'s recipes. Add one of your favorites so it isn't lost.`
        : fallback || 'A family is preserving their recipes. Contribute one of yours.',
  },
  memorial: {
    eyebrow: 'In loving memory',
    intro: (honorees, fallback) =>
      honorees
        ? `In memory of ${honorees}. Share a recipe that reminds you of them.`
        : fallback,
  },
  holiday: {
    eyebrow: 'A holiday cookbook',
    intro: (_, fallback) =>
      fallback || 'A holiday cookbook is being put together. Contribute a recipe from the season.',
  },
  general: {
    eyebrow: 'A cookbook project',
    intro: (_, fallback) => fallback || 'Submit a recipe to be included in the cookbook.',
  },
};

export const ContributorLandingPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [mode, setMode] = useState<Mode>('photo');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [submittedTitle, setSubmittedTitle] = useState<string | null>(null);

  const {
    data: info,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['public-book-project', token],
    queryFn: () => bookProjectsApi.fetchPublicByToken(token ?? ''),
    enabled: !!token,
    retry: false,
  });

  if (!token) {
    return <ErrorScreen message="Missing share token." />;
  }
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="text-sm" style={{ color: '#9b644b' }}>
          Loading…
        </div>
      </div>
    );
  }
  if (error || !info) {
    return (
      <ErrorScreen
        message={
          (error as Error)?.message ||
          "We couldn't find this link. It may have been revoked or expired."
        }
      />
    );
  }

  const honoreesJoined = (info.project.honorees || []).join(' & ');
  const copy = PROJECT_TYPE_COPY[info.project.project_type] ?? PROJECT_TYPE_COPY.general;
  const introFallback =
    info.project.subtitle || `A cookbook is being collected. Add a recipe.`;
  const introText = copy.intro(honoreesJoined, introFallback);

  if (submittedTitle) {
    return (
      <ThankYouScreen
        title={submittedTitle}
        onSubmitAnother={() => {
          setSubmittedTitle(null);
          setMode('photo');
        }}
      />
    );
  }

  return (
    <div className="min-h-screen px-4 py-8 sm:py-12" style={{ backgroundColor: '#fcf9f8' }}>
      <div className="max-w-md mx-auto">
        <header className="mb-8 text-center">
          <p
            className="text-xs uppercase tracking-widest mb-2"
            style={{ color: '#9b644b' }}
          >
            {copy.eyebrow}
          </p>
          <h1 className="text-2xl font-bold mb-3" style={{ color: '#1c120d' }}>
            {info.project.title}
          </h1>
          <p className="text-sm leading-relaxed" style={{ color: '#3a2d23' }}>
            {introText}
          </p>
        </header>

        <ModeTabs mode={mode} onChange={setMode} />

        <div
          className="rounded-lg border p-4 mb-4"
          style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
        >
          {mode === 'photo' && (
            <PhotoForm
              token={token}
              displayName={displayName}
              email={email}
              onSuccess={(title) => setSubmittedTitle(title || 'Your recipe')}
            />
          )}
          {mode === 'text' && (
            <TextForm
              token={token}
              displayName={displayName}
              email={email}
              onSuccess={(title) => setSubmittedTitle(title || 'Your recipe')}
            />
          )}
          {mode === 'url' && (
            <UrlForm
              token={token}
              displayName={displayName}
              email={email}
              onSuccess={(title) => setSubmittedTitle(title || 'Your recipe')}
            />
          )}
        </div>

        <div
          className="rounded-lg border p-4"
          style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
        >
          <p className="text-xs font-medium mb-2" style={{ color: '#1c120d' }}>
            From whom?
          </p>
          <p className="text-xs mb-3" style={{ color: '#9b644b' }}>
            Optional — used for the attribution in the printed book.
          </p>
          <input
            type="text"
            placeholder="Your name (e.g. Aunt Linda)"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full px-3 py-2 rounded border mb-2 text-sm"
            style={{ borderColor: '#e8dccf', backgroundColor: '#fcf9f8' }}
          />
          <input
            type="email"
            placeholder="Email (optional)"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 rounded border text-sm"
            style={{ borderColor: '#e8dccf', backgroundColor: '#fcf9f8' }}
          />
        </div>

        <p className="mt-6 text-center text-xs" style={{ color: '#9b644b' }}>
          Powered by Cookle
        </p>
      </div>
    </div>
  );
};

const ModeTabs: React.FC<{ mode: Mode; onChange: (m: Mode) => void }> = ({
  mode,
  onChange,
}) => {
  const tabs: { value: Mode; label: string }[] = [
    { value: 'photo', label: 'Photo' },
    { value: 'text', label: 'Text' },
    { value: 'url', label: 'URL' },
  ];
  return (
    <div className="flex gap-1 mb-3 p-1 rounded-lg" style={{ backgroundColor: '#f6efe6' }}>
      {tabs.map((t) => {
        const active = mode === t.value;
        return (
          <button
            key={t.value}
            onClick={() => onChange(t.value)}
            className="flex-1 py-2 text-sm rounded-md transition-colors"
            style={{
              backgroundColor: active ? '#fffbf5' : 'transparent',
              color: active ? '#1c120d' : '#6b5a52',
              fontWeight: active ? 600 : 400,
              border: active ? '1px solid #e8dccf' : '1px solid transparent',
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
};

const PhotoForm: React.FC<{
  token: string;
  displayName: string;
  email: string;
  onSuccess: (title?: string) => void;
}> = ({ token, displayName, email, onSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      bookProjectsApi.submitImageByToken(token, file as File, {
        display_name: displayName || undefined,
        email: email || undefined,
      }),
    onSuccess: () => onSuccess(),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div>
      <p className="text-sm font-medium mb-2" style={{ color: '#1c120d' }}>
        Snap or upload a photo of the recipe
      </p>
      <p className="text-xs mb-3" style={{ color: '#9b644b' }}>
        Handwritten card, printed page, or a screenshot — we'll do the rest.
      </p>
      <label
        className="block w-full px-3 py-4 rounded-lg border-2 border-dashed text-center cursor-pointer mb-3"
        style={{ borderColor: '#d4c2b3', backgroundColor: '#fcf9f8' }}
      >
        <input
          type="file"
          accept="image/*"
          capture="environment"
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            setFile(f);
            setError(null);
          }}
          className="hidden"
        />
        <div className="text-sm" style={{ color: file ? '#1c120d' : '#9b644b' }}>
          {file ? file.name : 'Tap to take a photo or choose a file'}
        </div>
      </label>
      <button
        onClick={() => {
          if (!file) {
            setError('Please choose a file first.');
            return;
          }
          mutation.mutate();
        }}
        disabled={!file || mutation.isPending}
        className="w-full py-2.5 text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
        style={{ backgroundColor: '#f15f1c' }}
      >
        {mutation.isPending ? 'Submitting…' : 'Submit recipe'}
      </button>
      {error && (
        <div
          className="mt-3 px-3 py-2 rounded text-sm"
          style={{ backgroundColor: '#fef0ea', color: '#9b3a1c' }}
        >
          {error}
        </div>
      )}
    </div>
  );
};

const TextForm: React.FC<{
  token: string;
  displayName: string;
  email: string;
  onSuccess: (title?: string) => void;
}> = ({ token, displayName, email, onSuccess }) => {
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      bookProjectsApi.submitTextByToken(token, {
        text,
        display_name: displayName || undefined,
        email: email || undefined,
      }),
    onSuccess: (resp) => onSuccess(resp.submission.title),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div>
      <p className="text-sm font-medium mb-2" style={{ color: '#1c120d' }}>
        Type or paste the recipe
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={8}
        placeholder="Ingredients, instructions, anything — we'll parse it."
        className="w-full px-3 py-2 rounded border text-sm mb-3"
        style={{ borderColor: '#e8dccf', backgroundColor: '#fcf9f8' }}
      />
      <button
        onClick={() => {
          if (!text.trim()) {
            setError('Please enter some recipe text.');
            return;
          }
          setError(null);
          mutation.mutate();
        }}
        disabled={mutation.isPending}
        className="w-full py-2.5 text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
        style={{ backgroundColor: '#f15f1c' }}
      >
        {mutation.isPending ? 'Submitting…' : 'Submit recipe'}
      </button>
      {error && (
        <div
          className="mt-3 px-3 py-2 rounded text-sm"
          style={{ backgroundColor: '#fef0ea', color: '#9b3a1c' }}
        >
          {error}
        </div>
      )}
    </div>
  );
};

const UrlForm: React.FC<{
  token: string;
  displayName: string;
  email: string;
  onSuccess: (title?: string) => void;
}> = ({ token, displayName, email, onSuccess }) => {
  const [url, setUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      bookProjectsApi.submitUrlByToken(token, {
        url,
        display_name: displayName || undefined,
        email: email || undefined,
      }),
    onSuccess: (resp) => onSuccess(resp.submission.title),
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div>
      <p className="text-sm font-medium mb-2" style={{ color: '#1c120d' }}>
        Paste a recipe URL
      </p>
      <input
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://example.com/grandmas-pie"
        className="w-full px-3 py-2 rounded border text-sm mb-3"
        style={{ borderColor: '#e8dccf', backgroundColor: '#fcf9f8' }}
      />
      <button
        onClick={() => {
          if (!url.trim()) {
            setError('Please paste a URL.');
            return;
          }
          setError(null);
          mutation.mutate();
        }}
        disabled={mutation.isPending}
        className="w-full py-2.5 text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
        style={{ backgroundColor: '#f15f1c' }}
      >
        {mutation.isPending ? 'Submitting…' : 'Submit recipe'}
      </button>
      {error && (
        <div
          className="mt-3 px-3 py-2 rounded text-sm"
          style={{ backgroundColor: '#fef0ea', color: '#9b3a1c' }}
        >
          {error}
        </div>
      )}
    </div>
  );
};

const ThankYouScreen: React.FC<{
  title: string;
  onSubmitAnother: () => void;
}> = ({ title, onSubmitAnother }) => (
  <div className="min-h-screen px-4 py-12" style={{ backgroundColor: '#fcf9f8' }}>
    <div className="max-w-md mx-auto text-center">
      <div className="text-3xl mb-4" aria-hidden>
        ✓
      </div>
      <h1 className="text-2xl font-bold mb-2" style={{ color: '#1c120d' }}>
        Thanks!
      </h1>
      <p className="mb-6" style={{ color: '#3a2d23' }}>
        We got "{title}". It'll show up in the organizer's draft of the book.
      </p>
      <button
        onClick={onSubmitAnother}
        className="px-5 py-2 text-white rounded-lg"
        style={{ backgroundColor: '#f15f1c' }}
      >
        Submit another recipe
      </button>
    </div>
  </div>
);

const ErrorScreen: React.FC<{ message: string }> = ({ message }) => (
  <div className="min-h-screen px-4 py-12" style={{ backgroundColor: '#fcf9f8' }}>
    <div className="max-w-md mx-auto text-center">
      <h1 className="text-2xl font-bold mb-3" style={{ color: '#1c120d' }}>
        Hmm.
      </h1>
      <p style={{ color: '#3a2d23' }}>{message}</p>
    </div>
  </div>
);

export default ContributorLandingPage;
