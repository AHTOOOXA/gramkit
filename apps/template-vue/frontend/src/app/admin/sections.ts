import type { Component } from 'vue';
import { appAdminSections } from './app-sections';

/**
 * Admin sections — the single list the admin router and `AdminTabs` read.
 *
 * Each entry becomes a child route of `/admin` (rendered inside `AdminShell`).
 * Entries with a `labelKey` also get a tab. To add a screen, append it to
 * `appAdminSections` in `./app-sections.ts`; this file holds the sections that
 * ship with the template (they call the core admin API).
 */
export interface AdminSection {
  /** Route name, e.g. 'admin-users'. */
  name: string;
  /** Child path under `/admin`, e.g. 'users' or 'users/:id'. */
  path: string;
  /** i18n key of the tab label. Set it to show the section in `AdminTabs`. */
  labelKey?: string;
  /** Lazy screen component (what `() => import('x.vue')` returns). */
  loader: () => Promise<{ default: Component }>;
  /**
   * Tab active-state matching: exact path instead of prefix. Use it when the
   * section's path prefixes a sibling's (e.g. 'reports' vs 'reports/daily').
   */
  exact?: boolean;
}

export const coreAdminSections: AdminSection[] = [
  // First tab: `/admin` redirects here. Apps add KPI tiles to it on the server
  // (`register_overview_card` in the backend's `services/admin_metrics.py`).
  {
    name: 'admin-overview',
    path: 'overview',
    labelKey: 'admin.nav.overview',
    loader: () => import('@app/presentation/screens/admin/AdminOverview.vue'),
  },
  {
    name: 'admin-users',
    path: 'users',
    labelKey: 'admin.nav.users',
    loader: () => import('@app/presentation/screens/admin/AdminUsers.vue'),
  },
  {
    name: 'admin-user-detail',
    path: 'users/:id',
    loader: () => import('@app/presentation/screens/admin/AdminUserDetail.vue'),
  },
  {
    name: 'admin-analytics',
    path: 'analytics',
    labelKey: 'admin.nav.analytics',
    loader: () => import('@app/presentation/screens/admin/AdminAnalytics.vue'),
  },
  {
    name: 'admin-audit-log',
    path: 'audit-log',
    labelKey: 'admin.nav.auditLog',
    loader: () => import('@app/presentation/screens/admin/AdminAuditLog.vue'),
  },
  {
    name: 'admin-tasks',
    path: 'tasks',
    labelKey: 'admin.nav.tasks',
    loader: () => import('@app/presentation/screens/admin/AdminTasks.vue'),
  },
  // Broadcasts: the tab stays lit on new / detail / edit through the prefix
  // match, and vue-router ranks the static 'broadcasts/new' above 'broadcasts/:id'.
  {
    name: 'admin-broadcasts',
    path: 'broadcasts',
    labelKey: 'admin.nav.broadcasts',
    loader: () => import('@app/presentation/screens/admin/BroadcastsList.vue'),
  },
  {
    name: 'admin-broadcast-new',
    path: 'broadcasts/new',
    loader: () => import('@app/presentation/screens/admin/BroadcastComposer.vue'),
  },
  {
    name: 'admin-broadcast-detail',
    path: 'broadcasts/:id',
    loader: () => import('@app/presentation/screens/admin/BroadcastDetail.vue'),
  },
  {
    name: 'admin-broadcast-edit',
    path: 'broadcasts/:id/edit',
    loader: () => import('@app/presentation/screens/admin/BroadcastComposer.vue'),
  },
  {
    name: 'admin-marketing',
    path: 'marketing',
    labelKey: 'admin.nav.marketing',
    loader: () => import('@app/presentation/screens/admin/AdminMarketingLinks.vue'),
  },
];

export { appAdminSections };

export const adminSections: AdminSection[] = [...coreAdminSections, ...appAdminSections];
