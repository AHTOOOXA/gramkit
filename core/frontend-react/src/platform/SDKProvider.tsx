'use client';

import { type PropsWithChildren, useEffect } from 'react';
import {
  getSelectedMockUser,
  isMockModeEnabled,
  injectMockInitData,
} from './usePlatformMock';
import { getHeaderColorForScheme } from './theme-colors';

/**
 * SDKProvider - Initializes Telegram Mini App SDK
 *
 * Key optimizations:
 * 1. Calls ready() and expand() IMMEDIATELY using native API (no waiting)
 * 2. Does NOT block rendering - children render immediately
 * 3. SDK features (buttons, haptics) initialized in background
 * 4. No viewport.mount() wait - not needed for ready/expand
 */
export function SDKProvider({ children }: PropsWithChildren) {
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const tg = (window as any).Telegram?.WebApp;
    const isDebugMode = process.env.NEXT_PUBLIC_DEBUG === 'true';
    const hasRealTelegramData = !!tg?.initData;

    // Step 1: Inject mock data for development (before anything else)
    const mockEnabled = isMockModeEnabled() && !hasRealTelegramData && isDebugMode;
    if (mockEnabled) {
      const mockUser = getSelectedMockUser();
      if (mockUser) {
        injectMockInitData(mockUser);
      }
    }

    // Step 2: IMMEDIATELY call ready/expand using native API (instant, no SDK needed)
    if (tg) {
      // Set header color first (before showing app)
      try {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const headerColor = getHeaderColorForScheme(prefersDark);
        tg.setHeaderColor(headerColor);
        console.log('[SDKProvider] Header color set:', headerColor);
      } catch (e) {
        console.warn('[SDKProvider] Failed to set header color:', e);
      }

      // Expand to full height
      try {
        tg.expand();
        console.log('[SDKProvider] Expanded');
      } catch (e) {
        console.warn('[SDKProvider] Failed to expand:', e);
      }

      // Signal ready - hides Telegram's loading screen
      try {
        tg.ready();
        console.log('[SDKProvider] ✓ Ready signal sent');
      } catch (e) {
        console.warn('[SDKProvider] Failed to call ready:', e);
      }
    }

    // Step 3: Initialize SDK in background for advanced features (buttons, haptics, etc.)
    // This doesn't block rendering
    import('@tma.js/sdk')
      .then(({ init, miniApp, themeParams, backButton, mainButton }) => {
        try {
          init();

          // Mount components for later use (sync, instant)
          if (!miniApp.isMounted()) miniApp.mount();
          if (!themeParams.isMounted()) themeParams.mount();
          if (!backButton.isMounted()) backButton.mount();
          if (!mainButton.isMounted()) mainButton.mount();

          console.log('[SDKProvider] SDK components mounted');
        } catch (e) {
          // Not in Telegram or init failed - that's OK
          console.log('[SDKProvider] SDK init skipped (not in Telegram)');
        }
      })
      .catch(() => {
        // SDK import failed - app still works without it
      });
  }, []);

  // No loading screen - render children immediately!
  return <>{children}</>;
}
