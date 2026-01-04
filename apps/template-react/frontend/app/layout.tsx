import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import Script from 'next/script';
import { ViewTransitions } from 'next-view-transitions';
import { NuqsAdapter } from 'nuqs/adapters/next/app';

import '@/styles/globals.css';

import { PlatformDetector } from '@/components/platform-detector';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
};

export const metadata: Metadata = {
  title: 'TMA Template React',
  description: 'Telegram Mini App Template with React and Next.js',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
    ],
    apple: '/apple-touch-icon.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html suppressHydrationWarning>
      <head>
        {/* Telegram WebApp SDK - CRITICAL for authentication */}
        {/* beforeInteractive ensures script loads before React hydration */}
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
      </head>
      <body className={`${inter.className} min-h-dvh bg-background antialiased`}>
        <NuqsAdapter>
          <ViewTransitions>
            <PlatformDetector />
            {children}
          </ViewTransitions>
        </NuqsAdapter>
      </body>
    </html>
  );
}
