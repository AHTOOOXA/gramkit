'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Check, Bell, Send } from 'lucide-react';

import { useScheduleNotificationDemoNotifyPost } from '@/src/gen/hooks';
import { ProfileSection } from './ProfileSection';
import { Button } from '@/components/ui/button';

const DELAYS = [
  { label: '1', value: 1 },
  { label: '5', value: 5 },
  { label: '10', value: 10 },
];

export function NotificationSection() {
  const t = useTranslations('profile.notification');

  const { mutate: notify, isPending } = useScheduleNotificationDemoNotifyPost();

  const [lastSent, setLastSent] = useState<number | null>(null);
  const [status, setStatus] = useState<'idle' | 'sent'>('idle');
  const [selectedDelay, setSelectedDelay] = useState<number | null>(null);

  const handleNotify = (delaySeconds: number) => {
    setSelectedDelay(delaySeconds);
    notify(
      { data: { delay_seconds: delaySeconds } },
      {
        onSuccess: () => {
          setLastSent(delaySeconds);
          setStatus('sent');
          setSelectedDelay(null);
          setTimeout(() => { setStatus('idle'); }, 3000);
        },
        onError: () => {
          setSelectedDelay(null);
        },
      }
    );
  };

  return (
    <ProfileSection icon="&#128276;" title={t('title')}>
      <div className="space-y-4">
        {/* Description */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Bell className="w-4 h-4" />
          <span>{t('description')}</span>
        </div>

        {/* Delay buttons - matching demo polling pattern */}
        <div className="flex gap-2 flex-wrap">
          {DELAYS.map((delay) => (
            <Button
              key={delay.value}
              disabled={isPending}
              variant={selectedDelay === delay.value ? 'default' : 'outline'}
              size="sm"
              className={`active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150 ${
                selectedDelay === delay.value ? 'motion-preset-pop motion-duration-[0.15s]' : ''
              }`}
              onClick={() => { handleNotify(delay.value); }}
            >
              {selectedDelay === delay.value && (
                <Send className="w-3 h-3 mr-1 animate-pulse" />
              )}
              {delay.label}{t('seconds')}
            </Button>
          ))}
        </div>

        {/* Success message with slide-in and pop */}
        {status === 'sent' && (
          <div className="flex items-center gap-2 text-sm text-green-500 bg-green-500/10 rounded-lg p-3 motion-preset-slide-up-sm motion-preset-fade motion-duration-[0.3s]">
            <Check className="w-4 h-4 motion-preset-pop motion-duration-[0.2s]" />
            <span>{t('sent', { seconds: lastSent ?? 0 })}</span>
          </div>
        )}

        <p className="text-xs text-muted-foreground">{t('note')}</p>
      </div>
    </ProfileSection>
  );
}
