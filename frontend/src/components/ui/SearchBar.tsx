import React from 'react';
import { Input } from './Input';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

const SearchBar: React.FC<SearchBarProps> = ({ 
  value, 
  onChange, 
  placeholder = "Search recipes, ingredients, tags...",
  className = ""
}) => {
  const searchIcon = (
    <svg 
      className="h-5 w-5" 
      fill="none" 
      viewBox="0 0 24 24" 
      stroke="currentColor"
    >
      <path 
        strokeLinecap="round" 
        strokeLinejoin="round" 
        strokeWidth={2} 
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" 
      />
    </svg>
  );

  return (
    <div className={`max-w-2xl ${className}`}>
      <Input
        type="search"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        icon={searchIcon}
        className="text-lg py-3"
      />
    </div>
  );
};

export { SearchBar };