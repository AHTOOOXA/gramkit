import { type ComponentType } from 'react';

import { appUserPanels } from './app-userPanels';

/** Props every user-detail panel receives. */
export interface AdminUserPanelProps {
  userId: string;
  /** Call after the panel changed the user (a refund, a grant). */
  onMutated: () => void;
}

/**
 * Tabs on the admin user detail page (`/admin/users/[id]`).
 *
 * The detail page wraps each `loader` in `React.lazy` once and renders it in a
 * `Suspense` boundary with the `userId` prop. A panel that changes the user
 * calls `onMutated`; the detail page then refetches the profile and every
 * `/admin/users/:user_id/...` query, so the other panels refresh too. Panel
 * modules default-export the component.
 *
 * To add a panel, append it to `appUserPanels` in `./app-userPanels.ts`. Same
 * shape (`key`, `labelKey`, `loader`) as template-vue's `app/admin/userPanels.ts`.
 *
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export interface AdminUserPanel {
  /** Stable tab value. */
  key: string;
  /** Full i18n key of the tab label. */
  labelKey: string;
  /** Lazy panel component (what `() => import('…')` returns). */
  loader: () => Promise<{ default: ComponentType<AdminUserPanelProps> }>;
}

export const coreUserPanels: AdminUserPanel[] = [
  {
    key: 'payments',
    labelKey: 'admin.users.tabs.payments',
    loader: () => import('@/components/admin/users/AdminUserPaymentsPanel'),
  },
  {
    key: 'subscriptions',
    labelKey: 'admin.users.tabs.subscriptions',
    loader: () =>
      import('@/components/admin/users/AdminUserSubscriptionsPanel'),
  },
];

export { appUserPanels };

export const adminUserPanels: AdminUserPanel[] = [
  ...coreUserPanels,
  ...appUserPanels,
];
