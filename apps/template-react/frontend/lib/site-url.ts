import { headers } from 'next/headers';

/**
 * Absolute URL of this deployment (origin + basePath), read from the request.
 * Open Graph images, canonical links, robots.txt and the sitemap need absolute
 * URLs, and the domain differs per deploy, so it comes from the proxy's
 * forwarded headers rather than an env var baked in at build time.
 * Calling it makes the route render per request.
 */
export async function getSiteUrl(): Promise<string> {
  const h = await headers();
  const host = h.get('x-forwarded-host') ?? h.get('host') ?? 'localhost:3001';
  const proto =
    h.get('x-forwarded-proto') ??
    (host.startsWith('localhost') ? 'http' : 'https');
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '/template-react';
  return `${proto}://${host}${basePath}`;
}
