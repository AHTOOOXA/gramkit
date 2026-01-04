import { type NextRequest } from 'next/server';
import createMiddleware from 'next-intl/middleware';

import { routing } from './i18n/routing';
import { createRedirect } from './lib/middleware-utils';

const intlMiddleware = createMiddleware(routing);

/**
 * Proxy: i18n routing + access control
 *
 * Route access levels:
 * - Public routes (/,/demo): accessible to everyone, no redirects
 * - Guest-only routes (/login, /marketing): redirect authenticated users to home
 * - Auth-required routes (/profile, /admin): redirect guests to login
 */
export default function proxy(request: NextRequest) {
  // Apply i18n middleware for locale routing
  const intlResponse = intlMiddleware(request);

  // Extract locale and path from URL
  const pathname = request.nextUrl.pathname;
  const localeMatch = /^\/([a-z]{2})(\/.*)?$/.exec(pathname);
  const locale = localeMatch?.[1] ?? 'en';
  const pathWithoutLocale = localeMatch?.[2] ?? '/';

  // Check if request is authenticated
  // TMA auth: initData header
  const initData = request.headers.get('initData');
  const hasTmaAuth = !!initData && initData.length > 0;

  // Web auth: session cookie (format: {app_name}_session)
  const appName = process.env.APP_NAME ?? 'app';
  const sessionCookie = request.cookies.get(`${appName}_session`)?.value;
  const hasSessionAuth = !!sessionCookie;

  const isAuthenticated = hasTmaAuth || hasSessionAuth;

  // Route classification
  // Public: accessible to everyone (no access control)
  const publicRoutes = ['/', '/demo'];
  // Guest-only: redirect authenticated users to home
  const guestOnlyRoutes = ['/login', '/marketing'];
  // Auth-required: redirect guests to login
  const authRequiredRoutes = ['/profile', '/admin', '/test-gen'];

  const isPublicRoute = publicRoutes.some(
    (route) => pathWithoutLocale === route || (route !== '/' && pathWithoutLocale.startsWith(route + '/'))
  );
  const isGuestOnlyRoute = guestOnlyRoutes.some(
    (route) => pathWithoutLocale === route || pathWithoutLocale.startsWith(route + '/')
  );
  const isAuthRequiredRoute = authRequiredRoutes.some(
    (route) => pathWithoutLocale === route || pathWithoutLocale.startsWith(route + '/')
  );

  // Access control rules

  // Rule 1: Public routes - always accessible, no redirects
  if (isPublicRoute) {
    return intlResponse;
  }

  // Rule 2: Guest-only routes - redirect authenticated users to home
  if (isGuestOnlyRoute && isAuthenticated) {
    return createRedirect(request, `/${locale}`);
  }

  // Rule 3: Auth-required routes - redirect guests to login
  if (isAuthRequiredRoute && !isAuthenticated) {
    return createRedirect(request, `/${locale}/login`);
  }

  // Default: allow through (unknown routes)
  return intlResponse;
}

export const config = {
  // The matcher is relative to the basePath
  matcher: [
    '/', // Handle root of basePath
    '/((?!api|_next|_vercel|.*\\..*).*)', // All other routes
  ],
};
