/**
 * Fallback theme colors for Telegram Mini App header.
 * Used only if CSS color extraction fails.
 */
export const DEFAULT_THEME_COLORS = {
  light: '#eef1f4',
  dark: '#1c2230',
} as const;

export type ThemeColors = typeof DEFAULT_THEME_COLORS;

/**
 * Convert any CSS color to hex using Canvas (browsers normalize colors)
 */
function cssColorToHex(cssColor: string): string | null {
  if (typeof document === 'undefined') return null;

  try {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.fillStyle = cssColor;
    const normalizedColor = ctx.fillStyle; // Browser normalizes to #rrggbb or rgb()

    // Already hex
    if (normalizedColor.startsWith('#')) {
      return normalizedColor;
    }

    // Parse rgb(r, g, b)
    const match = /rgb\((\d+),\s*(\d+),\s*(\d+)\)/.exec(normalizedColor);
    if (match?.[1] && match[2] && match[3]) {
      const r = parseInt(match[1]).toString(16).padStart(2, '0');
      const g = parseInt(match[2]).toString(16).padStart(2, '0');
      const b = parseInt(match[3]).toString(16).padStart(2, '0');
      return `#${r}${g}${b}`;
    }
  } catch (e) {
    console.warn('[theme-colors] Failed to convert color:', e);
  }

  return null;
}

/**
 * Extract background color from CSS --background variable
 */
export function getBackgroundColorFromCSS(isDark: boolean): string {
  if (typeof document === 'undefined') {
    return isDark ? DEFAULT_THEME_COLORS.dark : DEFAULT_THEME_COLORS.light;
  }

  try {
    // Temporarily apply dark class if needed to read correct variable
    const root = document.documentElement;
    const hadDarkClass = root.classList.contains('dark');

    if (isDark && !hadDarkClass) {
      root.classList.add('dark');
    } else if (!isDark && hadDarkClass) {
      root.classList.remove('dark');
    }

    const computedStyle = getComputedStyle(root);
    const bgColor = computedStyle.getPropertyValue('--background').trim();

    // Restore original class
    if (isDark && !hadDarkClass) {
      root.classList.remove('dark');
    } else if (!isDark && hadDarkClass) {
      root.classList.add('dark');
    }

    if (bgColor) {
      const hex = cssColorToHex(bgColor);
      if (hex) {
        return hex;
      }
    }
  } catch (e) {
    console.warn('[theme-colors] Failed to extract from CSS:', e);
  }

  // Fallback
  return isDark ? DEFAULT_THEME_COLORS.dark : DEFAULT_THEME_COLORS.light;
}

/**
 * Get header color based on color scheme preference
 */
export function getHeaderColorForScheme(prefersDark: boolean): string {
  return getBackgroundColorFromCSS(prefersDark);
}
