import { AppShell } from '@/components/shells';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Middleware redirects unauthenticated users to login
  return <AppShell>{children}</AppShell>;
}
