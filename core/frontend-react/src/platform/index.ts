export { useTelegram, type UseTelegramReturn } from './useTelegram';
export { usePlatform, type UsePlatformReturn } from './usePlatform';
export { SDKProvider } from './SDKProvider';
export {
  usePlatformMock,
  initPlatformMock,
  injectMockInitData,
  createMockInitDataString,
  getSelectedMockUser,
  isMockModeEnabled,
  type MockUser,
  type UsePlatformMockReturn,
} from './usePlatformMock';
export {
  DEFAULT_THEME_COLORS,
  getHeaderColorForScheme,
  getBackgroundColorFromCSS,
  type ThemeColors,
} from './theme-colors';
