import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { SplashScreen } from '@capacitor/splash-screen'
import { StatusBar, Style } from '@capacitor/status-bar'
import { isNativePlatform } from './utils/platform'
import './index.css'
import { App } from './App.tsx'

// Note: Sentry initialization is handled by CookieConsentContext
// after user consents to cookies (GDPR compliance)

const initApp = async () => {
  // Initialize native platform features
  if (isNativePlatform()) {
    try {
      // Configure status bar - overlay mode makes it transparent
      // so content extends behind it (we use safe-area-inset-top for padding)
      await StatusBar.setOverlaysWebView({ overlay: true });
      await StatusBar.setStyle({ style: Style.Dark });
      await StatusBar.setBackgroundColor({ color: '#fcf9f8' });
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
