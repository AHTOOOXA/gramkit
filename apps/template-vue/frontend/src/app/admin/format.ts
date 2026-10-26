/**
 * Small display helpers shared by the admin screens (users list, user detail,
 * panels, audit log). Pure functions — no i18n inside; callers translate.
 */

export type RoleBadgeVariant = 'default' | 'secondary' | 'destructive';

/** Badge colour per role: owner stands out, admin is primary, user is muted. */
export const roleVariant = (role: string): RoleBadgeVariant => {
  if (role === 'owner') return 'destructive';
  if (role === 'admin') return 'default';
  return 'secondary';
};

/** Locale date (or date + time) for an ISO string; '—' when missing, raw when unparsable. */
export const formatDate = (iso: string | null | undefined, withTime = false): string => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return withTime ? d.toLocaleString() : d.toLocaleDateString();
};

/** Best human label for a user row: app username, Telegram username, display name, then id. */
export const userLabel = (user: {
  id?: string;
  username?: string | null;
  tg_username?: string | null;
  display_name?: string | null;
}): string => user.username ?? user.tg_username ?? user.display_name ?? user.id ?? '—';
