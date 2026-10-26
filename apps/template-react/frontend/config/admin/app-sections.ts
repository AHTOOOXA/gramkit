import type { AdminSection } from './sections';

/**
 * App-specific admin sections, appended after the core ones (Overview, Users,
 * Analytics, Audit log, Tasks, Broadcasts, Marketing).
 *
 * Each one needs a page file: `app/[locale]/(admin)/admin/<path>/page.tsx`
 * (a `'use client'` page; the `/admin` layout already renders the shell, the
 * tabs and the role guard around it).
 *
 * Backend: put the endpoints in this app's admin router (same `/admin` prefix
 * and `admin` tag). Paths under `/admin/users/<x>` need two or more segments
 * after `users/`, because the core router's `GET /admin/users/{user_id}`
 * matches first.
 *
 * @example
 * export const appAdminSections: AdminSection[] = [
 *   {
 *     id: 'reports',
 *     href: '/admin/reports', // app/[locale]/(admin)/admin/reports/page.tsx
 *     labelKey: 'admin.nav.reports', // add the key to en.json and ru.json
 *   },
 * ];
 */
export const appAdminSections: AdminSection[] = [];
