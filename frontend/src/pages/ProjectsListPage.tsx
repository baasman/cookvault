import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { useAuth } from '../contexts/AuthContext';
import { BooksSubNav } from '../components/navigation/BooksSubNav';
import { bookProjectsApi } from '../services/bookProjectsApi';
import type { BookProject, ProjectType } from '../types';

const PROJECT_TYPE_LABEL: Record<ProjectType, string> = {
  wedding: 'Wedding',
  anniversary: 'Anniversary',
  heirloom: 'Family Heirloom',
  memorial: 'In Memory',
  holiday: 'Holiday',
  general: 'General',
};

export const ProjectsListPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const { data: projects, isLoading, error, refetch } = useQuery({
    queryKey: ['book-projects'],
    queryFn: () => bookProjectsApi.list(),
    enabled: isAuthenticated,
    staleTime: 60 * 1000,
  });

  if (authLoading) {
    return null;
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <h1 className="text-3xl font-bold mb-3" style={{ color: '#1c120d' }}>
          My Books
        </h1>
        <p className="mb-6" style={{ color: '#9b644b' }}>
          Sign in to create a collaborative cookbook and invite family and friends to contribute.
        </p>
        <button
          onClick={() => navigate('/login')}
          className="px-6 py-2 text-white rounded-lg hover:opacity-90 transition-opacity"
          style={{ backgroundColor: '#f15f1c' }}
        >
          Sign in
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <BooksSubNav active="projects" />
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: '#1c120d' }}>
            My Books
          </h1>
          <p className="mt-1 text-sm" style={{ color: '#9b644b' }}>
            Collaborative cookbooks — collect recipes from family and friends, export a PDF
            you can print as a gift.
          </p>
        </div>
        <button
          onClick={() => navigate('/projects/create')}
          className="px-4 py-2 text-white rounded-lg hover:opacity-90 transition-opacity whitespace-nowrap"
          style={{ backgroundColor: '#f15f1c' }}
        >
          New book
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-20 rounded-lg animate-pulse"
              style={{ backgroundColor: '#f6efe6' }}
            />
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="mb-3" style={{ color: '#9b644b' }}>
            Couldn't load your books.
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 text-white rounded-lg"
            style={{ backgroundColor: '#f15f1c' }}
          >
            Retry
          </button>
        </div>
      ) : !projects || projects.length === 0 ? (
        <EmptyState onCreate={() => navigate('/projects/create')} />
      ) : (
        <ul className="space-y-3">
          {projects.map((p) => (
            <ProjectListItem key={p.id} project={p} onClick={() => navigate(`/projects/${p.id}`)} />
          ))}
        </ul>
      )}
    </div>
  );
};

const ProjectListItem: React.FC<{ project: BookProject; onClick: () => void }> = ({
  project,
  onClick,
}) => {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className="w-full text-left px-5 py-4 rounded-lg border hover:opacity-90 transition-opacity"
        style={{ backgroundColor: '#fffbf5', borderColor: '#e8dccf' }}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="font-semibold truncate" style={{ color: '#1c120d' }}>
              {project.title}
            </h2>
            {project.honorees && project.honorees.length > 0 && (
              <p className="text-sm truncate" style={{ color: '#6b5a52' }}>
                For {project.honorees.join(' & ')}
              </p>
            )}
            <div className="flex items-center gap-3 mt-1 text-xs" style={{ color: '#9b644b' }}>
              <span>{PROJECT_TYPE_LABEL[project.project_type] ?? project.project_type}</span>
              <span>•</span>
              <span>
                {project.recipe_count ?? 0}{' '}
                {(project.recipe_count ?? 0) === 1 ? 'recipe' : 'recipes'}
              </span>
              <span>•</span>
              <span>{project.status}</span>
            </div>
          </div>
          {project.submission_deadline && (
            <div className="text-xs text-right" style={{ color: '#6b5a52' }}>
              <div>Deadline</div>
              <div className="font-medium">{project.submission_deadline}</div>
            </div>
          )}
        </div>
      </button>
    </li>
  );
};

const EmptyState: React.FC<{ onCreate: () => void }> = ({ onCreate }) => (
  <div
    className="text-center py-16 px-4 rounded-lg"
    style={{ backgroundColor: '#fffbf5', border: '1px dashed #d4c2b3' }}
  >
    <h2 className="text-xl font-semibold mb-2" style={{ color: '#1c120d' }}>
      Start your first book
    </h2>
    <p className="max-w-md mx-auto mb-5 text-sm" style={{ color: '#6b5a52' }}>
      Create a project for a wedding, an anniversary, or a family heirloom cookbook, share the
      link with everyone, and collect recipes — without anyone needing an account.
    </p>
    <button
      onClick={onCreate}
      className="px-5 py-2 text-white rounded-lg"
      style={{ backgroundColor: '#f15f1c' }}
    >
      Create a project
    </button>
  </div>
);

export default ProjectsListPage;

