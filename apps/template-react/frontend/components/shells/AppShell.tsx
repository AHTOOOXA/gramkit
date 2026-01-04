'use client';

import { cn } from '@/lib/utils';
import { usePlatform } from '@/hooks';
import { AppNav } from '@/components/navigation/AppNav';
import { layoutConfig } from '@/config/layout';

const variantClasses = {
  default: 'max-w-[var(--page-max-width)]',
  wide: 'max-w-[90rem]',
  narrow: 'max-w-[40rem]',
  full: 'w-full',
} as const;

export interface AppShellProps {
  children: React.ReactNode;
  /** Optional footer slot (pass <Footer /> or <FooterMinimal />) */
  footer?: React.ReactNode;
  /** Content width variant (default: 'default') */
  variant?: keyof typeof variantClasses;
}

/**
 * AppShell - Unified layout wrapper for all pages
 *
 * Provides:
 * - AppNav (handles guest/auth, desktop/mobile automatically)
 * - Responsive content area with width variants
 * - Optional footer slot
 *
 * Usage:
 * - Marketing pages: <AppShell footer={<Footer />}>
 * - Auth pages: <AppShell footer={<FooterMinimal />}> or <AppShell>
 * - App pages: <AppShell>
 * - Admin pages: <AppShell variant="wide">
 */
export function AppShell({
  children,
  footer,
  variant = 'default'
}: AppShellProps) {
  const { isTelegramMobile } = usePlatform();
  const { mobileLayout } = layoutConfig;

  // Telegram Mini App on mobile device with bottom tabs: reduce top padding
  const useMobilePadding = isTelegramMobile && mobileLayout === 'bottom-tabs';

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <AppNav />
      <main className={cn(
        'flex-1 w-full mx-auto px-[var(--page-padding-x)] py-[var(--page-padding-y)] pb-[var(--bottom-nav-height)] md:pb-[var(--page-padding-y)]',
        variantClasses[variant],
        useMobilePadding && 'pt-2'
      )}>
        {children}
      </main>
      {footer}
    </div>
  );
}
