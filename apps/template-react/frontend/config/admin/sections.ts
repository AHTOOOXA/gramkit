import { appAdminSections } from './app-sections';

/**
 * Admin sections — the tabs `AdminTabs` renders under `/admin`.
 *
 * Next routes by file, so this registry drives the tabs only: each section is
 * a page file under `app/[locale]/(admin)/admin/<path>/page.tsx` (rendered
 * inside `AdminShell` by the `/admin` layout) plus an entry here. Detail pages
 * (`users/[id]`, …) need no entry; the prefix match keeps their tab lit.
 *
 * To add a screen, add its page file and append it to `appAdminSections` in
 * `./app-sections.ts`; this file holds the sections that ship with the
 * template (they call the core admin API). Same ids, order and i18n keys as
 * template-vue's `app/admin/sections.ts`.
 *
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export interface AdminSection {
  /** Stable key, e.g. 'users'. */
  id: string;
  /** Locale-less path of an existing page, e.g. '/admin/users'. */
  href: string;
  /** Full i18n key of the tab label, e.g. 'admin.nav.users'. */
  labelKey: string;
  /**
   * Tab active-state matching: exact path instead of prefix. Use it when the
   * section's path prefixes a sibling's (e.g. 'reports' vs 'reports/daily').
   */
  exact?: boolean;
}

export const coreAdminSections: AdminSection[] = [
  // First tab: `/admin` redirects here. Apps add KPI tiles to it on the server
  // (`register_overview_card` in the backend's `services/admin_metrics.py`).
  { id: 'overview', href: '/admin/overview', labelKey: 'admin.nav.overview' },
  { id: 'users', href: '/admin/users', labelKey: 'admin.nav.users' },
  {
    id: 'analytics',
    href: '/admin/analytics',
    labelKey: 'admin.nav.analytics',
  },
  { id: 'audit-log', href: '/admin/audit-log', labelKey: 'admin.nav.auditLog' },
  { id: 'tasks', href: '/admin/tasks', labelKey: 'admin.nav.tasks' },
  // The tab stays lit on new / detail / edit through the prefix match; Next
  // ranks the static `broadcasts/new` above `broadcasts/[id]`.
  {
    id: 'broadcasts',
    href: '/admin/broadcasts',
    labelKey: 'admin.nav.broadcasts',
  },
  {
    id: 'marketing',
    href: '/admin/marketing',
    labelKey: 'admin.nav.marketing',
  },
];

export { appAdminSections };

export const adminSections: AdminSection[] = [
  ...coreAdminSections,
  ...appAdminSections,
];
