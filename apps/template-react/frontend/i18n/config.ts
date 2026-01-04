export const locales = ['en', 'ru'] as const;
export const defaultLocale = 'en';

export type Locale = (typeof locales)[number];
