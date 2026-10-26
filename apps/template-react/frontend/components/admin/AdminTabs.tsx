'use client';

import { useTranslations } from 'next-intl';

import { cn } from '@/lib/utils';
import { adminSections, type AdminSection } from '@/config/admin/sections';
import { Link, usePathname } from '@/i18n/navigation';

/**
 * AdminTabs — the admin sub-navigation, built from the section registry
 * (`@/config/admin/sections`): every section gets a tab, so a new section never
 * needs an edit here. Active state is a prefix match on the (locale-less) path
 * (Users stays lit on /admin/users/[id]), or an exact match when the section
 * sets `exact`. Scrolls sideways when the tabs don't fit a phone.
 *
 * Port of template-vue's `AdminTabs.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function AdminTabs() {
  const t = useTranslations();
  const pathname = usePathname();

  const isActive = (section: AdminSection) =>
    section.exact
      ? pathname === section.href
      : pathname === section.href || pathname.startsWith(`${section.href}/`);

  return (
    <nav className="border-border -mx-[var(--page-padding-x)] flex [scrollbar-width:none] gap-1 overflow-x-auto border-b px-[var(--page-padding-x)] md:mx-0 md:px-0">
      {adminSections.map((section) => {
        const active = isActive(section);
        return (
          <Link
            key={section.id}
            href={section.href}
            aria-current={active ? 'page' : undefined}
            className={cn(
              '-mb-px border-b-2 px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors',
              active
                ? 'border-primary text-foreground'
                : 'text-muted-foreground hover:text-foreground border-transparent'
            )}
          >
            {t(section.labelKey)}
          </Link>
        );
      })}
    </nav>
  );
}
