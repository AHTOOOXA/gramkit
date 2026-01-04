'use client';

import { useTranslations } from 'next-intl';
import { Logo } from '@/components/shared/logo';

/**
 * Footer for marketing/public pages
 *
 * Full footer with logo, copyright, and legal links.
 * Adds bottom padding on mobile to account for fixed bottom navigation.
 */
export function Footer() {
  const t = useTranslations();

  return (
    <footer className="border-t bg-muted/30 pb-[var(--bottom-nav-height)] md:pb-0">
      <div className="max-w-[var(--page-max-width)] mx-auto px-[var(--page-padding-x)] py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <Logo size="sm" showText={true} />
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} {t('app.name')}. {t('footer.rights')}
          </p>
        </div>
      </div>
    </footer>
  );
}
