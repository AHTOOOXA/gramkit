import type { Component } from 'vue'
import { Home, FlaskConical, User, Settings, ArrowRight } from 'lucide-vue-next'

/**
 * Access levels for navigation items:
 * - 'public': Visible to everyone (guests and authenticated users)
 * - 'guest': Visible only to guests (not logged in)
 * - 'auth': Visible only to authenticated users
 * - 'admin': Visible only to admin or owner users
 * - 'owner': Visible only to owner users (highest privilege)
 */
export type AccessLevel = 'public' | 'guest' | 'auth' | 'admin' | 'owner'

export interface NavItem {
  id: string
  href: string
  icon: Component  // lucide-vue-next icon component
  labelKey: string // i18n key for translation
  access: AccessLevel
  /** Show in mobile bottom tabs (max 5 recommended) */
  showInMobile?: boolean
  /** Show in desktop header nav */
  showInDesktop?: boolean
  /** Show lock icon for non-authenticated users (only for public items) */
  lockedForGuests?: boolean
}

/**
 * Main app navigation items
 * Single source of truth for all navigation across the app
 */
export const navItems: NavItem[] = [
  {
    id: 'home',
    href: '/',
    icon: Home,
    labelKey: 'nav.home',
    access: 'public',
    showInMobile: true,
    showInDesktop: true,
  },
  {
    id: 'demo',
    href: '/demo',
    icon: FlaskConical,
    labelKey: 'nav.demo',
    access: 'public',
    showInMobile: true,
    showInDesktop: true,
  },
  {
    id: 'profile',
    href: '/profile',
    icon: User,
    labelKey: 'nav.profile',
    access: 'public',
    showInMobile: true,
    showInDesktop: true,
    lockedForGuests: true,
  },
  {
    id: 'admin',
    href: '/admin',
    icon: Settings,
    labelKey: 'nav.admin',
    access: 'admin',
    showInMobile: false,
    showInDesktop: true,
  },
]

/**
 * Auth CTA item (Get Started button for guests)
 */
export const authCtaItem: NavItem = {
  id: 'getStarted',
  href: '/login',
  icon: ArrowRight,
  labelKey: 'nav.getStarted',
  access: 'guest',
  showInMobile: true,
  showInDesktop: true,
}

/**
 * Filter nav items based on user access level
 */
export function filterNavItems(
  items: NavItem[],
  options: {
    isAuthenticated: boolean
    isAdmin?: boolean
    isOwner?: boolean
    mobileOnly?: boolean
    desktopOnly?: boolean
  }
): NavItem[] {
  const { isAuthenticated, isAdmin = false, isOwner = false, mobileOnly, desktopOnly } = options

  return items.filter((item) => {
    // Check access level
    const hasAccess = (() => {
      switch (item.access) {
        case 'public':
          return true
        case 'guest':
          return !isAuthenticated
        case 'auth':
          return isAuthenticated
        case 'admin':
          return isAdmin || isOwner // admin OR owner can access
        case 'owner':
          return isOwner // only owner
        default:
          return false
      }
    })()

    if (!hasAccess) return false

    // Check display context
    if (mobileOnly && !item.showInMobile) return false
    if (desktopOnly && !item.showInDesktop) return false

    return true
  })
}

/**
 * Get all visible nav items for current user state
 */
export function getVisibleNavItems(options: {
  isAuthenticated: boolean
  isAdmin?: boolean
  isOwner?: boolean
}): {
  mainNav: NavItem[]
  mobileNav: NavItem[]
  showLoginCta: boolean
} {
  const { isAuthenticated, isAdmin, isOwner } = options

  const mainNav = filterNavItems(navItems, {
    isAuthenticated,
    isAdmin,
    isOwner,
    desktopOnly: true,
  })

  const mobileNav = filterNavItems(navItems, {
    isAuthenticated,
    isAdmin,
    isOwner,
    mobileOnly: true,
  })

  const showLoginCta = !isAuthenticated

  return { mainNav, mobileNav, showLoginCta }
}
