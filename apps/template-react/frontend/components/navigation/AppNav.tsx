'use client';

import { useState } from 'react';
import { Menu, X, Lock } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { cn } from '@/lib/utils';
import { Link, usePathname } from '@/i18n/navigation';
import { Logo } from '@/components/shared/logo';
import { LanguageToggle } from '@/components/shared/language-toggle';
import { ThemeToggle } from '@/components/shared/theme-toggle';
import { ProfileDropdown } from '@/components/shared/profile-dropdown';
import { Button } from '@/components/ui/button';
import { useAuth, usePlatform } from '@/hooks';
import { getVisibleNavItems, authCtaItem } from '@/config/navigation';
import { layoutConfig } from '@/config/layout';

const ICON_SIZE = 22;

/**
 * AppNav - Main application navigation component
 *
 * Renders desktop header + mobile navigation (bottom tabs or hamburger menu).
 * Reads nav items from config/navigation.ts and filters by user access level.
 * Mobile layout style is configured in config/layout.ts.
 */
export function AppNav() {
  const { mobileLayout } = layoutConfig;
  const pathname = usePathname();
  const t = useTranslations();
  const [menuOpen, setMenuOpen] = useState(false);
  const { isAuthenticated, isAdmin, isOwner } = useAuth();
  const { isTelegramMobile } = usePlatform();

  // Extra bottom padding for Telegram Mini App on mobile device with bottom tabs
  const useTelegramMobilePadding = isTelegramMobile && mobileLayout === 'bottom-tabs';

  const { mainNav, mobileNav, showLoginCta } = getVisibleNavItems({
    isAuthenticated,
    isAdmin,
    isOwner,
  });

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <>
      {/* Mobile: Bottom nav (only shown when mobileLayout='bottom-tabs') */}
      {mobileLayout === 'bottom-tabs' && (
        <nav className={cn(
          'fixed bottom-0 left-0 right-0 z-50 bg-background border-t md:hidden',
          useTelegramMobilePadding && 'pb-4'
        )}>
          <div
            className="grid gap-1 px-4"
            style={{ gridTemplateColumns: `repeat(${String(mobileNav.length + (showLoginCta ? 1 : 0))}, 1fr)` }}
          >
            {mobileNav.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              const isLocked = item.lockedForGuests && !isAuthenticated;
              const linkHref = isLocked ? '/login' : item.href;
              return (
                <Link
                  key={item.id}
                  href={linkHref}
                  className={cn(
                    'flex flex-col items-center justify-center gap-1 py-3 transition-colors',
                    active ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
                    isLocked && 'opacity-75'
                  )}
                >
                  <Icon size={ICON_SIZE} className="shrink-0" />
                  <span className="text-[11px] leading-4 font-medium flex items-center gap-0.5">
                    {t(item.labelKey)}
                    {isLocked && <Lock size={8} />}
                  </span>
                </Link>
              );
            })}
            {showLoginCta && (
              <Link
                href={authCtaItem.href}
                className="flex flex-col items-center justify-center gap-1 py-3 transition-colors text-primary hover:text-primary/80"
              >
                <authCtaItem.icon size={ICON_SIZE} className="shrink-0" />
                <span className="text-[11px] leading-4 font-medium">{t(authCtaItem.labelKey)}</span>
              </Link>
            )}
          </div>
        </nav>
      )}

      {/* Mobile: Hamburger header (only shown when mobileLayout='hamburger') */}
      {mobileLayout === 'hamburger' && (
        <header className="fixed top-0 left-0 right-0 z-50 border-b bg-background md:hidden">
          <div className="w-full px-4 flex h-14 items-center justify-between">
            <Logo size="sm" showText={true} />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setMenuOpen(!menuOpen); }}
              aria-label={menuOpen ? t('nav.closeMenu') : t('nav.openMenu')}
              className="cursor-pointer"
            >
              {menuOpen ? <X size={24} /> : <Menu size={24} />}
            </Button>
          </div>

          {/* Mobile Menu Content - dropdown below header */}
          {menuOpen && (
            <div className="border-t bg-background">
              <div className="p-2">
                {mainNav.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);
                  const isLocked = item.lockedForGuests && !isAuthenticated;
                  const linkHref = isLocked ? '/login' : item.href;
                  return (
                    <Link
                      key={item.id}
                      href={linkHref}
                      onClick={() => { setMenuOpen(false); }}
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors',
                        active
                          ? 'bg-accent text-accent-foreground'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                        isLocked && 'opacity-75'
                      )}
                    >
                      <Icon size={16} />
                      <span className="flex items-center gap-1">
                        {t(item.labelKey)}
                        {isLocked && <Lock size={10} />}
                      </span>
                    </Link>
                  );
                })}
                {showLoginCta && (
                  <>
                    <div className="my-2 h-px bg-border" />
                    <Link
                      href={authCtaItem.href}
                      onClick={() => { setMenuOpen(false); }}
                      className="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium text-primary hover:bg-accent"
                    >
                      <authCtaItem.icon size={16} />
                      <span>{t(authCtaItem.labelKey)}</span>
                    </Link>
                  </>
                )}
                <div className="my-2 h-px bg-border" />
                <div className="flex items-center gap-1 px-1">
                  <LanguageToggle />
                  <ThemeToggle />
                  <div className="flex-1" />
                  {isAuthenticated && <ProfileDropdown />}
                </div>
              </div>
            </div>
          )}
        </header>
      )}

      {/* Desktop: Top header with nav (always shown on desktop) */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b bg-background/95 backdrop-blur hidden md:block">
        <div className="max-w-[var(--page-max-width)] mx-auto px-[var(--page-padding-x)]">
          <div className="flex items-center justify-between h-14">
            {/* Left: Logo + Nav tabs */}
            <div className="flex items-center gap-6">
              <Logo size="md" showText={true} />
              <nav className="flex items-center gap-1">
                {mainNav.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);
                  const isLocked = item.lockedForGuests && !isAuthenticated;
                  const linkHref = isLocked ? '/login' : item.href;
                  return (
                    <Link
                      key={item.id}
                      href={linkHref}
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
                        active
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:text-foreground hover:bg-muted',
                        isLocked && 'opacity-75'
                      )}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="flex items-center gap-1">
                        {t(item.labelKey)}
                        {isLocked && <Lock size={10} />}
                      </span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* Right: Controls */}
            <div className="flex items-center gap-2">
              <LanguageToggle />
              <ThemeToggle />
              {showLoginCta && (
                <Button asChild>
                  <Link href={authCtaItem.href}>
                    <authCtaItem.icon className="w-4 h-4 mr-2" />
                    {t(authCtaItem.labelKey)}
                  </Link>
                </Button>
              )}
              {isAuthenticated && <ProfileDropdown />}
            </div>
          </div>
        </div>
      </header>

      {/* Spacer to prevent content from being hidden under fixed header */}
      {mobileLayout === 'hamburger' && <div className="h-14 md:hidden" />}
      <div className="hidden md:block h-14" />
    </>
  );
}
