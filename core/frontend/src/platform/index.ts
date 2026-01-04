export { default as useTelegram } from './useTelegram';
export { usePlatform } from './usePlatform';
export type { PlatformState, PlatformActions, UsePlatformReturn } from './usePlatform';
export {
  usePlatformMock,
  initPlatformMock,
  injectMockInitData,
  createMockInitDataString,
  getSelectedMockUser,
  isMockModeEnabled,
} from './usePlatformMock';
export type { MockUser, UsePlatformMockReturn } from './usePlatformMock';
