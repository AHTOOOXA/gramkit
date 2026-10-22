import useTelegram from './useTelegram';
import { usePlatformMock, createMockInitDataString } from './usePlatformMock';

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
  showConfirm: (message: string) => Promise<boolean>;
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
  /** Telegram WebView background (pre-paint, iOS overscroll). Bot API 6.1+; no-op on web / older clients. */
  setBackgroundColor: (color: 'bg_color' | 'secondary_bg_color' | `#${string}`) => void;
  /** Telegram bottom bar behind the native Main/Secondary buttons. Bot API 7.10+; no-op on web / older clients. */
  setBottomBarColor: (color: 'bg_color' | 'secondary_bg_color' | 'bottom_bar_bg_color' | `#${string}`) => void;
  webAppInitData: string;
  openTelegramLink: (url: string) => void;
  shareMessage: (msgId: string, callback?: (success: boolean) => void) => void;
  openLink: (url: string) => void;
  disableVerticalSwipes: () => void;
  enableClosingConfirmation: () => void;
  disableClosingConfirmation: () => void;
}

export type UsePlatformReturn = PlatformState & PlatformActions;

/**
 * Platform detection and abstraction layer
 * Wraps useTelegram and provides platform-aware functionality
 */
export function usePlatform(): UsePlatformReturn {
  const telegram = useTelegram();
  const platformMock = usePlatformMock();

  // Two INDEPENDENT debug switches (decoupled on purpose):
  //   tgMock   → report platform as Telegram (iOS), regardless of who you are.
  //   userMock → authenticate as the selected mock user, regardless of platform.
  // So you can log in as a real user while staying on the web platform.
  const isDebug = import.meta.env.VITE_DEBUG === 'true';
  const tgMock = isDebug && platformMock.isMockEnabled.value;
  const userMock = isDebug && platformMock.isUserMockEnabled.value;

  // Detect if we're in Telegram Mini App or web browser
  let isTelegram: boolean;
  let isWeb: boolean;
  let platform: 'telegram' | 'web';
  let telegramPlatform: typeof telegram.platform;
  let webAppInitData: string;

  // --- Platform: driven by TG mock only ---
  if (tgMock) {
    // Mock a Telegram iOS environment.
    isTelegram = true;
    isWeb = false;
    platform = 'telegram';
    telegramPlatform = 'ios';
  } else {
    // Normal platform detection.
    isTelegram = telegram.platform !== 'unknown' && !!telegram.webAppInitData;
    isWeb = !isTelegram;
    platform = isTelegram ? 'telegram' : 'web';
    telegramPlatform = telegram.platform;
  }

  // --- Auth (initData): driven by login-as only ---
  if (userMock) {
    // Authenticate as the selected mock user (works on web or telegram platform).
    const selectedUser = platformMock.selectedUser.value;
    webAppInitData = selectedUser
      ? createMockInitDataString(selectedUser)
      : createMockInitDataString({
          user_id: 123456789,
          username: 'ReallyCoolSupport',
          display_name: 'Really Cool Support',
          user_type: 'REGISTERED',
        });
  } else {
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

    showConfirm: (message: string): Promise<boolean> => {
      if (isTelegram) {
        return telegram.showConfirm(message);
      }
      // Web fallback — native confirm is reliable outside the Telegram WebView.
      return Promise.resolve(window.confirm(message));
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

    setBackgroundColor: (color: 'bg_color' | 'secondary_bg_color' | `#${string}`) => {
      // Web: the page's own background is the canvas — nothing to set.
      if (isTelegram) telegram.setBackgroundColor(color);
    },

    setBottomBarColor: (color: 'bg_color' | 'secondary_bg_color' | 'bottom_bar_bg_color' | `#${string}`) => {
      if (isTelegram) telegram.setBottomBarColor(color);
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

    enableClosingConfirmation: () => {
      if (isTelegram) {
        telegram.enableClosingConfirmation();
      } else {
        console.log('Web fallback: enableClosingConfirmation');
      }
    },

    disableClosingConfirmation: () => {
      if (isTelegram) {
        telegram.disableClosingConfirmation();
      } else {
        console.log('Web fallback: disableClosingConfirmation');
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
