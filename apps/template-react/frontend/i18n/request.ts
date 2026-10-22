import { getRequestConfig } from 'next-intl/server';

import { routing } from './routing';

// TODO: migrate to next/root-params (https://next-intl.dev/blog/nextjs-root-params)
// eslint-disable-next-line @typescript-eslint/no-deprecated
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
