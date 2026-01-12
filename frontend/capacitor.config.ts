import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.cookle.app',
  appName: 'Cookle',
  webDir: 'dist',

  ios: {
    scheme: 'App',
    contentInset: 'automatic',
    allowsLinkPreview: true,
    backgroundColor: '#ffffff',
    preferredContentMode: 'mobile',
  },

  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#ffffff',
      showSpinner: false,
      iosSpinnerStyle: 'small',
      spinnerColor: '#f15f1c',
    },

    Keyboard: {
      resize: 'body',
      resizeOnFullScreen: true,
    },

    StatusBar: {
      style: 'dark',
      backgroundColor: '#ffffff',
    },
  },
};

export default config;
