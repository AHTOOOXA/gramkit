'use client';

import { useLanguageService } from '@/lib/services/useLanguageService';

export function LanguageInitializer() {
  useLanguageService();
  return null;
}
