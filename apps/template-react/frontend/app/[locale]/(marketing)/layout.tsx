import { AppShell } from '@/components/shells';
import { Footer } from '@/components/layout';

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell footer={<Footer />}>{children}</AppShell>;
}
