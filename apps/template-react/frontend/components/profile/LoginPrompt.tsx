'use client';

import { useTranslations } from 'next-intl';
import { LogIn, Lock } from 'lucide-react';

import { ProfileSection } from './ProfileSection';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';

export function LoginPrompt() {
  const t = useTranslations('profile.login');

  return (
    <ProfileSection icon="&#128274;" title={t('title')}>
      <div className="space-y-4">
        {/* Lock icon with subtle animation */}
        <div className="flex justify-center">
          <Lock className="w-12 h-12 text-muted-foreground/50 motion-preset-pulse motion-duration-[3s] motion-loop-infinite" />
        </div>

        {/* Description */}
        <div className="text-center">
          <p className="text-muted-foreground mb-4">{t('description')}</p>
        </div>

        {/* Login button - links to login page */}
        <Button
          asChild
          className="w-full active:scale-95 hover:scale-[1.02] hover:-translate-y-1 hover:shadow-lg hover:shadow-primary/25 transition-all duration-200"
        >
          <Link href="/login">
            <LogIn className="w-4 h-4 mr-2" />
            {t('button')}
          </Link>
        </Button>
      </div>
    </ProfileSection>
  );
}
