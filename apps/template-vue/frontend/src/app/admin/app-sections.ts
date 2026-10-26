import type { AdminSection } from './sections';

/**
 * App-specific admin sections, appended after the core ones (Overview, Users,
 * Analytics, Audit log, Tasks, Broadcasts, Marketing).
 *
 * Backend: put the endpoints in this app's admin router (same `/admin` prefix
 * and `admin` tag). Paths under `/admin/users/<x>` need two or more segments
 * after `users/`, because the core router's `GET /admin/users/{user_id}`
 * matches first.
 *
 * @example
 * export const appAdminSections: AdminSection[] = [
 *   {
 *     name: 'admin-reports',
 *     path: 'reports',
 *     labelKey: 'admin.nav.reports', // add the key to en.json and ru.json
 *     loader: () => import('@app/presentation/screens/admin/AdminReports.vue'),
 *   },
 * ];
 */
export const appAdminSections: AdminSection[] = [];
