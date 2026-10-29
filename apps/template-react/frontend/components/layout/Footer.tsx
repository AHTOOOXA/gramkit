'use client';

import { useTranslations } from 'next-intl';

import { Logo } from '@/components/shared/logo';
import { GITHUB_URL, VUE_DEMO_URL } from '@/config/constants';

/**
 * Footer for marketing/public pages
 *
 * Logo, copyright and the project links (repo, changelog, license, the Vue demo).
 * Adds bottom padding on mobile to account for fixed bottom navigation.
 */
export function Footer() {
  const t = useTranslations('footer');

  const links = [
    { href: GITHUB_URL, label: t('github') },
    { href: `${GITHUB_URL}/blob/main/CHANGELOG.md`, label: t('changelog') },
    { href: `${GITHUB_URL}/blob/main/LICENSE`, label: t('license') },
    { href: VUE_DEMO_URL, label: t('vueDemo') },
  ];

  return (
    <footer className="bg-muted/30 border-t pb-[var(--bottom-nav-height)] md:pb-0">
      <div className="mx-auto max-w-[var(--page-max-width)] px-[var(--page-padding-x)] py-8">
        <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
          <Logo size="sm" showText={true} />
          <nav className="text-muted-foreground flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm">
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground transition-colors"
              >
                {link.label}
              </a>
            ))}
            <span>© {new Date().getFullYear()} Gramkit</span>
          </nav>
        </div>
      </div>
    </footer>
  );
}
