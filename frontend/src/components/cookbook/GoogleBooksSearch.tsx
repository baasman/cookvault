import React, { useState, useEffect } from 'react';
import { useDebounce } from '../../hooks/useDebounce';
import { Button, Input } from '../ui';
import { cookbooksApi, type GoogleBook } from '../../services/cookbooksApi';

interface GoogleBooksSearchProps {
  onBookSelect: (book: GoogleBook) => void;
  onManualEntry: () => void;
  isLoading?: boolean;
  className?: string;
}

const GoogleBooksSearch: React.FC<GoogleBooksSearchProps> = ({
  onBookSelect,
  onManualEntry,
  isLoading = false,
  className = ''
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [books, setBooks] = useState<GoogleBook[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);

  // Debounce search query to avoid excessive API calls
  const debouncedSearchQuery = useDebounce(searchQuery, 500);

  useEffect(() => {
    if (debouncedSearchQuery.trim().length >= 3) {
      searchBooks(debouncedSearchQuery);
    } else {
      setBooks([]);
      setShowResults(false);
    }
  }, [debouncedSearchQuery]);

  const searchBooks = async (query: string) => {
    setIsSearching(true);
    setError(null);
    
    try {
      const data = await cookbooksApi.searchGoogleBooks(query, 8);
      setBooks(data.books);
      setShowResults(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred while searching');
      setBooks([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleBookSelect = (book: GoogleBook) => {
    onBookSelect(book);
    setShowResults(false);
    setSearchQuery('');
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '';
    
    try {
      const date = new Date(dateString);
      return date.getFullYear().toString();
    } catch {
      return dateString;
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="text-center">
        <h3 className="text-lg font-semibold mb-2" style={{ color: '#1c120d' }}>
          Search Online Database
        </h3>
        <p className="text-sm mb-4" style={{ color: '#9b644b' }}>
          Find your cookbook automatically or enter details manually
        </p>
      </div>

      <div className="space-y-3">
        <div className="relative">
          <Input
            type="text"
            placeholder="Search by title, author, or ISBN..."
            value={searchQuery}
            onChange={setSearchQuery}
            className="pr-10"
            disabled={isLoading}
          />
          
          {isSearching && (
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2" style={{ borderColor: '#f15f1c' }}></div>
            </div>
          )}
        </div>

        {error && (
          <div className="p-3 rounded-md" style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca' }}>
            <p className="text-sm" style={{ color: '#dc2626' }}>{error}</p>
          </div>
        )}

        {showResults && books.length > 0 && (
          <div className="border rounded-lg p-4 max-h-96 overflow-y-auto" style={{ backgroundColor: '#ffffff', border: '1px solid #e8d7cf' }}>
            <h4 className="font-medium mb-3" style={{ color: '#1c120d' }}>
              Found {books.length} cookbook{books.length !== 1 ? 's' : ''} online
            </h4>
            
            <div className="space-y-3">
              {books.map((book) => (
                <div
                  key={book.google_books_id}
                  className="flex items-start space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => handleBookSelect(book)}
                >
                  <div className="flex-shrink-0">
                    {book.thumbnail_url ? (
                      <img
                        src={book.thumbnail_url}
                        alt={book.title}
                        className="w-16 h-20 object-cover rounded"
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="w-16 h-20 bg-gray-200 rounded flex items-center justify-center">
                        <svg className="w-8 h-8 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                        </svg>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h5 className="font-medium text-sm truncate" style={{ color: '#1c120d' }}>
                      {book.title}
                    </h5>
                    {book.author && (
                      <p className="text-sm mt-1" style={{ color: '#9b644b' }}>
                        by {book.author}
                      </p>
                    )}
                    <div className="flex items-center space-x-2 mt-1 text-xs" style={{ color: '#9b644b' }}>
                      {book.publisher && (
                        <span>{book.publisher}</span>
                      )}
                      {book.publication_date && (
                        <span>• {formatDate(book.publication_date)}</span>
                      )}
                      {book.page_count && (
                        <span>• {book.page_count} pages</span>
                      )}
                    </div>
                    {book.description && (
                      <p className="text-xs mt-2 text-gray-600 overflow-hidden" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as const }}>
                        {book.description.length > 100 
                          ? `${book.description.substring(0, 100)}...`
                          : book.description
                        }
                      </p>
                    )}
                  </div>
                  
                  <div className="flex-shrink-0">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleBookSelect(book);
                      }}
                    >
                      Use This Book
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {showResults && books.length === 0 && !isSearching && (
          <div className="text-center py-8" style={{ color: '#9b644b' }}>
            <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.29-1.009-5.824-2.562M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <p className="text-sm">No cookbooks found online for "{searchQuery}"</p>
            <p className="text-xs mt-1">Try a different search term or enter details manually</p>
          </div>
        )}
      </div>

      <div className="flex items-center space-x-3">
        <div className="flex-1 h-px bg-gray-300"></div>
        <span className="text-sm" style={{ color: '#9b644b' }}>or</span>
        <div className="flex-1 h-px bg-gray-300"></div>
      </div>

      <div className="text-center">
        <Button
          variant="outline"
          onClick={onManualEntry}
          disabled={isLoading}
          className="w-full"
        >
          Enter Details Manually
        </Button>
      </div>
    </div>
  );
};

export { GoogleBooksSearch };