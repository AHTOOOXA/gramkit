'use client';

import { useEffect, useState } from 'react';
import { Globe, Check } from 'lucide-react';

import { useLanguageService } from '@/lib/services/useLanguageService';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const languageNames: Record<string, string> = {
  en: 'English',
  ru: 'Русский',
};

export function LanguageToggle() {
  const { currentLocale, supportedLocales, changeLanguage } =
    useLanguageService();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon">
          <Globe className="h-[1.2rem] w-[1.2rem]" />
          <span className="sr-only">Toggle language</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {supportedLocales.map((locale) => (
          <DropdownMenuItem
            key={locale}
            onClick={() => {
              void changeLanguage(locale);
            }}
            className="flex items-center justify-between gap-2"
          >
            <span>{languageNames[locale]}</span>
            {currentLocale === locale && <Check className="h-4 w-4" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
