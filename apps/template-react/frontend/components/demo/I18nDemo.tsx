'use client';

import { useTranslations } from 'next-intl';

import { useLanguageService, type SupportedLocale } from '@/lib/services/useLanguageService';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';

const languages = [
  { id: 'en', label: 'English', flag: '\u{1F1FA}\u{1F1F8}' },
  { id: 'ru', label: '\u0420\u0443\u0441\u0441\u043a\u0438\u0439', flag: '\u{1F1F7}\u{1F1FA}' },
];

export function I18nDemo() {
  const t = useTranslations('demo.i18n');
  const { currentLocale, changeLanguage } = useLanguageService();

  const handleLanguageChange = async (langId: string) => {
    await changeLanguage(langId as SupportedLocale);
  };

  return (
    <DemoSection icon="&#127760;" title={t('title')}>
      <div className="space-y-4">
        <div className="flex gap-2">
          {languages.map((lang) => (
            <Button
              key={lang.id}
              variant={currentLocale === lang.id ? 'default' : 'outline'}
              className={`flex-1 active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150 ${
                currentLocale === lang.id ? 'motion-preset-pop motion-duration-[0.2s]' : ''
              }`}
              onClick={() => handleLanguageChange(lang.id)}
            >
              <span className={`mr-2 inline-block ${
                currentLocale === lang.id ? 'motion-preset-bounce motion-duration-[0.3s]' : ''
              }`}>
                {lang.flag}
              </span>
              {lang.label}
            </Button>
          ))}
        </div>

        <div
          className="bg-muted rounded-lg p-4 text-sm motion-preset-fade motion-duration-[0.3s]"
          key={currentLocale}
        >
          <p className="font-medium mb-2">{t('preview')}:</p>
          <p>{t('sampleText')}</p>
        </div>

        <p className="text-xs text-muted-foreground">
          {t('current')}: {currentLocale}
        </p>
      </div>
    </DemoSection>
  );
}
