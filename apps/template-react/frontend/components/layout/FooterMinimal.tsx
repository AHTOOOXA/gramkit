'use client';

import { useTranslations } from 'next-intl';

/**
 * Minimal footer for auth/checkout flows
 *
 * Minimal distraction - just copyright and essential links
 */
export function FooterMinimal() {
  const t = useTranslations();

  return (
    <footer className="border-t py-4 text-center text-xs text-muted-foreground">
      <p>
        © {new Date().getFullYear()} {t('app.name')}
      </p>
    </footer>
  );
}
