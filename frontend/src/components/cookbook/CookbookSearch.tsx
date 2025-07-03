import React, { useState, useEffect } from 'react';
import { useDebounce } from '../../hooks/useDebounce';
import { cookbooksApi } from '../../services/cookbooksApi';
import type { Cookbook } from '../../types';

interface CookbookSearchProps {
  onSelect: (cookbook: Cookbook) => void;
  onCreateNew: () => void;
}

const CookbookSearch: React.FC<CookbookSearchProps> = ({ onSelect, onCreateNew }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Cookbook[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  useEffect(() => {
    const performSearch = async () => {
      if (!debouncedSearchQuery.trim()) {
        setSearchResults([]);
        setHasSearched(false);
        return;
      }

      setIsLoading(true);
      try {
        const results = await cookbooksApi.searchAllCookbooks(debouncedSearchQuery);
        setSearchResults(results);
        setHasSearched(true);
      } catch (error) {
        console.error('Search failed:', error);
        setSearchResults([]);
        setHasSearched(true);
      } finally {
        setIsLoading(false);
      }
    };

    performSearch();
  }, [debouncedSearchQuery]);

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.getFullYear().toString();
    } catch {
      return '';
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Search Input */}
      <div>
        <label className="block text-sm font-medium mb-2" style={{color: '#1c120d'}}>
          Search for Existing Cookbook
        </label>
        <input
          type="text"
          placeholder="Search by title, author, publisher, or ISBN..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
          style={{borderColor: '#e8d7cf'}}
        />
        <p className="text-xs mt-1" style={{color: '#9b644b'}}>
          Search across cookbooks uploaded by other users
        </p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2" style={{borderColor: '#f15f1c'}}></div>
        </div>
      )}

      {/* Search Results */}
      {!isLoading && hasSearched && (
        <div className="max-h-64 overflow-y-auto">
          {searchResults.length > 0 ? (
            <div className="space-y-2">
              <p className="text-sm font-medium" style={{color: '#1c120d'}}>
                Found {searchResults.length} cookbook{searchResults.length !== 1 ? 's' : ''}:
              </p>
              {searchResults.map((cookbook) => (
                <div
                  key={cookbook.id}
                  onClick={() => onSelect(cookbook)}
                  className="p-3 border rounded-lg cursor-pointer transition-colors hover:bg-background-secondary hover:border-accent/20"
                  style={{borderColor: '#e8d7cf'}}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-medium text-sm" style={{color: '#1c120d'}}>
                        {cookbook.title}
                      </h4>
                      {cookbook.author && (
                        <p className="text-xs text-text-secondary">
                          by {cookbook.author}
                        </p>
                      )}
                      {cookbook.description && (
                        <p className="text-xs text-text-secondary mt-1 line-clamp-2">
                          {cookbook.description}
                        </p>
                      )}
                      
                      {/* Metadata */}
                      <div className="flex items-center gap-3 mt-2 text-xs text-text-secondary">
                        {cookbook.publisher && (
                          <span>{cookbook.publisher}</span>
                        )}
                        {cookbook.publication_date && (
                          <span>{formatDate(cookbook.publication_date)}</span>
                        )}
                        {cookbook.isbn && (
                          <span>ISBN: {cookbook.isbn}</span>
                        )}
                      </div>
                      
                      {/* Creator and Recipe Count */}
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-xs" style={{color: '#9b644b'}}>
                          {(cookbook as any).creator 
                            ? `Uploaded by ${(cookbook as any).creator.username}`
                            : 'Unknown creator'
                          }
                        </span>
                        <span className="text-xs px-2 py-1 rounded-full bg-background-secondary">
                          {cookbook.recipe_count} recipe{cookbook.recipe_count !== 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>
                    
                    <div className="ml-3 flex-shrink-0">
                      <button className="text-xs px-3 py-1 rounded-full text-white transition-colors" style={{backgroundColor: '#f15f1c'}}>
                        Select
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6">
              <svg className="h-12 w-12 mx-auto text-text-secondary mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <h3 className="text-sm font-medium text-text-primary mb-2">
                No cookbooks found
              </h3>
              <p className="text-xs text-text-secondary mb-4">
                No existing cookbooks match your search. You can create a new one instead.
              </p>
              <button
                onClick={onCreateNew}
                className="text-xs px-4 py-2 rounded-full text-white transition-colors"
                style={{backgroundColor: '#f15f1c'}}
              >
                Create New Cookbook
              </button>
            </div>
          )}
        </div>
      )}

      {/* Initial State */}
      {!hasSearched && !isLoading && searchQuery.trim() === '' && (
        <div className="text-center py-6 text-text-secondary">
          <svg className="h-12 w-12 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p className="text-sm">
            Start typing to search for existing cookbooks
          </p>
        </div>
      )}
    </div>
  );
};

export { CookbookSearch };