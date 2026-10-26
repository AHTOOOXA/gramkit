import type { AdminUserPanel } from './userPanels';

/**
 * App-specific tabs on the admin user detail page, after Payments and
 * Subscriptions. A panel gets a `userId` prop and may emit `mutated`.
 *
 * @example
 * export const appUserPanels: AdminUserPanel[] = [
 *   {
 *     key: 'orders',
 *     labelKey: 'admin.users.tabs.orders', // add the key to en.json and ru.json
 *     loader: () => import('@app/presentation/components/admin/users/AdminUserOrdersPanel.vue'),
 *   },
 * ];
 */
export const appUserPanels: AdminUserPanel[] = [];
