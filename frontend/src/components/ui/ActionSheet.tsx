import React, { useEffect, useRef, useState, useCallback } from 'react';
import { isIOS, isNativePlatform } from '../../utils/platform';
import { lightImpact, selectionChanged } from '../../utils/haptics';

export interface ActionSheetOption {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  destructive?: boolean;
}

interface ActionSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  options: ActionSheetOption[];
  cancelText?: string;
}

/**
 * iOS-style action sheet component that slides up from the bottom
 * Only renders on iOS native platform, returns null otherwise
 */
export const ActionSheet: React.FC<ActionSheetProps> = ({
  isOpen,
  onClose,
  title,
  options,
  cancelText = 'Cancel',
}) => {
  const [isAnimating, setIsAnimating] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const sheetRef = useRef<HTMLDivElement>(null);
  const startY = useRef<number>(0);
  const currentY = useRef<number>(0);
  const isDragging = useRef<boolean>(false);

  // Only show on native iOS
  const shouldRender = isIOS() && isNativePlatform();

  // Handle open/close animations
  useEffect(() => {
    if (isOpen) {
      setIsVisible(true);
      // Small delay to ensure DOM is ready for animation
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setIsAnimating(true);
        });
      });
    } else {
      setIsAnimating(false);
      // Wait for animation to complete before hiding
      const timer = setTimeout(() => {
        setIsVisible(false);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Handle backdrop click
  const handleBackdropClick = useCallback(() => {
    lightImpact();
    onClose();
  }, [onClose]);

  // Handle option click
  const handleOptionClick = useCallback((option: ActionSheetOption) => {
    selectionChanged();
    option.onClick();
    onClose();
  }, [onClose]);

  // Handle cancel click
  const handleCancelClick = useCallback(() => {
    lightImpact();
    onClose();
  }, [onClose]);

  // Drag-to-dismiss handlers
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    startY.current = e.touches[0].clientY;
    isDragging.current = true;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isDragging.current || !sheetRef.current) return;

    currentY.current = e.touches[0].clientY;
    const deltaY = currentY.current - startY.current;

    // Only allow dragging down
    if (deltaY > 0) {
      sheetRef.current.style.transform = `translateY(${deltaY}px)`;
    }
  }, []);

  const handleTouchEnd = useCallback(() => {
    if (!isDragging.current || !sheetRef.current) return;

    isDragging.current = false;
    const deltaY = currentY.current - startY.current;

    // If dragged more than 100px, close the sheet
    if (deltaY > 100) {
      lightImpact();
      onClose();
    } else {
      // Reset position
      sheetRef.current.style.transform = '';
    }

    startY.current = 0;
    currentY.current = 0;
  }, [onClose]);

  // Prevent body scroll when sheet is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!shouldRender || !isVisible) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className={`ios-action-sheet-backdrop transition-opacity duration-300 ${
          isAnimating ? 'opacity-100' : 'opacity-0'
        }`}
        onClick={handleBackdropClick}
        aria-hidden="true"
      />

      {/* Action Sheet */}
      <div
        ref={sheetRef}
        className={`ios-action-sheet ${isAnimating ? 'open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Action sheet'}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Drag handle */}
        <div className="ios-action-sheet-handle" />

        {/* Title */}
        {title && (
          <div className="px-4 py-3 text-center border-b" style={{ borderColor: '#e8d7cf' }}>
            <h3 className="text-sm font-medium text-gray-500">{title}</h3>
          </div>
        )}

        {/* Options */}
        <div className="py-2">
          {options.map((option, index) => (
            <button
              key={index}
              className="w-full px-4 py-4 text-left flex items-center gap-3 active:bg-gray-100 transition-colors"
              style={{
                color: option.destructive ? '#ef4444' : '#1c120d',
              }}
              onClick={() => handleOptionClick(option)}
            >
              {option.icon && (
                <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                  {option.icon}
                </span>
              )}
              <span className="text-base font-medium">{option.label}</span>
            </button>
          ))}
        </div>

        {/* Cancel button */}
        <div className="border-t px-4 py-2" style={{ borderColor: '#e8d7cf' }}>
          <button
            className="w-full py-4 text-center text-base font-semibold active:bg-gray-100 rounded-xl transition-colors"
            style={{ color: '#f15f1c' }}
            onClick={handleCancelClick}
          >
            {cancelText}
          </button>
        </div>
      </div>
    </>
  );
};
