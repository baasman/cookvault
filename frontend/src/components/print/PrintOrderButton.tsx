import React, { useState } from 'react';
import { PrinterIcon } from '@heroicons/react/24/outline';
import { PrintOrderModal } from './PrintOrderModal';

interface PrintOrderButtonProps {
  cookbookId: number;
  cookbookTitle: string;
  className?: string;
  buttonText?: string;
  variant?: 'primary' | 'secondary' | 'outline';
}

export const PrintOrderButton: React.FC<PrintOrderButtonProps> = ({
  cookbookId,
  cookbookTitle,
  className = '',
  buttonText = 'Order Print Copy',
  variant = 'primary'
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const getButtonClasses = () => {
    const baseClasses = "inline-flex items-center px-4 py-2 text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200";

    switch (variant) {
      case 'primary':
        return `${baseClasses} text-white hover:opacity-90 focus:ring-emerald-500 shadow-sm`;
      case 'secondary':
        return `${baseClasses} text-emerald-700 hover:opacity-90 focus:ring-emerald-500`;
      case 'outline':
        return `${baseClasses} text-emerald-700 border border-emerald-300 hover:bg-emerald-50 focus:ring-emerald-500`;
      default:
        return `${baseClasses} text-white hover:opacity-90 focus:ring-emerald-500 shadow-sm`;
    }
  };

  const getButtonStyle = () => {
    switch (variant) {
      case 'primary':
        return { backgroundColor: '#059669' }; // emerald-600
      case 'secondary':
        return { backgroundColor: '#d1fae5' }; // emerald-100
      case 'outline':
        return { backgroundColor: '#ffffff' };
      default:
        return { backgroundColor: '#059669' }; // emerald-600
    }
  };

  return (
    <>
      <button
        onClick={() => setIsModalOpen(true)}
        className={`${getButtonClasses()} ${className}`}
        style={getButtonStyle()}
      >
        <PrinterIcon className="h-5 w-5 mr-2" />
        {buttonText}
      </button>

      {isModalOpen && (
        <PrintOrderModal
          cookbookId={cookbookId}
          cookbookTitle={cookbookTitle}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </>
  );
};