import type { AdminUserPanel } from './userPanels';

/**
 * App-specific tabs on the admin user detail page, after Payments and
 * Subscriptions. A panel default-exports a component that gets `userId` and
 * `onMutated` (`AdminUserPanelProps`).
 *
 * @example
 * export const appUserPanels: AdminUserPanel[] = [
 *   {
 *     key: 'orders',
 *     labelKey: 'admin.users.tabs.orders', // add the key to en.json and ru.json
 *     loader: () => import('@/components/admin/users/AdminUserOrdersPanel'),
 *   },
 * ];
 */
export const appUserPanels: AdminUserPanel[] = [];
