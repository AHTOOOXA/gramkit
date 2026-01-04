'use client';

import { useEffect } from 'react';

/**
 * Detects platform (Telegram vs Web) and stores in cookie
 * Runs once on app load, cookie persists for 1 year
 *
 * IMPORTANT: Respects mock mode state from localStorage
 * - Mock ON: Treat as Telegram (window.Telegram.WebApp injected by mock)
 * - Mock OFF: Treat as Web (even if window.Telegram.WebApp exists from previous mock session)
 */
export function PlatformDetector() {
  useEffect(() => {
    // Determine platform based on localStorage mock state
    // localStorage is the SOURCE OF TRUTH for development mode
    let platform: 'telegram' | 'web';

    const mockState =
      typeof window !== 'undefined'
        ? localStorage.getItem('telegram-platform-mock')
        : null;

    if (mockState === 'true') {
      // Mock explicitly enabled - treat as Telegram
      platform = 'telegram';
    } else if (mockState === 'false') {
      // Mock explicitly disabled - ALWAYS treat as Web
      // Ignore window.Telegram.WebApp as it may be stale from previous session
      platform = 'web';
    } else {
      // No mock state set (first load) - detect from Telegram WebApp
      const telegram =
        typeof window !== 'undefined' ? window.Telegram : undefined;
      const webApp = telegram?.WebApp;
      const hasRealTelegramEnv = webApp?.initData !== undefined;
      platform = hasRealTelegramEnv ? 'telegram' : 'web';
    }

    // Set app-namespaced cookie for server-side access
    // Prevents conflicts between apps on same domain
    const cookieName = `${process.env.APP_NAME ?? 'app'}-platform`;
    document.cookie = `${cookieName}=${platform}; path=/; max-age=31536000; samesite=lax`;

    // Log for debugging (always in dev, respects NEXT_PUBLIC_DEBUG in prod)
    if (
      process.env.NODE_ENV === 'development' ||
      process.env.NEXT_PUBLIC_DEBUG === 'true'
    ) {
      console.log(
        `[PlatformDetector] Platform detected: ${platform} (mockState: ${mockState ?? 'null'})`
      );
    }
  }, []); // Run once on mount

  // Component renders nothing
  return null;
}
