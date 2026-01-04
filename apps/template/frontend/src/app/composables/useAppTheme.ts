import { computed, watch, type ComputedRef } from 'vue';
import { useTelegram } from '@core/platform';
import { mode } from '@app/store/theme';
import { getBackgroundColorFromCSS } from '@app/utils/theme-colors';

export type Theme = 'light' | 'dark' | 'auto';

export interface UseAppThemeReturn {
  theme: ComputedRef<string>;
  resolvedTheme: ComputedRef<string>;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  applyTheme: (theme: Theme) => void;
}

/**
 * Enhanced theme management composable that integrates VueUse's useColorMode with Telegram SDK.
 *
 * Features:
 * - Theme state management via @vueuse/core (with automatic persistence)
 * - Toggle between light → dark → auto
 * - Apply theme with Telegram header color sync (using actual CSS background color)
 * - Automatic header color updates on theme changes
 */
export function useAppTheme(): UseAppThemeReturn {
  const telegram = useTelegram();

  // Compute resolved theme (what is actually applied)
  const resolvedTheme = computed(() => {
    if (mode.value === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return mode.value;
  });

  /**
   * Update Telegram header color based on actual CSS background color
   */
  const updateHeaderColor = (resolvedThemeValue: string) => {
    if (!resolvedThemeValue) {
      return;
    }

    // Wait a tick for CSS variables to update after theme change
    requestAnimationFrame(() => {
      const isDark = resolvedThemeValue === 'dark';
      const hexColor = getBackgroundColorFromCSS(isDark);
      try {
        telegram.setHeaderColor(hexColor as `#${string}`);
      } catch (e) {
        console.error('[useAppTheme] Failed to set header color:', e);
      }
    });
  };

  /**
   * Sync header color when resolved theme changes
   */
  watch(
    resolvedTheme,
    (newResolvedTheme) => {
      updateHeaderColor(newResolvedTheme);
    },
    { immediate: true }
  );

  /**
   * Toggle theme: light → dark → auto → light
   */
  const toggleTheme = () => {
    const themes: Theme[] = ['light', 'dark', 'auto'];
    const currentTheme = (mode.value as Theme) ?? 'auto';
    const currentIndex = themes.indexOf(currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    const nextTheme = themes[nextIndex];
    if (nextTheme) {
      mode.value = nextTheme;
    }
  };

  /**
   * Apply theme and update Telegram header color
   */
  const applyTheme = (newTheme: Theme) => {
    mode.value = newTheme;
    // Header color will be updated by the watcher when resolvedTheme changes
  };

  /**
   * Wrapper for setTheme to ensure type safety
   */
  const setTheme = (newTheme: Theme) => {
    mode.value = newTheme;
  };

  return {
    theme: computed(() => mode.value),
    resolvedTheme,
    setTheme,
    toggleTheme,
    applyTheme,
  };
}
