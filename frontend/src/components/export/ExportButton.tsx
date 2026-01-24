import React, { useState, useEffect } from 'react';
import { DocumentArrowDownIcon } from '@heroicons/react/24/outline';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';
import toast from 'react-hot-toast';
import { getApiUrl } from '../../utils/getApiUrl';
import { apiFetch } from '../../utils/apiInterceptor';
import { Button } from '../ui';
import { isNativePlatform, isIOS } from '../../utils/platform';

interface ExportButtonProps {
  type: 'recipe' | 'cookbook' | 'collection';
  recipeId?: number;
  cookbookId?: number;
  recipeIds?: number[];
  collectionTitle?: string;
  className?: string;
  buttonText?: string;
  showOptions?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

interface ExportOptions {
  template: string;
  profile: string;
  pageSize: string;
  includeImages: boolean;
  includeNotes: boolean;
  includeToc: boolean;
  includeIndex: boolean;
}

export const ExportButton: React.FC<ExportButtonProps> = ({
  type,
  recipeId,
  cookbookId,
  recipeIds = [],
  collectionTitle = 'My Recipe Collection',
  className = '',
  buttonText = 'Download',
  showOptions = false,
  size = 'sm'
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // Load saved preferences from localStorage
  const loadSavedPreferences = (): ExportOptions => {
    try {
      const savedTemplate = localStorage.getItem('cookbook_export_template');
      const savedProfile = localStorage.getItem('cookbook_export_profile');
      const savedPageSize = localStorage.getItem('cookbook_export_page_size');

      return {
        template: savedTemplate || 'modern',
        profile: savedProfile || 'digital',
        pageSize: savedPageSize || 'letter',
        includeImages: true,
        includeNotes: true,
        includeToc: true,
        includeIndex: false
      };
    } catch {
      return {
        template: 'modern',
        profile: 'digital',
        pageSize: 'letter',
        includeImages: true,
        includeNotes: true,
        includeToc: true,
        includeIndex: false
      };
    }
  };

  const [exportOptions, setExportOptions] = useState<ExportOptions>(loadSavedPreferences());

  // Save preferences to localStorage when they change
  useEffect(() => {
    try {
      localStorage.setItem('cookbook_export_template', exportOptions.template);
      localStorage.setItem('cookbook_export_profile', exportOptions.profile);
      localStorage.setItem('cookbook_export_page_size', exportOptions.pageSize);
    } catch (error) {
      console.warn('Failed to save export preferences:', error);
    }
  }, [exportOptions.template, exportOptions.profile, exportOptions.pageSize]);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      let blob: Blob;
      let filename: string;

      if (type === 'recipe' && recipeId) {
        const response = await apiFetch(
          `${getApiUrl()}/recipes/${recipeId}/export/pdf?` + new URLSearchParams({
            template: exportOptions.template,
            profile: exportOptions.profile,
            page_size: exportOptions.pageSize,
            include_images: String(exportOptions.includeImages),
            include_notes: String(exportOptions.includeNotes)
          }),
          {
            method: 'GET',
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
        const response = await apiFetch(
          `${getApiUrl()}/cookbooks/${cookbookId}/export/pdf?` + new URLSearchParams({
            template: exportOptions.template,
            profile: exportOptions.profile,
            page_size: exportOptions.pageSize,
            include_images: String(exportOptions.includeImages),
            include_notes: String(exportOptions.includeNotes),
            include_toc: String(exportOptions.includeToc),
            include_index: String(exportOptions.includeIndex)
          }),
          {
            method: 'GET',
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
        const response = await apiFetch(`${getApiUrl()}/recipes/export/pdf`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/pdf'
          },
          body: JSON.stringify({
            recipe_ids: recipeIds,
            title: collectionTitle,
            template: exportOptions.template,
            profile: exportOptions.profile,
            page_size: exportOptions.pageSize,
            include_images: exportOptions.includeImages,
            include_notes: exportOptions.includeNotes,
            include_toc: exportOptions.includeToc,
            include_index: exportOptions.includeIndex
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

      // Handle download based on platform
      if (isNativePlatform() && isIOS()) {
        // iOS: Write to file and share via native share sheet
        try {
          toast.loading('Preparing PDF...', { id: 'pdf-export' });

          // Convert blob to base64
          const reader = new FileReader();
          const base64Promise = new Promise<string>((resolve, reject) => {
            reader.onloadend = () => {
              const base64 = reader.result as string;
              // Remove data URL prefix (e.g., "data:application/pdf;base64,")
              const base64Data = base64.split(',')[1];
              resolve(base64Data);
            };
            reader.onerror = reject;
          });
          reader.readAsDataURL(blob);
          const base64Data = await base64Promise;

          // Write to a temporary file
          const result = await Filesystem.writeFile({
            path: filename,
            data: base64Data,
            directory: Directory.Cache,
          });

          toast.dismiss('pdf-export');

          // Share the file - this opens the iOS share sheet
          await Share.share({
            title: filename,
            url: result.uri,
            dialogTitle: 'Save or Share PDF',
          });
        } catch (err) {
          console.error('iOS export failed:', err);
          toast.error('Failed to export PDF. Please try again.', { id: 'pdf-export' });
        }
      } else {
        // Web/Android: Use standard download approach
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }

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
      <Button
        onClick={handleQuickExport}
        disabled={isExporting}
        variant="primary"
        size={size}
        className={className}
      >
        <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
        {isExporting ? 'Downloading...' : buttonText}
      </Button>

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
  options: ExportOptions;
  onChange: (options: ExportOptions) => void;
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
  const templateDescriptions: Record<string, string> = {
    classic: 'Traditional professional layout',
    modern: 'Clean, contemporary design with ample white space',
    book: 'Elegant two-column layout'
  };

  const profileDescriptions: Record<string, string> = {
    digital: 'Optimized for screens (85% quality, RGB, smaller file size)',
    home_print: 'Optimized for home printers (90% quality, RGB)',
    professional_print: 'Print-ready with CMYK colors (95% quality, crop marks, bleed)'
  };

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Export Options</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Template Style</label>
            <select
              value={options.template}
              onChange={(e) => onChange({ ...options, template: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              <option value="modern">Modern Minimalist</option>
              <option value="classic">Classic</option>
              <option value="book">Book Style</option>
            </select>
            <p className="mt-1 text-xs text-gray-500">
              {templateDescriptions[options.template]}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Output Profile</label>
            <select
              value={options.profile}
              onChange={(e) => onChange({ ...options, profile: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              <option value="digital">Digital Viewing</option>
              <option value="home_print">Home Printing</option>
              <option value="professional_print">Professional Print Service</option>
            </select>
            <p className="mt-1 text-xs text-gray-500">
              {profileDescriptions[options.profile]}
            </p>
          </div>

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
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent"
          >
            Cancel
          </button>
          <button
            onClick={onExport}
            disabled={isExporting}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: isExporting ? '#9ca3af' : '#f15f1c' }}
          >
            {isExporting ? 'Downloading...' : 'Download'}
          </button>
        </div>
      </div>
    </div>
  );
};