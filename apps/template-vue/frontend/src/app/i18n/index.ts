import { createI18n } from 'vue-i18n';
import en from './locales/en.json';
import ru from './locales/ru.json';

export const SUPPORTED_LOCALES = ['en', 'ru'] as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

const LOCALE_STORAGE_KEY = 'app-locale';

/**
 * Get initial locale with priority:
 * 1. localStorage (user's previous choice)
 * 2. Browser language
 * 3. Default 'en'
 */
function getInitialLocale(): SupportedLocale {
  if (typeof window === 'undefined') return 'en';

  // 1. Check localStorage first (persisted preference)
  try {
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (saved && SUPPORTED_LOCALES.includes(saved as SupportedLocale)) {
      return saved as SupportedLocale;
    }
  } catch {
    // localStorage not available
  }

  // 2. Check browser language
  const browserLang = navigator.language.split('-')[0];
  if (SUPPORTED_LOCALES.includes(browserLang as SupportedLocale)) {
    return browserLang as SupportedLocale;
  }

  // 3. Default
  return 'en';
}

/**
 * Save locale to localStorage for persistence across refreshes.
 */
export function saveLocale(locale: SupportedLocale): void {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  } catch {
    // localStorage not available
  }
}

export const i18n = createI18n({
  legacy: false, // Use Composition API
  globalInjection: true, // Make $t and locale changes reactive globally
  locale: getInitialLocale(),
  fallbackLocale: 'en',
  messages: { en, ru },
});
