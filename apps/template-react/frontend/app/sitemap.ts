import type { MetadataRoute } from 'next';

import { getSiteUrl } from '@/lib/site-url';
import { routing } from '@/i18n/routing';

// Public pages only: the home page and the tech demos, per locale.
const PUBLIC_PATHS = ['', '/demo'];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl = await getSiteUrl();
  return PUBLIC_PATHS.map((path) => ({
    url: `${siteUrl}/${routing.defaultLocale}${path}`,
    changeFrequency: 'monthly',
    priority: path === '' ? 1 : 0.6,
    alternates: {
      languages: Object.fromEntries(
        routing.locales.map((locale) => [locale, `${siteUrl}/${locale}${path}`])
      ),
    },
  }));
}
