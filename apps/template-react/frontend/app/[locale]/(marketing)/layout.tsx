import type { Metadata, Viewport } from 'next';
import { getTranslations } from 'next-intl/server';

import { getSiteUrl } from '@/lib/site-url';
import { Footer } from '@/components/layout';
import { AppShell } from '@/components/shells';
import { routing } from '@/i18n/routing';

// A marketing page must stay zoomable (WCAG 1.4.4): undo the app shell's zoom lock.
// Viewport fields merge with the parent's, so the lock is overridden, not omitted.
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: 'cover',
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'homePage.meta' });
  const siteUrl = await getSiteUrl();
  const title = t('title');
  const description = t('description');
  // Absolute: Telegram and X ignore relative image URLs. Served by app/[locale]/og.png/route.tsx.
  const image = {
    url: `${siteUrl}/${locale}/og.png`,
    width: 1200,
    height: 630,
    alt: 'Gramkit: Telegram Mini App + web starter on FastAPI and Next.js',
  };

  return {
    // Trailing slash: relative URLs below resolve under the basePath.
    metadataBase: new URL(`${siteUrl}/`),
    title,
    description,
    alternates: {
      canonical: locale,
      languages: Object.fromEntries(routing.locales.map((l) => [l, l])),
    },
    openGraph: {
      type: 'website',
      siteName: 'Gramkit',
      title,
      description,
      url: locale,
      locale: locale === 'ru' ? 'ru_RU' : 'en_US',
      images: [image],
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [image],
    },
  };
}

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell footer={<Footer />}>{children}</AppShell>;
}
