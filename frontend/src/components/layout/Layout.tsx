import React from 'react';
import { Header } from './Header';
import { Footer } from './Footer';
import BetaBanner from '../ui/BetaBanner';
import OfflineBanner from '../OfflineBanner';
import { useSwipeBack } from '../../hooks/useSwipeBack';

interface LayoutProps {
  children: React.ReactNode;
  className?: string;
}

const Layout: React.FC<LayoutProps> = ({ children, className = '' }) => {
  const { isActive, progress } = useSwipeBack();

  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden w-full max-w-full" style={{ backgroundColor: '#fcf9f8' }}>
      {/* Swipe back indicator */}
      {isActive && (
        <div
          className="fixed left-0 top-0 bottom-0 z-[100] pointer-events-none"
          style={{
            width: '8px',
            background: `linear-gradient(to right, rgba(241, 95, 28, ${0.3 + progress * 0.5}), transparent)`,
            transform: `scaleX(${1 + progress * 2})`,
            transformOrigin: 'left',
          }}
        />
      )}
      {/* Back arrow indicator */}
      {isActive && progress > 0.2 && (
        <div
          className="fixed left-2 top-1/2 -translate-y-1/2 z-[100] pointer-events-none transition-opacity"
          style={{
            opacity: Math.min((progress - 0.2) * 2, 1),
          }}
        >
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{
              backgroundColor: `rgba(241, 95, 28, ${0.8 + progress * 0.2})`,
              transform: `scale(${0.8 + progress * 0.4})`,
            }}
          >
            <svg
              className="w-6 h-6 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </div>
        </div>
      )}
      <BetaBanner />
      <OfflineBanner />
      <Header />
      <main className={`max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 overflow-x-hidden box-border ${className}`}>
        {children}
      </main>
      <Footer />
    </div>
  );
};

export { Layout };