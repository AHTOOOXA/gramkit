import { useTelegram } from './useTelegram';
import { usePlatformMock } from './usePlatformMock';

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

  // Check if mock mode is enabled (development mode only)
  // Mock mode is controlled via debug panel and stored in localStorage
  const isMockMode = platformMock.isMockEnabled;

  let isTelegram: boolean;
  let isWeb: boolean;
  let platform: 'telegram' | 'web';
  let initData: string;

  if (isMockMode) {
    // Mock mode enabled - treat as Telegram platform
    isTelegram = true;
    isWeb = false;
    platform = 'telegram';
    // Use mock initData from the selected mock user
    initData = telegram.initData || '';
  } else {
    // Normal platform detection based on Telegram SDK
    // Check if we have initData - this indicates real Telegram environment
    const hasInitData = Boolean(telegram.initData && telegram.initData.length > 0);
    isTelegram = hasInitData;
    isWeb = !hasInitData;
    platform = isTelegram ? 'telegram' : 'web';
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
