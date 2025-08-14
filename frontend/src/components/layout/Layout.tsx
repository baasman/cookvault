import React from 'react';
import { Header } from './Header';
import BetaBanner from '../ui/BetaBanner';

interface LayoutProps {
  children: React.ReactNode;
  className?: string;
}

const Layout: React.FC<LayoutProps> = ({ children, className = '' }) => {
  return (
    <div className="min-h-screen" style={{backgroundColor: '#fcf9f8'}}>
      <BetaBanner />
      <Header />
      <main className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 ${className}`}>
        {children}
      </main>
    </div>
  );
};

export { Layout };