import React from 'react';

interface IconProps {
  className?: string;
}



const ArrowRightIcon: React.FC<IconProps> = ({ className = '' }) => {
  return (
    <svg 
      className={`${className} flex-shrink-0`}
      fill="currentColor" 
      viewBox="0 0 24 24"
      style={{ maxWidth: '100%', maxHeight: '100%' }}
    >
      <path d="M4,11V13H16L10.5,18.5L11.92,19.92L19.84,12L11.92,4.08L10.5,5.5L16,11H4Z"/>
    </svg>
  );
};

export { ArrowRightIcon };