import React, { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Modal, Button } from '../ui';
import { apiFetch } from '../../utils/apiInterceptor';
import { getApiUrl } from '../../utils/getApiUrl';
import toast from 'react-hot-toast';

interface ImportRecipesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ImportPreview {
  recipeCount: number;
  titles: string[];
}

interface ImportResult {
  imported: number;
  recipe_ids: number[];
  errors: Array<{ index: number; title: string; reason: string }>;
}

const ImportRecipesModal: React.FC<ImportRecipesModalProps> = ({ isOpen, onClose }) => {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const importMutation = useMutation({
    mutationFn: async (file: File): Promise<ImportResult> => {
      const formData = new FormData();
      formData.append('file', file);
      const response = await apiFetch(`${getApiUrl()}/recipes/import/json`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Import failed');
      }
      return data;
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      if (result.imported > 0) {
        toast.success(`Imported ${result.imported} recipe${result.imported !== 1 ? 's' : ''}`);
      }
      if (result.errors.length > 0) {
        toast.error(`${result.errors.length} recipe${result.errors.length !== 1 ? 's' : ''} failed to import`);
      }
      handleClose();
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to import recipes');
    },
  });

  const handleFileSelect = (selectedFile: File) => {
    setParseError(null);
    setPreview(null);

    if (!selectedFile.name.endsWith('.json')) {
      setParseError('Please select a .json file');
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setParseError('File is too large (max 10MB)');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        if (!data.recipes || !Array.isArray(data.recipes)) {
          setParseError('Invalid format: missing "recipes" array');
          return;
        }
        if (data.recipes.length === 0) {
          setParseError('No recipes found in file');
          return;
        }
        setFile(selectedFile);
        setPreview({
          recipeCount: data.recipes.length,
          titles: data.recipes.slice(0, 10).map((r: { title?: string }) => r.title || 'Untitled'),
        });
      } catch {
        setParseError('Invalid JSON file');
      }
    };
    reader.readAsText(selectedFile);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) handleFileSelect(droppedFile);
  };

  const handleClose = () => {
    setFile(null);
    setPreview(null);
    setParseError(null);
    setDragOver(false);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="md">
      <div className="p-6">
        <h2 className="text-lg font-bold text-text-primary mb-4">Import Recipes</h2>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            dragOver
              ? 'border-accent bg-accent/5'
              : 'border-gray-300 hover:border-accent/50'
          }`}
        >
          <svg className="w-10 h-10 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-sm text-text-secondary">
            Drag and drop a .json file here, or click to browse
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFileSelect(f);
            }}
          />
        </div>

        {/* Parse error */}
        {parseError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {parseError}
          </div>
        )}

        {/* Preview */}
        {preview && file && (
          <div className="mt-4">
            <div className="flex items-center gap-2 mb-3">
              <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="font-medium text-text-primary">
                {preview.recipeCount} recipe{preview.recipeCount !== 1 ? 's' : ''} found
              </span>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 max-h-40 overflow-y-auto">
              <ul className="space-y-1">
                {preview.titles.map((title, i) => (
                  <li key={i} className="text-sm text-text-secondary flex items-center gap-2">
                    <span className="w-5 text-right text-xs text-gray-400">{i + 1}.</span>
                    {title}
                  </li>
                ))}
                {preview.recipeCount > 10 && (
                  <li className="text-sm text-text-secondary italic pl-7">
                    ...and {preview.recipeCount - 10} more
                  </li>
                )}
              </ul>
            </div>
          </div>
        )}

        {/* Import errors */}
        {importMutation.isError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {importMutation.error?.message || 'Import failed'}
          </div>
        )}

        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={handleClose} disabled={importMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => { if (file) importMutation.mutate(file); }}
            disabled={!file || !preview || importMutation.isPending}
          >
            {importMutation.isPending ? 'Importing...' : `Import ${preview?.recipeCount || 0} Recipe${(preview?.recipeCount || 0) !== 1 ? 's' : ''}`}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export { ImportRecipesModal };
