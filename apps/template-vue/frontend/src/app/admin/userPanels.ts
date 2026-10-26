import type { Component } from 'vue';
import { appUserPanels } from './app-userPanels';

/**
 * Tabs on the admin user detail page (`AdminUserDetail`).
 *
 * Each panel is rendered with `defineAsyncComponent(panel.loader)` and receives
 * a `userId: string` prop. A panel that changes the user (a refund, a grant)
 * emits `mutated`; the detail page then refetches the profile and every
 * `/admin/users/:user_id/...` query, so the other panels refresh too.
 * To add a panel, append it to `appUserPanels` in `./app-userPanels.ts`.
 */
export interface AdminUserPanel {
  /** Stable tab value. */
  key: string;
  /** i18n key of the tab label. */
  labelKey: string;
  /** Lazy panel component (what `() => import('x.vue')` returns). */
  loader: () => Promise<{ default: Component }>;
}

export const coreUserPanels: AdminUserPanel[] = [
  {
    key: 'payments',
    labelKey: 'admin.users.tabs.payments',
    loader: () => import('@app/presentation/components/admin/users/AdminUserPaymentsPanel.vue'),
  },
  {
    key: 'subscriptions',
    labelKey: 'admin.users.tabs.subscriptions',
    loader: () => import('@app/presentation/components/admin/users/AdminUserSubscriptionsPanel.vue'),
  },
];

export { appUserPanels };

export const adminUserPanels: AdminUserPanel[] = [...coreUserPanels, ...appUserPanels];
