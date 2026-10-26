import { AdminShell } from '@/components/admin/AdminShell';
import { AppShell } from '@/components/shells';

/**
 * The `/admin` layout: the wide AppShell (its own route group, because the
 * `(app)` layout hardwires the default width) around `AdminShell` (title,
 * section tabs, role guard). Next keeps it mounted across child navigation.
 * `proxy.ts` sends guests to /login; roles are checked in `AdminShell` and on
 * the backend.
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
