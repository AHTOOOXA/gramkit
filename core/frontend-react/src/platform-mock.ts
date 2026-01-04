/**
 * Mock platform utilities - SDK-free entry point
 *
 * Use this module for mock initialization BEFORE importing @tma-platform/core-react/platform.
 * This avoids the SDK import which freezes window.Telegram.WebApp.
 *
 * Usage in providers.tsx:
 *   import { initPlatformMock, injectMockInitData, ... } from '@tma-platform/core-react/platform-mock';
 *   // Initialize mock BEFORE other imports
 *   initPlatformMock(MOCK_USERS);
 *   if (isMockModeEnabled()) { ... }
 *
 *   // Now safe to import SDK-dependent modules
 *   import { SDKProvider } from '@tma-platform/core-react/platform';
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
