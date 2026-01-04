import type { Language } from '@tma-platform/core-react/types';

export const APP_NAME =
  process.env.NEXT_PUBLIC_APP_NAME ?? 'TMA Template React';

export const SUPPORTED_LANGUAGES: readonly Language[] = ['en', 'ru'] as const;
export const DEFAULT_LANGUAGE: Language = 'en';
