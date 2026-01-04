import { type NextRequest, NextResponse } from 'next/server';

/**
 * Create a redirect response that respects Next.js basePath.
 *
 * NEVER use `new URL('/path', request.url)` in middleware - it ignores basePath.
 * ALWAYS use this helper or `request.nextUrl.clone()`.
 *
 * @example
 * // In middleware.ts
 * return createRedirect(request, '/login');
 * return createRedirect(request, '/en/dashboard');
 */
export function createRedirect(
  request: NextRequest,
  pathname: string,
  options?: { permanent?: boolean }
): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = pathname;
  return options?.permanent
    ? NextResponse.redirect(url, 308)
    : NextResponse.redirect(url);
}

/**
 * Create a rewrite response that respects Next.js basePath.
 *
 * @example
 * return createRewrite(request, '/api/proxy');
 */
export function createRewrite(request: NextRequest, pathname: string): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = pathname;
  return NextResponse.rewrite(url);
}
