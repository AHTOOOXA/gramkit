import { getRequestConfig } from 'next-intl/server';

import { routing } from './routing';

export default getRequestConfig(async ({ requestLocale }) => {
  // Typically corresponds to the `[locale]` segment
  const requested = await requestLocale;
  const typedRequested = requested as 'en' | 'ru' | null;
  const locale =
    typedRequested && routing.locales.includes(typedRequested)
      ? typedRequested
      : routing.defaultLocale;

  return {
    locale,
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
    messages: (await import(`./messages/${locale}.json`)).default as Record<
      string,
      string
    >,
    timeZone: 'UTC',
  };
});
