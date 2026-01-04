import useTelegram from './useTelegram';
import { usePlatformMock } from './usePlatformMock';

export interface PlatformState {
  isTelegram: boolean;
  isWeb: boolean;
  platform: 'telegram' | 'web';
  /** True if Telegram on mobile device (android or ios) */
  isTelegramMobile: boolean;
  /** True if Telegram on desktop app (tdesktop or macos) */
  isTelegramDesktop: boolean;
}

export interface PlatformActions {
  showMainButton: (text: string, callback: () => void) => void;
  hideMainButton: () => void;
  showBackButton: (callback: () => void) => void;
  hideBackButton: () => void;
  setButtonLoader: (state: boolean) => void;
  showAlert: (text: string) => void;
  openInvoice: (url: string, callback: (status: 'pending' | 'failed' | 'cancelled' | 'paid') => void) => void;
  closeApp: () => void;
  expand: () => void;
  getViewportHeight: () => number;
  vibrate: (style?: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' | 'error' | 'warning' | 'success') => void;
  ready: () => void;
  colorScheme: 'light' | 'dark' | undefined;
  telegramPlatform:
    | 'android'
    | 'android_x'
    | 'ios'
    | 'macos'
    | 'tdesktop'
    | 'web'
    | 'weba'
    | 'webk'
    | 'unigram'
    | 'unknown';
  headerColor: string;
  setHeaderColor: (color: 'bg_color' | 'secondary_bg_color' | `#${string}`) => void;
  webAppInitData: string;
  openTelegramLink: (url: string) => void;
  shareMessage: (msgId: string, callback?: (success: boolean) => void) => void;
  openLink: (url: string) => void;
  disableVerticalSwipes: () => void;
}

export type UsePlatformReturn = PlatformState & PlatformActions;

/**
 * Platform detection and abstraction layer
 * Wraps useTelegram and provides platform-aware functionality
 */
export function usePlatform(): UsePlatformReturn {
  const telegram = useTelegram();
  const platformMock = usePlatformMock();

  // Check if mock mode is enabled (debug mode only)
  const isMockMode = import.meta.env.VITE_DEBUG === 'true' && platformMock.isMockEnabled.value;

  // Detect if we're in Telegram Mini App or web browser
  let isTelegram: boolean;
  let isWeb: boolean;
  let platform: 'telegram' | 'web';
  let telegramPlatform: typeof telegram.platform;
  let webAppInitData: string;

  if (isMockMode) {
    // Mock Telegram iOS environment with selected user data
    const selectedUser = platformMock.selectedUser.value;
    isTelegram = true;
    isWeb = false;
    platform = 'telegram';
    telegramPlatform = 'ios';

    // Create mock initData with selected user information
    const mockUserData = selectedUser
      ? {
          user_id: selectedUser.user_id,
          username: selectedUser.username,
          display_name: selectedUser.display_name,
          user_type: selectedUser.user_type,
        }
      : {
          user_id: 123456789,
          username: 'ReallyCoolSupport',
          display_name: 'Really Cool Support',
          user_type: 'REGISTERED',
        };

    webAppInitData = `mock_init_data=true&user=${encodeURIComponent(JSON.stringify(mockUserData))}`; // Include mock user data
  } else {
    // Normal platform detection
    isTelegram = telegram.platform !== 'unknown' && !!telegram.webAppInitData;
    isWeb = !isTelegram;
    platform = isTelegram ? 'telegram' : 'web';
    telegramPlatform = telegram.platform;
    webAppInitData = telegram.webAppInitData;
  }

  // Web fallbacks for Telegram-specific functionality
  const webFallbacks = {
    showMainButton: (text: string, callback: () => void) => {
      if (isTelegram) {
        telegram.showMainButton(text, callback);
      } else {
        // For web, we could show a custom button or ignore
        console.log('Web fallback: showMainButton', text);
      }
    },

    hideMainButton: () => {
      if (isTelegram) {
        telegram.hideMainButton();
      } else {
        console.log('Web fallback: hideMainButton');
      }
    },

    showBackButton: (callback: () => void) => {
      if (isTelegram) {
        telegram.showBackButton(callback);
      } else {
        console.log('Web fallback: showBackButton');
      }
    },

    hideBackButton: () => {
      if (isTelegram) {
        telegram.hideBackButton();
      } else {
        console.log('Web fallback: hideBackButton');
      }
    },

    setButtonLoader: (state: boolean) => {
      if (isTelegram) {
        telegram.setButtonLoader(state);
      } else {
        console.log('Web fallback: setButtonLoader', state);
      }
    },

    showAlert: (text: string) => {
      if (isTelegram) {
        telegram.showAlert(text);
      } else {
        // Use browser alert as fallback
        alert(text);
      }
    },

    openInvoice: (url: string, callback: (status: 'pending' | 'failed' | 'cancelled' | 'paid') => void) => {
      if (isTelegram) {
        telegram.openInvoice(url, callback);
      } else {
        // For web, open in new window/tab
        window.open(url, '_blank');
        callback('pending');
      }
    },

    closeApp: () => {
      if (isTelegram) {
        telegram.closeApp();
      } else {
        // For web, could close window or redirect
        console.log('Web fallback: closeApp');
      }
    },

    expand: () => {
      if (isTelegram) {
        telegram.expand();
      } else {
        console.log('Web fallback: expand');
      }
    },

    getViewportHeight: () => {
      if (isTelegram) {
        return telegram.getViewportHeight();
      } else {
        return window.innerHeight;
      }
    },

    vibrate: (style?: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' | 'error' | 'warning' | 'success') => {
      if (isTelegram) {
        telegram.vibrate(style);
      } else {
        // Use web vibration API if available
        if (navigator.vibrate) {
          const duration = style === 'light' ? 50 : style === 'heavy' ? 200 : 100;
          navigator.vibrate(duration);
        }
      }
    },

    ready: () => {
      if (isTelegram) {
        telegram.ready();
      } else {
        console.log('Web fallback: ready');
      }
    },

    setHeaderColor: (color: 'bg_color' | 'secondary_bg_color' | `#${string}`) => {
      if (isTelegram) {
        telegram.setHeaderColor(color);
      } else {
        console.log('Web fallback: setHeaderColor', color);
      }
    },

    openTelegramLink: (url: string) => {
      if (isTelegram) {
        telegram.openTelegramLink(url);
      } else {
        // For web, open in new tab
        window.open(url, '_blank');
      }
    },

    shareMessage: (msgId: string, callback?: (success: boolean) => void) => {
      if (isTelegram) {
        telegram.shareMessage(msgId, callback);
      } else {
        // Web fallback - could use Web Share API
        if (navigator.share) {
          navigator
            .share({ text: msgId })
            .then(() => callback?.(true))
            .catch(() => callback?.(false));
        } else {
          callback?.(false);
        }
      }
    },

    openLink: (url: string) => {
      if (isTelegram) {
        telegram.openLink(url);
      } else {
        window.open(url, '_blank');
      }
    },

    disableVerticalSwipes: () => {
      if (isTelegram) {
        telegram.disableVerticalSwipes();
      } else {
        console.log('Web fallback: disableVerticalSwipes');
      }
    },
  };

  // Detect mobile vs desktop Telegram
  const isTelegramMobile = isTelegram && (telegramPlatform === 'android' || telegramPlatform === 'ios');
  const isTelegramDesktop = isTelegram && (telegramPlatform === 'tdesktop' || telegramPlatform === 'macos');

  return {
    // Platform state
    isTelegram,
    isWeb,
    platform,
    isTelegramMobile,
    isTelegramDesktop,

    // Actions with fallbacks
    ...webFallbacks,

    // Direct telegram properties (with fallbacks)
    colorScheme: isTelegram ? telegram.colorScheme : undefined,
    telegramPlatform: telegramPlatform,
    headerColor: isTelegram ? telegram.headerColor : '',
    webAppInitData: webAppInitData,
  };
}
