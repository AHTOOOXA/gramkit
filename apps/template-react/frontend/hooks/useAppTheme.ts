'use client';

import { useCallback, useEffect } from 'react';
import {
  useTelegram,
  getBackgroundColorFromCSS,
} from '@tma-platform/core-react/platform';
import { useTheme } from 'next-themes';

type Theme = 'light' | 'dark' | 'system';

export interface UseAppThemeReturn {
  theme: string | undefined;
  resolvedTheme: string | undefined;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  applyTheme: (theme: Theme) => void;
}

/**
 * Enhanced theme management hook that integrates next-themes with Telegram SDK.
 *
 * Features:
 * - Theme state management via next-themes (with automatic persistence)
 * - Toggle between light → dark → system
 * - Apply theme with Telegram header color sync (using actual CSS background color)
 * - Automatic header color updates on theme changes
 */
export function useAppTheme(): UseAppThemeReturn {
  const { theme, setTheme: setNextTheme, resolvedTheme } = useTheme();
  const telegram = useTelegram();

  console.log('[useAppTheme] Render', { theme, resolvedTheme });

  /**
   * Update Telegram header color based on actual CSS background color
   */
  const updateHeaderColor = useCallback(
    (resolvedThemeValue: string | undefined) => {
      console.log('[useAppTheme] updateHeaderColor called', { resolvedThemeValue });

      if (!resolvedThemeValue) {
        console.log('[useAppTheme] No resolved theme yet, skipping');
        return;
      }

      // Wait a tick for CSS variables to update after theme change
      requestAnimationFrame(() => {
        const isDark = resolvedThemeValue === 'dark';
        const hexColor = getBackgroundColorFromCSS(isDark);
        console.log('[useAppTheme] Got background color:', hexColor);
        try {
          telegram.setHeaderColor(hexColor);
          telegram.setBackgroundColor(hexColor);
          console.log('[useAppTheme] ✓ Header and background color set to:', hexColor);
        } catch (e) {
          console.error('[useAppTheme] Failed to set colors:', e);
        }
      });
    },
    [telegram]
  );

  /**
   * Sync header color when resolved theme changes
   */
  useEffect(() => {
    console.log('[useAppTheme] useEffect triggered, resolvedTheme:', resolvedTheme);
    updateHeaderColor(resolvedTheme);
  }, [resolvedTheme, updateHeaderColor]);

  /**
   * Toggle theme: light → dark → system → light
   */
  const toggleTheme = useCallback(() => {
    const themes: Theme[] = ['light', 'dark', 'system'];
    const currentTheme = (theme as Theme | undefined) ?? 'system';
    const currentIndex = themes.indexOf(currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    const nextTheme = themes[nextIndex];
    if (nextTheme) {
      setNextTheme(nextTheme);
    }
  }, [theme, setNextTheme]);

  /**
   * Apply theme and update Telegram header color
   */
  const applyTheme = useCallback(
    (newTheme: Theme) => {
      setNextTheme(newTheme);
      // Header color will be updated by the effect when resolvedTheme changes
    },
    [setNextTheme]
  );

  /**
   * Wrapper for setTheme to ensure type safety
   */
  const setTheme = useCallback(
    (newTheme: Theme) => {
      setNextTheme(newTheme);
    },
    [setNextTheme]
  );

  return {
    theme,
    resolvedTheme,
    setTheme,
    toggleTheme,
    applyTheme,
  };
}
