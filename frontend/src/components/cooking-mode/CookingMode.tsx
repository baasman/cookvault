import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { Recipe } from '../../types';
import { selectionChanged, lightImpact } from '../../utils/haptics';
import { isNativePlatform } from '../../utils/platform';
import { useWakeLock } from '../../hooks/useWakeLock';
import { CookingModeProgress } from './CookingModeProgress';
import { CookingModeStep } from './CookingModeStep';
import { CookingModeIngredients } from './CookingModeIngredients';

interface CookingModeProps {
  recipe: Recipe;
  scaleFactor: number;
  onClose: () => void;
}

const CookingMode: React.FC<CookingModeProps> = ({ recipe, scaleFactor, onClose }) => {
  const sortedInstructions = [...(recipe.instructions || [])].sort(
    (a, b) => a.step_number - b.step_number
  );
  const totalSteps = sortedInstructions.length;
  const [currentStep, setCurrentStep] = useState(1);
  // Default open on desktop, closed on mobile
  const [showIngredients, setShowIngredients] = useState(
    typeof window !== 'undefined' && window.innerWidth >= 768
  );
  const contentRef = useRef<HTMLDivElement>(null);

  // Keep screen awake while cooking
  useWakeLock(true);

  // Swipe state
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const isSwipingRef = useRef(false);

  const goToStep = useCallback((step: number) => {
    const clamped = Math.max(1, Math.min(step, totalSteps));
    if (clamped !== currentStep) {
      setCurrentStep(clamped);
      selectionChanged();
      if (contentRef.current) {
        contentRef.current.scrollTop = 0;
      }
    }
  }, [currentStep, totalSteps]);

  const goNext = useCallback(() => goToStep(currentStep + 1), [goToStep, currentStep]);
  const goPrev = useCallback(() => goToStep(currentStep - 1), [goToStep, currentStep]);

  const toggleIngredients = useCallback(() => {
    setShowIngredients(prev => !prev);
    lightImpact();
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowRight':
        case 'ArrowDown':
          e.preventDefault();
          goNext();
          break;
        case 'ArrowLeft':
        case 'ArrowUp':
          e.preventDefault();
          goPrev();
          break;
        case 'Escape':
          e.preventDefault();
          // On mobile, if ingredients panel is open as overlay, close it first
          if (showIngredients && window.innerWidth < 768) {
            setShowIngredients(false);
          } else {
            onClose();
          }
          break;
        case 'i':
          e.preventDefault();
          toggleIngredients();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [goNext, goPrev, onClose, showIngredients, toggleIngredients]);

  // Touch/swipe navigation on the step content area
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0];
    touchStartRef.current = { x: touch.clientX, y: touch.clientY };
    isSwipingRef.current = false;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!touchStartRef.current) return;
    const touch = e.touches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;

    if (!isSwipingRef.current && Math.abs(deltaY) > Math.abs(deltaX)) {
      touchStartRef.current = null;
      return;
    }

    if (Math.abs(deltaX) > 20) {
      isSwipingRef.current = true;
    }
  }, []);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (!touchStartRef.current || !isSwipingRef.current) {
      touchStartRef.current = null;
      return;
    }

    const touch = e.changedTouches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;

    if (Math.abs(deltaX) >= 50) {
      if (deltaX < 0) {
        goNext();
      } else {
        goPrev();
      }
    }

    touchStartRef.current = null;
    isSwipingRef.current = false;
  }, [goNext, goPrev]);

  // Prevent body scroll and hide status bar
  useEffect(() => {
    document.body.style.overflow = 'hidden';

    const hideStatusBar = async () => {
      if (isNativePlatform()) {
        try {
          const { StatusBar } = await import('@capacitor/status-bar');
          await StatusBar.hide();
        } catch (error) {
          console.error('Failed to hide status bar:', error);
        }
      }
    };

    const showStatusBar = async () => {
      if (isNativePlatform()) {
        try {
          const { StatusBar } = await import('@capacitor/status-bar');
          await StatusBar.show();
        } catch (error) {
          console.error('Failed to show status bar:', error);
        }
      }
    };

    hideStatusBar();

    return () => {
      document.body.style.overflow = 'unset';
      showStatusBar();
    };
  }, []);

  const content = (
    <div
      className="fixed inset-0 z-[60] bg-white flex flex-col"
      style={{
        paddingTop: 'env(safe-area-inset-top, 0px)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      }}
    >
      {/* Progress bar + close */}
      <CookingModeProgress
        currentStep={currentStep}
        totalSteps={totalSteps}
        onClose={onClose}
      />

      {/* Main content area: sidebar + step */}
      <div className="flex-1 flex overflow-hidden">

        {/* Ingredients sidebar — always visible on md+, overlay on mobile */}
        {showIngredients && (
          <>
            {/* Mobile backdrop */}
            <div
              className="md:hidden fixed inset-0 bg-black/40 z-10"
              onClick={toggleIngredients}
            />

            {/* Sidebar panel */}
            <div
              className="
                fixed md:relative z-20 md:z-0
                left-0 top-0 bottom-0
                w-[85vw] md:w-80 lg:w-96
                bg-white md:bg-gray-50
                border-r border-gray-200
                flex flex-col
                shadow-xl md:shadow-none
              "
              style={{
                paddingTop: window.innerWidth < 768 ? 'env(safe-area-inset-top, 0px)' : undefined,
                paddingLeft: 'env(safe-area-inset-left, 0px)',
              }}
            >
              {/* Sidebar header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 flex-shrink-0">
                <span className="font-semibold text-lg" style={{ color: '#1c120d' }}>
                  Ingredients
                </span>
                <button
                  onClick={toggleIngredients}
                  className="p-1 text-gray-400 hover:text-gray-600 md:hidden"
                  aria-label="Close ingredients"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Scrollable ingredients list */}
              <div className="flex-1 overflow-y-auto">
                <CookingModeIngredients
                  ingredients={recipe.ingredients || []}
                  scaleFactor={scaleFactor}
                  servings={recipe.servings}
                />
              </div>
            </div>
          </>
        )}

        {/* Step content — vertically centered, max width constrained */}
        <div
          ref={contentRef}
          className="flex-1 overflow-y-auto flex items-start md:items-center justify-center"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div className="w-full max-w-4xl px-4">
            <CookingModeStep
              instruction={sortedInstructions[currentStep - 1]}
              recipeId={recipe.id}
              stepNumber={currentStep}
            />
          </div>
        </div>
      </div>

      {/* Navigation buttons */}
      <div className="flex-shrink-0 border-t border-gray-200 px-4 py-3">
        <div className="flex gap-3 items-center">
          <button
            onClick={goPrev}
            disabled={currentStep <= 1}
            className="flex-1 py-3 px-4 rounded-xl font-medium text-center active:scale-[0.97] disabled:opacity-30"
            style={{
              backgroundColor: '#f1ece9',
              color: '#1c120d',
            }}
          >
            ← Prev
          </button>

          {/* Ingredients toggle — only shown on mobile where sidebar is an overlay */}
          <button
            onClick={toggleIngredients}
            className={`md:hidden flex items-center gap-1.5 py-3 px-3 rounded-xl active:scale-[0.97] border text-sm font-medium ${showIngredients ? 'border-orange-300 bg-orange-50 text-orange-700' : 'border-gray-200 bg-white text-gray-600'}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            Ingredients
          </button>

          {currentStep < totalSteps ? (
            <button
              onClick={goNext}
              className="flex-1 py-3 px-4 rounded-xl font-medium text-white text-center active:scale-[0.97]"
              style={{ backgroundColor: '#f15f1c' }}
            >
              Next →
            </button>
          ) : (
            <button
              onClick={onClose}
              className="flex-1 py-3 px-4 rounded-xl font-medium text-white text-center active:scale-[0.97] bg-green-600"
            >
              Done ✓
            </button>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
};

export { CookingMode };
