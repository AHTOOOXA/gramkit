'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Smartphone, Globe, Vibrate, X, MessageSquare } from 'lucide-react';

import { usePlatform, useTelegram } from '@/hooks';
import { ProfileSection } from './ProfileSection';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function TelegramSection() {
  const t = useTranslations('profile.telegram');
  const platform = usePlatform();
  const telegram = useTelegram();

  const [isVibrating, setIsVibrating] = useState(false);

  const handleVibrate = () => {
    setIsVibrating(true);
    telegram.vibrate('medium');
    setTimeout(() => { setIsVibrating(false); }, 300);
  };

  const handleShowAlert = async () => {
    await telegram.showAlert(t('alertMessage'));
  };

  return (
    <ProfileSection icon="📱" title={t('title')}>
      <div className="space-y-4">
        {/* Platform Status */}
        <div className="flex items-center justify-between p-3 bg-muted rounded-lg transition-all duration-300 hover:bg-muted/80">
          <div className="flex items-center gap-3">
            {platform.isTelegram ? (
              <Smartphone className="w-5 h-5 text-blue-500" />
            ) : (
              <Globe className="w-5 h-5 text-gray-500" />
            )}
            <div>
              <p className="font-medium">{t('platform')}</p>
              <p className="text-sm text-muted-foreground">
                {platform.isTelegram ? t('telegramApp') : t('webBrowser')}
              </p>
            </div>
          </div>
          {/* Badge with pop on change */}
          <Badge
            variant={platform.isTelegram ? 'default' : 'secondary'}
            className="motion-preset-pop motion-duration-[0.2s]"
            key={platform.isTelegram ? 'telegram' : 'web'}
          >
            {platform.isTelegram ? 'Telegram' : 'Web'}
          </Badge>
        </div>

        {/* Platform Details (Telegram only) */}
        {platform.isTelegram && (
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-muted rounded-lg p-3 transition-all duration-200 hover:bg-muted/80 hover:scale-[1.02]">
              <p className="text-muted-foreground text-xs">{t('client')}</p>
              <p className="font-mono capitalize">{platform.platform}</p>
            </div>
            <div className="bg-muted rounded-lg p-3 transition-all duration-200 hover:bg-muted/80 hover:scale-[1.02]">
              <p className="text-muted-foreground text-xs">{t('colorScheme')}</p>
              <p className="capitalize">{platform.colorScheme}</p>
            </div>
          </div>
        )}

        {/* Telegram-only Actions */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">
            {t('actionsTitle')}
          </p>

          {platform.isTelegram ? (
            <>
              {/* Vibrate button with shake feedback */}
              <Button
                variant="outline"
                className={`w-full justify-start gap-2 active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150 ${
                  isVibrating ? 'motion-preset-shake motion-duration-[0.3s]' : ''
                }`}
                onClick={handleVibrate}
              >
                <Vibrate className={`w-4 h-4 ${isVibrating ? 'animate-pulse' : ''}`} />
                {t('vibrate')}
              </Button>

              {/* Show Alert button */}
              <Button
                variant="outline"
                className="w-full justify-start gap-2 active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
                onClick={handleShowAlert}
              >
                <MessageSquare className="w-4 h-4" />
                {t('showAlert')}
              </Button>
            </>
          ) : (
            /* Web user message */
            <div className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg text-sm text-muted-foreground">
              <X className="w-4 h-4 shrink-0 opacity-50" />
              <span>{t('webOnlyMessage')}</span>
            </div>
          )}
        </div>
      </div>
    </ProfileSection>
  );
}
