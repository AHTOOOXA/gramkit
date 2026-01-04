/**
 * Layout configuration - single source of truth for app layout settings
 *
 * Change these values when creating a new app from template.
 */

/**
 * Mobile navigation layout style
 *
 * - 'bottom-tabs': iOS-style bottom navigation bar (default, best for consumer apps with 2-5 sections)
 * - 'hamburger': Minimal header with slide-out menu (best for admin/dashboard apps with many tabs)
 */
export type MobileLayout = 'bottom-tabs' | 'hamburger';

export const layoutConfig = {
  /**
   * Mobile navigation style
   *
   * 'bottom-tabs' - Fixed bottom navigation bar (consumer apps)
   * 'hamburger' - Header with hamburger menu (admin/dashboard apps)
   */
  mobileLayout: 'bottom-tabs' as MobileLayout,
} as const;
