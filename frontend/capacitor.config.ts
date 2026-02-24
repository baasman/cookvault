import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.cookle.app',
  appName: 'Cookle',
  webDir: 'dist',

  ios: {
    scheme: 'App',
    contentInset: 'automatic',
    allowsLinkPreview: true,
    backgroundColor: '#fcf9f8',
    preferredContentMode: 'mobile',
  },

  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#fcf9f8',
      showSpinner: false,
      iosSpinnerStyle: 'small',
      spinnerColor: '#f15f1c',
    },

    Keyboard: {
      resize: 'native',
      resizeOnFullScreen: true,
      scrollPadding: 100,
    },

    StatusBar: {
      style: 'dark',
      backgroundColor: '#fcf9f8',
      overlaysWebView: true,
    },
  },
};

export default config;
