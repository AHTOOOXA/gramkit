/**
 * Language service interface for managing application locale.
 *
 * This allows core to define the contract while the app provides
 * the implementation with app-specific i18n and user data.
 */
export interface LanguageService {
  /**
   * Set the application locale
   */
  setLanguage: (locale: string) => void;

  /**
   * Get the current application locale
   */
  getCurrentLanguage: () => string;
}
