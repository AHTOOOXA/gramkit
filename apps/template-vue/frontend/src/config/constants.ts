export const APP_NAME = import.meta.env.VITE_APP_NAME ?? 'TMA Template Vue';

export const SUPPORTED_LANGUAGES = ['en', 'ru'] as const;
export type Language = typeof SUPPORTED_LANGUAGES[number];

export const DEFAULT_LANGUAGE: Language = 'en';
