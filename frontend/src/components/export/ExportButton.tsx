import React, { useState } from 'react';
import { DocumentArrowDownIcon } from '@heroicons/react/24/outline';
import { getApiUrl } from '../../utils/getApiUrl';

interface ExportButtonProps {
  type: 'recipe' | 'cookbook' | 'collection';
  recipeId?: number;
  cookbookId?: number;
  recipeIds?: number[];
  collectionTitle?: string;
  className?: string;
  buttonText?: string;
  showOptions?: boolean;
}

export const ExportButton: React.FC<ExportButtonProps> = ({
  type,
  recipeId,
  cookbookId,
  recipeIds = [],
  collectionTitle = 'My Recipe Collection',
  className = '',
  buttonText = 'Export PDF',
  showOptions = false
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [exportOptions, setExportOptions] = useState({
    template: 'classic',
    pageSize: 'letter',
    includeImages: true,
    includeNotes: true,
    includeToc: true,
    includeIndex: false
  });

  const handleExport = async () => {
    setIsExporting(true);
    try {
      let blob: Blob;
      let filename: string;

      if (type === 'recipe' && recipeId) {
        const response = await fetch(
          `${getApiUrl()}/recipes/${recipeId}/export/pdf?` + new URLSearchParams({
            template: exportOptions.template,
            page_size: exportOptions.pageSize,
            include_images: String(exportOptions.includeImages),
            include_notes: String(exportOptions.includeNotes)
          }),
          {
            method: 'GET',
            credentials: 'include',
            headers: {
              'Accept': 'application/pdf'
            }
          }
        );

        if (!response.ok) {
          throw new Error('Failed to export PDF');
        }

        blob = await response.blob();
        
        // Extract filename from Content-Disposition header if available
        const contentDisposition = response.headers.get('Content-Disposition');
        filename = 'recipe.pdf';
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="(.+)"/);
          if (match) {
            filename = match[1];
          }
        }
      } else if (type === 'cookbook' && cookbookId) {
        const response = await fetch(
          `${getApiUrl()}/cookbooks/${cookbookId}/export/pdf?` + new URLSearchParams({
            template: exportOptions.template,
            page_size: exportOptions.pageSize,
            include_images: String(exportOptions.includeImages),
            include_notes: String(exportOptions.includeNotes),
            include_toc: String(exportOptions.includeToc),
            include_index: String(exportOptions.includeIndex)
          }),
          {
            method: 'GET',
            credentials: 'include',
            headers: {
              'Accept': 'application/pdf'
            }
          }
        );

        if (!response.ok) {
          throw new Error('Failed to export PDF');
        }

        blob = await response.blob();
        filename = 'cookbook.pdf';
        
        const contentDisposition = response.headers.get('Content-Disposition');
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="(.+)"/);
          if (match) {
            filename = match[1];
          }
        }
      } else if (type === 'collection' && recipeIds.length > 0) {
        const response = await fetch(`${getApiUrl()}/recipes/export/pdf`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/pdf'
          },
          body: JSON.stringify({
            recipe_ids: recipeIds,
            title: collectionTitle,
            ...exportOptions
          })
        });

        if (!response.ok) {
          throw new Error('Failed to export PDF');
        }

        blob = await response.blob();
        filename = 'recipe_collection.pdf';
        
        const contentDisposition = response.headers.get('Content-Disposition');
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="(.+)"/);
          if (match) {
            filename = match[1];
          }
        }
      } else {
        throw new Error('Invalid export configuration');
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      setShowModal(false);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export PDF. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleQuickExport = () => {
    if (showOptions) {
      setShowModal(true);
    } else {
      handleExport();
    }
  };

  return (
    <>
      <button
        onClick={handleQuickExport}
        disabled={isExporting}
        className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      >
        <DocumentArrowDownIcon className="h-5 w-5 mr-2" />
        {isExporting ? 'Exporting...' : buttonText}
      </button>

      {showModal && (
        <ExportOptionsModal
          options={exportOptions}
          onChange={setExportOptions}
          onExport={handleExport}
          onClose={() => setShowModal(false)}
          isExporting={isExporting}
          type={type}
        />
      )}
    </>
  );
};

interface ExportOptionsModalProps {
  options: any;
  onChange: (options: any) => void;
  onExport: () => void;
  onClose: () => void;
  isExporting: boolean;
  type: 'recipe' | 'cookbook' | 'collection';
}

const ExportOptionsModal: React.FC<ExportOptionsModalProps> = ({
  options,
  onChange,
  onExport,
  onClose,
  isExporting,
  type
}) => {
  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Export Options</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Page Size</label>
            <select
              value={options.pageSize}
              onChange={(e) => onChange({ ...options, pageSize: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              <option value="letter">Letter (8.5" × 11")</option>
              <option value="a4">A4 (210mm × 297mm)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Include</label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={options.includeImages}
                  onChange={(e) => onChange({ ...options, includeImages: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Recipe Images</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={options.includeNotes}
                  onChange={(e) => onChange({ ...options, includeNotes: e.target.checked })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Recipe Notes</span>
              </label>

              {(type === 'cookbook' || type === 'collection') && (
                <>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={options.includeToc}
                      onChange={(e) => onChange({ ...options, includeToc: e.target.checked })}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">Table of Contents</span>
                  </label>
                  
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={options.includeIndex}
                      onChange={(e) => onChange({ ...options, includeIndex: e.target.checked })}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">Ingredient Index</span>
                  </label>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Cancel
          </button>
          <button
            onClick={onExport}
            disabled={isExporting}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isExporting ? 'Exporting...' : 'Export PDF'}
          </button>
        </div>
      </div>
    </div>
  );
};