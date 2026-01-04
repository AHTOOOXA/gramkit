'use client';

import { useLanguageService } from '@/lib/services/useLanguageService';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const languageNames: Record<string, string> = {
  en: 'English',
  ru: 'Русский',
};

export function LanguageSwitcher() {
  const { currentLocale, supportedLocales, changeLanguage } =
    useLanguageService();

  return (
    <Select value={currentLocale} onValueChange={changeLanguage}>
      <SelectTrigger className="w-[180px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {supportedLocales.map((locale) => (
          <SelectItem key={locale} value={locale}>
            {languageNames[locale]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
