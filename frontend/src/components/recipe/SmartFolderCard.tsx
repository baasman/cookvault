import React from 'react';
import { Link } from 'react-router-dom';
import type { SmartFolder } from '../../services/smartFoldersApi';

interface SmartFolderCardProps {
  folder: SmartFolder;
}

const SmartFolderCard: React.FC<SmartFolderCardProps> = ({ folder }) => {
  return (
    <Link to={`/smart-folders/${folder.id}`}>
      <div className="group bg-white rounded-xl shadow-sm border transition-all duration-200 hover:shadow-md hover:border-accent/20 overflow-hidden" style={{ borderColor: '#e8d7cf' }}>
        {/* Smart Folder Cover */}
        <div className="aspect-video bg-gradient-to-br from-blue-50 to-indigo-100 relative overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <svg className="h-12 w-12 text-indigo-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <p className="text-xs text-indigo-400 font-medium">Smart Folder</p>
            </div>
          </div>

          {/* Recipe count badge */}
          <div className="absolute top-3 right-3">
            <div className="px-2 py-1 text-xs font-medium bg-indigo-500 text-white rounded-full">
              {folder.recipe_count ?? 0} recipe{folder.recipe_count !== 1 ? 's' : ''}
            </div>
          </div>

          {/* Smart badge */}
          <div className="absolute top-3 left-3">
            <div className="px-2 py-1 text-xs font-medium bg-indigo-100 text-indigo-700 rounded-full flex items-center gap-1">
              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Auto
            </div>
          </div>
        </div>

        {/* Folder Content */}
        <div className="p-4">
          <h3 className="text-lg font-semibold text-text-primary group-hover:text-accent transition-colors line-clamp-2 mb-2">
            {folder.name}
          </h3>

          {folder.description && (
            <p className="text-sm text-text-secondary line-clamp-2 mb-3">
              {folder.description}
            </p>
          )}

          {/* Rule summary */}
          <div className="text-xs text-text-secondary">
            {folder.rules.conditions.length} rule{folder.rules.conditions.length !== 1 ? 's' : ''} ({folder.rules.match === 'all' ? 'match all' : 'match any'})
          </div>
        </div>
      </div>
    </Link>
  );
};

export { SmartFolderCard };
