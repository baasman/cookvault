import React from 'react';

interface IconProps {
  className?: string;
  style?: React.CSSProperties;
}

const BookIcon: React.FC<IconProps> = ({ className = '', style }) => {
  return (
    <svg 
      className={`${className} flex-shrink-0`}
      fill="none" 
      stroke="currentColor"
      viewBox="0 0 24 24"
      strokeWidth={2}
      style={style}
    >
      <path 
        strokeLinecap="round" 
        strokeLinejoin="round" 
        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" 
      />
    </svg>
  );
};

export { BookIcon };
