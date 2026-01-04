import { useCallback, useMemo } from 'react';
import { useSignal } from '@tma.js/sdk-react';
import {
  miniApp,
  mainButton,
  backButton,
  viewport,
  hapticFeedback,
  popup,
  themeParams,
  openLink as sdkOpenLink,
  openTelegramLink as sdkOpenTelegramLink,
} from '@tma.js/sdk';

export interface UseTelegramReturn {
  // Main Button
  showMainButton: (text: string, onClick: () => void) => void;
  hideMainButton: () => void;
  setMainButtonLoading: (loading: boolean) => void;

  // Back Button
  showBackButton: (onClick: () => void) => void;
  hideBackButton: () => void;

  // Alerts & Dialogs
  showAlert: (message: string) => Promise<void>;
  showConfirm: (message: string) => Promise<boolean>;

  // Navigation
  close: () => void;
  openLink: (url: string) => void;
  openTelegramLink: (url: string) => void;

  // Viewport
  expand: () => void;
  getViewportHeight: () => number;

  // Haptic Feedback
  vibrate: (style?: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
  notificationOccurred: (type: 'error' | 'success' | 'warning') => void;

  // Misc
  ready: () => void;
  setHeaderColor: (color: string) => void;
  setBackgroundColor: (color: string) => void;

  // Data
  initData: string;
  colorScheme: 'light' | 'dark';
  platform: string;
}

export function useTelegram(): UseTelegramReturn {
  // Use SSR-safe signals from @tma.js/sdk-react
  const isDark = useSignal(themeParams.isDark, () => false);
  const viewportHeight = useSignal(viewport.height, () => 0);

  // Get initData directly from window.Telegram.WebApp.initData
  // Reading directly avoids timing issues with SDK signal initialization
  // This matches how Vue template works with @twa-dev/sdk
  const initDataValue = useMemo(() => {
    if (typeof window === 'undefined') return '';
    try {
      return (window as { Telegram?: { WebApp?: { initData?: string } } }).Telegram?.WebApp?.initData || '';
    } catch {
      return '';
    }
  }, []);

  // Get platform from WebApp (android, ios, tdesktop, macos, weba, web)
  const platformValue = useMemo(() => {
    if (typeof window === 'undefined') return 'unknown';
    try {
      return (window as { Telegram?: { WebApp?: { platform?: string } } }).Telegram?.WebApp?.platform || 'unknown';
    } catch {
      return 'unknown';
    }
  }, []);

  const showMainButton = useCallback(
    (text: string, onClick: () => void) => {
      try {
        mainButton.setText(text);
        mainButton.show();
        mainButton.enable();
        mainButton.onClick(onClick);
      } catch (error) {
        console.warn('Failed to show main button:', error);
      }
    },
    []
  );

  const hideMainButton = useCallback(() => {
    try {
      mainButton.hide();
    } catch (error) {
      console.warn('Failed to hide main button:', error);
    }
  }, []);

  const setMainButtonLoading = useCallback(
    (loading: boolean) => {
      try {
        if (loading) {
          mainButton.showLoader();
        } else {
          mainButton.hideLoader();
        }
      } catch (error) {
        console.warn('Failed to set main button loading:', error);
      }
    },
    []
  );

  const showBackButton = useCallback(
    (onClick: () => void) => {
      try {
        backButton.onClick(onClick);
        backButton.show();
      } catch (error) {
        console.warn('Failed to show back button:', error);
      }
    },
    []
  );

  const hideBackButton = useCallback(() => {
    try {
      backButton.hide();
    } catch (error) {
      console.warn('Failed to hide back button:', error);
    }
  }, []);

  const showAlert = useCallback(
    async (message: string) => {
      try {
        await popup.show({ message });
      } catch (error) {
        console.warn('Failed to show alert:', error);
        window.alert(message);
      }
    },
    []
  );

  const showConfirm = useCallback(
    async (message: string) => {
      try {
        const result = await popup.show({
          message,
          buttons: [
            { id: 'cancel', type: 'cancel' },
            { id: 'ok', type: 'default', text: 'OK' },
          ],
        });
        return result === 'ok';
      } catch (error) {
        console.warn('Failed to show confirm:', error);
        return window.confirm(message);
      }
    },
    []
  );

  const close = useCallback(() => {
    try {
      miniApp.close();
    } catch (error) {
      console.warn('Failed to close app:', error);
    }
  }, []);

  const openLink = useCallback(
    (url: string) => {
      try {
        sdkOpenLink(url);
      } catch (error) {
        console.warn('Failed to open link:', error);
        window.open(url, '_blank');
      }
    },
    []
  );

  const openTelegramLink = useCallback(
    (url: string) => {
      try {
        sdkOpenTelegramLink(url);
      } catch (error) {
        console.warn('Failed to open Telegram link:', error);
        window.open(url, '_blank');
      }
    },
    []
  );

  const expand = useCallback(() => {
    try {
      viewport.expand();
    } catch (error) {
      console.warn('Failed to expand viewport:', error);
    }
  }, []);

  const getViewportHeight = useCallback(() => {
    return viewportHeight || (typeof window !== 'undefined' ? window.innerHeight : 0);
  }, [viewportHeight]);

  const vibrate = useCallback(
    (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' = 'medium') => {
      try {
        hapticFeedback.impactOccurred(style);
      } catch (error) {
        console.warn('Failed to vibrate:', error);
      }
    },
    []
  );

  const notificationOccurred = useCallback(
    (type: 'error' | 'success' | 'warning') => {
      try {
        hapticFeedback.notificationOccurred(type);
      } catch (error) {
        console.warn('Failed to trigger notification:', error);
      }
    },
    []
  );

  const ready = useCallback(() => {
    try {
      miniApp.ready();
    } catch (error) {
      console.warn('Failed to mark app as ready:', error);
    }
  }, []);

  const setHeaderColor = useCallback(
    (color: string) => {
      try {
        miniApp.setHeaderColor(color as any);
      } catch (error) {
        console.warn('Failed to set header color:', error);
      }
    },
    []
  );

  const setBackgroundColor = useCallback(
    (color: string) => {
      try {
        // Use native Telegram WebApp API directly (not available in @tma.js/sdk)
        const webApp = (window as { Telegram?: { WebApp?: { setBackgroundColor?: (color: string) => void } } }).Telegram?.WebApp;
        webApp?.setBackgroundColor?.(color);
      } catch (error) {
        console.warn('Failed to set background color:', error);
      }
    },
    []
  );

  return {
    showMainButton,
    hideMainButton,
    setMainButtonLoading,
    showBackButton,
    hideBackButton,
    showAlert,
    showConfirm,
    close,
    openLink,
    openTelegramLink,
    expand,
    getViewportHeight,
    vibrate,
    notificationOccurred,
    ready,
    setHeaderColor,
    setBackgroundColor,
    initData: initDataValue,
    colorScheme: isDark ? 'dark' : 'light',
    platform: platformValue, // android, ios, tdesktop, macos, weba, web, or unknown
  };
}
