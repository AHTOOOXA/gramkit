// eslint-disable-next-line no-restricted-imports -- Type-only import, safe from refactoring concerns
import type { LanguageService } from '@core/types/language';
import { i18n } from '@app/i18n';

const SUPPORTED_LOCALES = ['en', 'ru'] as const;
const DEFAULT_LOCALE = 'en';

type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

/**
 * Creates the language service implementation for the app.
 *
 * NOTE: User language sync is now handled in App.vue using TanStack Query.
 * This service only manages the i18n locale directly.
 */
export function createLanguageService(): LanguageService {
  const getUserLocale = (appLangCode = '', langCode = ''): SupportedLocale => {
    const lang = (appLangCode || langCode).toLowerCase();
    return SUPPORTED_LOCALES.includes(lang as SupportedLocale) ? (lang as SupportedLocale) : DEFAULT_LOCALE;
  };

  return {
    setLanguage: (locale: string) => {
      const validLocale = getUserLocale(locale);
      i18n.global.locale.value = validLocale;
    },
    getCurrentLanguage: () => i18n.global.locale.value,
  };
}
