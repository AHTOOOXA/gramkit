import { inject } from 'vue';
import { LanguageServiceKey } from '@core/injection-keys';

/**
 * Composable to access the language service.
 *
 * The language service must be provided at the app level using:
 * app.provide(LanguageServiceKey, languageService)
 *
 * @throws Error if LanguageService is not provided
 */
export function useLanguage() {
  const service = inject(LanguageServiceKey);

  if (!service) {
    throw new Error(
      'LanguageService not provided. ' +
      'Did you forget to provide it in main.ts using app.provide(LanguageServiceKey, service)?'
    );
  }

  return service;
}
