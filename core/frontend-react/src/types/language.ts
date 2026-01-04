export type Language = 'en' | 'ru';

export const SUPPORTED_LANGUAGES: readonly Language[] = ['en', 'ru'] as const;

export const DEFAULT_LANGUAGE: Language = 'en';

export function isValidLanguage(lang: unknown): lang is Language {
  return typeof lang === 'string' && SUPPORTED_LANGUAGES.includes(lang as Language);
}
