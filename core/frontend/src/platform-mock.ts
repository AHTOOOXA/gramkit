/**
 * Mock platform utilities - SDK-free entry point
 *
 * Use this module for mock initialization BEFORE importing @core/platform.
 * This avoids the SDK import which freezes window.Telegram.WebApp.
 *
 * Usage in main.ts:
 *   import { initPlatformMock, injectMockInitData, ... } from '@core/platform-mock';
 *   // Initialize mock BEFORE other imports
 *   initPlatformMock(MOCK_USERS);
 *   if (isMockModeEnabled()) { ... }
 *
 *   // Now safe to import SDK-dependent modules
 *   import { usePlatform } from '@core/platform';
 */
export {
  usePlatformMock,
  initPlatformMock,
  injectMockInitData,
  createMockInitDataString,
  getSelectedMockUser,
  isMockModeEnabled,
} from './platform/usePlatformMock';
export type { MockUser, UsePlatformMockReturn } from './platform/usePlatformMock';
