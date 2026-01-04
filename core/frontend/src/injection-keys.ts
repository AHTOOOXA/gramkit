import type { InjectionKey } from 'vue';
import type { LanguageService } from './types/language';

/**
 * Injection key for the language service.
 *
 * Use with provide/inject to pass the language service implementation
 * from the app to core components.
 */
export const LanguageServiceKey: InjectionKey<LanguageService> = Symbol('LanguageService');
