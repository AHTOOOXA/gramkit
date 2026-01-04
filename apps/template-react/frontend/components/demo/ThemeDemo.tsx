'use client';

import { useTranslations } from 'next-intl';
import { Sun, Moon, Monitor, Check } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import { useAppTheme } from '@/hooks';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';

interface ThemeOption {
  id: 'light' | 'dark' | 'system';
  icon: LucideIcon;
  labelKey: string;
}

const themes: ThemeOption[] = [
  { id: 'light', icon: Sun, labelKey: 'demo.theme.light' },
  { id: 'dark', icon: Moon, labelKey: 'demo.theme.dark' },
  { id: 'system', icon: Monitor, labelKey: 'demo.theme.system' },
];

export function ThemeDemo() {
  const t = useTranslations();
  const { theme, setTheme } = useAppTheme();

  return (
    <DemoSection icon="&#127912;" title={t('demo.theme.title')}>
      <div className="space-y-4">
        <div className="flex flex-col gap-2">
          {themes.map((themeOption) => {
            const Icon = themeOption.icon;
            return (
              <Button
                key={themeOption.id}
                variant={theme === themeOption.id ? 'default' : 'outline'}
                className={`w-full justify-start active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150 ${
                  theme === themeOption.id ? 'motion-preset-pop motion-duration-[0.2s]' : ''
                }`}
                onClick={() => { setTheme(themeOption.id); }}
              >
                <Icon className={`w-4 h-4 mr-2 transition-transform duration-300 ${
                  theme === themeOption.id ? 'rotate-[360deg]' : ''
                }`} />
                {t(themeOption.labelKey)}
                {theme === themeOption.id && (
                  <Check className="w-4 h-4 ml-auto motion-preset-pop motion-duration-[0.2s]" />
                )}
              </Button>
            );
          })}
        </div>

        <p className="text-xs text-muted-foreground">
          {t('demo.theme.current')}: {theme}
        </p>
      </div>
    </DemoSection>
  );
}
