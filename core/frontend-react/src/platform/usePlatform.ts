import { useTelegram } from './useTelegram';
import { usePlatformMock, createMockInitDataString } from './usePlatformMock';

/** Telegram platform values from WebApp.platform */
export type TelegramPlatform = 'android' | 'ios' | 'tdesktop' | 'macos' | 'weba' | 'web' | 'unknown';

export interface UsePlatformReturn {
  isTelegram: boolean;
  isWeb: boolean;
  platform: 'telegram' | 'web';
  /** Specific Telegram platform: android, ios, tdesktop, macos, weba, web */
  tgPlatform: TelegramPlatform;
  /** True if Telegram on mobile device (android or ios) */
  isTelegramMobile: boolean;
  /** True if Telegram on desktop app (tdesktop or macos) */
  isTelegramDesktop: boolean;
  colorScheme: 'light' | 'dark';
  initData: string;
}

export function usePlatform(): UsePlatformReturn {
  const telegram = useTelegram();
  const platformMock = usePlatformMock();

  // Two INDEPENDENT debug switches (decoupled on purpose), stored in localStorage:
  //   tgMock   → report platform as Telegram, regardless of who you are.
  //   userMock → authenticate as the selected mock user, regardless of platform.
  // So you can log in as a real user while staying on the web platform.
  const tgMock = platformMock.isMockEnabled;
  const userMock = platformMock.isUserMockEnabled;

  let isTelegram: boolean;
  let isWeb: boolean;
  let platform: 'telegram' | 'web';
  let initData: string;

  // --- Platform: driven by TG mock only ---
  if (tgMock) {
    isTelegram = true;
    isWeb = false;
    platform = 'telegram';
  } else {
    // Normal platform detection based on Telegram SDK
    // Check if we have initData - this indicates real Telegram environment
    const hasInitData = Boolean(telegram.initData && telegram.initData.length > 0);
    isTelegram = hasInitData;
    isWeb = !hasInitData;
    platform = isTelegram ? 'telegram' : 'web';
  }

  // --- Auth (initData): driven by login-as only ---
  if (userMock && platformMock.selectedUser) {
    // Authenticate as the selected mock user (works on web or telegram platform).
    initData = createMockInitDataString(platformMock.selectedUser);
  } else {
    initData = telegram.initData;
  }

  // Get specific Telegram platform
  const tgPlatform = (telegram.platform || 'unknown') as TelegramPlatform;

  // Detect mobile vs desktop Telegram
  const isTelegramMobile = isTelegram && (tgPlatform === 'android' || tgPlatform === 'ios');
  const isTelegramDesktop = isTelegram && (tgPlatform === 'tdesktop' || tgPlatform === 'macos');

  return {
    isTelegram,
    isWeb,
    platform,
    tgPlatform,
    isTelegramMobile,
    isTelegramDesktop,
    colorScheme: telegram.colorScheme,
    initData,
  };
}
