import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import * as Sentry from '@sentry/react';
import { isNativePlatform } from '../utils/platform';

interface CookieConsentContextType {
  hasConsented: boolean | null; // null = not yet decided
  acceptCookies: () => void;
  declineCookies: () => void;
}

const CookieConsentContext = createContext<CookieConsentContextType | undefined>(undefined);

const CONSENT_KEY = 'cookie-consent';
const CONSENT_TIMESTAMP_KEY = 'cookie-consent-timestamp';

// Initialize Sentry when consent is given
const initializeSentry = () => {
  const sentryDsn = import.meta.env.VITE_SENTRY_DSN;

  if (sentryDsn && import.meta.env.PROD) {
    Sentry.init({
      dsn: sentryDsn,
      environment: import.meta.env.MODE,
      tracesSampleRate: 0.1,
      enabled: true,
      ignoreErrors: [
        /extensions\//i,
        /^chrome:\/\//i,
        'Network request failed',
        'Failed to fetch',
        'Load failed',
        'ResizeObserver loop limit exceeded',
        'ResizeObserver loop completed with undelivered notifications',
      ],
    });
  }
};

export const CookieConsentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [hasConsented, setHasConsented] = useState<boolean | null>(null);

  // Check for existing consent on mount
  useEffect(() => {
    // On native platforms (iOS/Android), auto-enable Sentry without consent prompt
    // Sentry is error monitoring, not advertising tracking, so ATT is not required
    if (isNativePlatform()) {
      setHasConsented(true);
      initializeSentry();
      return;
    }

    // On web, check for stored consent
    const storedConsent = localStorage.getItem(CONSENT_KEY);

    if (storedConsent === 'true') {
      setHasConsented(true);
      // Initialize Sentry if user previously consented
      initializeSentry();
    } else if (storedConsent === 'false') {
      setHasConsented(false);
    }
    // If null/undefined, keep hasConsented as null (show banner)
  }, []);

  const acceptCookies = useCallback(() => {
    localStorage.setItem(CONSENT_KEY, 'true');
    localStorage.setItem(CONSENT_TIMESTAMP_KEY, new Date().toISOString());
    setHasConsented(true);
    initializeSentry();
  }, []);

  const declineCookies = useCallback(() => {
    localStorage.setItem(CONSENT_KEY, 'false');
    localStorage.setItem(CONSENT_TIMESTAMP_KEY, new Date().toISOString());
    setHasConsented(false);
  }, []);

  return (
    <CookieConsentContext.Provider value={{ hasConsented, acceptCookies, declineCookies }}>
      {children}
    </CookieConsentContext.Provider>
  );
};

export const useCookieConsent = (): CookieConsentContextType => {
  const context = useContext(CookieConsentContext);
  if (context === undefined) {
    throw new Error('useCookieConsent must be used within a CookieConsentProvider');
  }
  return context;
};
