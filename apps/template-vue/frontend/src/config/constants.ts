export const APP_NAME = import.meta.env.VITE_APP_NAME ?? 'TMA Template Vue';

export const SUPPORTED_LANGUAGES = ['en', 'ru'] as const;
export type Language = typeof SUPPORTED_LANGUAGES[number];

export const DEFAULT_LANGUAGE: Language = 'en';

// Marketing page links (the template's home page is gramkit's demo landing).
export const GITHUB_URL = 'https://github.com/AHTOOOXA/gramkit';
export const REACT_DEMO_URL = 'https://react.antonchaynik.ru';
