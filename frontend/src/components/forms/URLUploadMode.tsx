import React from 'react';

interface URLUploadModeProps {
  recipeUrl: string;
  onUrlChange: (url: string) => void;
}

const URLUploadMode: React.FC<URLUploadModeProps> = ({
  recipeUrl,
  onUrlChange,
}) => {
  return (
    <div className="flex flex-col">
      <div className="pb-2">
        <label className="block text-base font-medium leading-normal" style={{color: '#1c120d'}}>
          Recipe URL *
        </label>
        <p className="text-sm mt-1" style={{color: '#9b644b'}}>
          Paste the URL of a recipe page. Works best with popular recipe sites.
        </p>
      </div>
      <input
        type="url"
        value={recipeUrl}
        onChange={(e) => onUrlChange(e.target.value)}
        placeholder="https://example.com/delicious-recipe"
        className="w-full px-4 py-3 border rounded-lg text-base"
        style={{
          borderColor: '#e8d7cf',
          backgroundColor: '#fcf9f8',
        }}
        required
      />
      <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-700 flex items-start gap-2">
          <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Recipes imported from URLs are for personal use only and cannot be shared publicly.</span>
        </p>
      </div>
    </div>
  );
};

export { URLUploadMode };
