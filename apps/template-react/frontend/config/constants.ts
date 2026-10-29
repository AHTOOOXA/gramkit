import type { Language } from '@tma-platform/core-react/types';

export const APP_NAME =
  process.env.NEXT_PUBLIC_APP_NAME ?? 'TMA Template React';

export const SUPPORTED_LANGUAGES: readonly Language[] = ['en', 'ru'] as const;
export const DEFAULT_LANGUAGE: Language = 'en';

// Marketing page links (the template's home page is gramkit's demo landing).
export const GITHUB_URL = 'https://github.com/AHTOOOXA/gramkit';
export const VUE_DEMO_URL = 'https://vue.antonchaynik.ru';
