import * as Sentry from '@sentry/react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { SplashScreen } from '@capacitor/splash-screen'
import { StatusBar, Style } from '@capacitor/status-bar'
import { isNativePlatform } from './utils/platform'
import './index.css'
import App from './App.tsx'

// Initialize Sentry for error tracking (before app renders)
Sentry.init({
  dsn: 'https://22aecad3c9e88113f53446ccc60aa114@o4510811666055168.ingest.us.sentry.io/4510811889139712',
  environment: import.meta.env.MODE, // 'development' or 'production'
  // Capture 10% of transactions for performance monitoring
  tracesSampleRate: 0.1,
  // Don't send errors in development (optional - remove if you want dev errors too)
  enabled: import.meta.env.PROD,
  // Ignore common non-actionable errors
  ignoreErrors: [
    // Browser extensions
    /extensions\//i,
    /^chrome:\/\//i,
    // Network errors that users can't do anything about
    'Network request failed',
    'Failed to fetch',
    'Load failed',
    // ResizeObserver errors (common, usually harmless)
    'ResizeObserver loop limit exceeded',
    'ResizeObserver loop completed with undelivered notifications',
  ],
})

const initApp = async () => {
  // Initialize native platform features
  if (isNativePlatform()) {
    try {
      // Configure status bar
      await StatusBar.setStyle({ style: Style.Dark });
    } catch (error) {
      console.error('Failed to configure status bar:', error);
    }
  }

  // Render the app
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );

  // Hide splash screen after app is rendered
  if (isNativePlatform()) {
    try {
      await SplashScreen.hide();
    } catch (error) {
      console.error('Failed to hide splash screen:', error);
    }
  }
};

initApp();
