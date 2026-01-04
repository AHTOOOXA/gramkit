import { notFound } from 'next/navigation';
import { NextIntlClientProvider } from 'next-intl';

import { PageViewTracker } from '@/components/analytics';
import { LanguageInitializer } from '@/components/language-initializer';
import { routing } from '@/i18n/routing';

import { Providers } from '../providers';

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

interface Props {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}

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
    <NextIntlClientProvider locale={locale} messages={messages} timeZone="UTC">
      <Providers>
        <LanguageInitializer />
        <PageViewTracker />
        {children}
      </Providers>
    </NextIntlClientProvider>
  );
}
