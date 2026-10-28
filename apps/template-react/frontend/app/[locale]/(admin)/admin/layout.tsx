import { AdminShell } from '@/components/admin/AdminShell';
import { AppShell } from '@/components/shells';

/**
 * The `/admin` layout: the wide AppShell (its own route group, because the
 * `(app)` layout hardwires the default width) around `AdminShell` (title,
 * section tabs, role guard). Next keeps it mounted across child navigation.
 * Access is checked in `AdminShell` (non-admins, guests included, go home) and
 * on the backend (403); `proxy.ts` can't see the API's session cookie.
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AppShell variant="wide">
      <AdminShell>{children}</AdminShell>
    </AppShell>
  );
}
