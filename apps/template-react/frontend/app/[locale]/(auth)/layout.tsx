import { AppShell } from '@/components/shells';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Middleware redirects authenticated users away from this route
  return <AppShell>{children}</AppShell>;
}
