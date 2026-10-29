import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import { notFound } from 'next/navigation';
import Script from 'next/script';
import { NextIntlClientProvider } from 'next-intl';
import { ViewTransitions } from 'next-view-transitions';
import { NuqsAdapter } from 'nuqs/adapters/next/app';

import '@/styles/globals.css';

import { PageViewTracker } from '@/components/analytics';
import { LanguageInitializer } from '@/components/language-initializer';
import { PlatformDetector } from '@/components/platform-detector';
import { routing } from '@/i18n/routing';

import { Providers } from '../providers';

const inter = Inter({
  subsets: ['latin', 'cyrillic'],
  display: 'swap',
  variable: '--font-inter',
});

// The app shell locks zoom (a Telegram WebView pinch-zooms on input focus).
// The marketing layout overrides this so the landing page stays zoomable.
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
};

export const metadata: Metadata = {
  title: 'Gramkit',
  description: 'Telegram Mini App + web starter on FastAPI and Next.js',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
    ],
    apple: '/apple-touch-icon.png',
  },
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

interface Props {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}

// The root layout lives under [locale] so <html lang> is rendered on the server.
export default async function LocaleLayout({ children, params }: Props) {
  // Ensure that the incoming `locale` is valid
  const { locale } = await params;
  const typedLocale = locale as 'en' | 'ru';
  if (!routing.locales.includes(typedLocale)) {
    notFound();
  }

  // Load messages manually (plugin config resolution not working in Docker/monorepo with Turbopack)
  // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
  const messagesModule = await import(`@/i18n/messages/${typedLocale}.json`);
  // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
  const messages = messagesModule.default as Record<string, string>;

  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        {/* Telegram WebApp SDK - CRITICAL for authentication */}
        {/* beforeInteractive ensures script loads before React hydration */}
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
      </head>
      <body
        className={`${inter.className} bg-background min-h-dvh antialiased`}
      >
        <NuqsAdapter>
          <ViewTransitions>
            <PlatformDetector />
            <NextIntlClientProvider
              locale={locale}
              messages={messages}
              timeZone="UTC"
            >
              <Providers>
                <LanguageInitializer />
                <PageViewTracker />
                {children}
              </Providers>
            </NextIntlClientProvider>
          </ViewTransitions>
        </NuqsAdapter>
      </body>
    </html>
  );
}
