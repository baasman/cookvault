import React from 'react';

interface IconProps {
  className?: string;
}



const UploadIcon: React.FC<IconProps> = ({ className = '' }) => {
  return (
    <svg 
      className={`${className} flex-shrink-0`}
      fill="currentColor" 
      viewBox="0 0 24 24"
    >
      <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
    </svg>
  );
};

export { UploadIcon };