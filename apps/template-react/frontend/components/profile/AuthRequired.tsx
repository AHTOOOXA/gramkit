'use client';

import { useTranslations } from 'next-intl';
import { Lock } from 'lucide-react';

interface AuthRequiredProps {
  locked: boolean;
  children: React.ReactNode;
}

export function AuthRequired({ locked, children }: AuthRequiredProps) {
  const t = useTranslations('profile');

  return (
    <div className="relative">
      {/* Content (blurred when locked with smooth transition) */}
      <div className={`transition-all duration-300 ${locked ? 'blur-sm pointer-events-none select-none' : ''}`}>
        {children}
      </div>

      {/* Lock overlay with animated entrance */}
      {locked && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/60 rounded-xl backdrop-blur-[2px]">
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            {/* Lock icon with subtle pulse */}
            <Lock className="w-6 h-6 motion-preset-pulse motion-duration-[2s] motion-loop-infinite" />
            {/* Text */}
            <span className="text-sm font-medium">{t('authRequired')}</span>
          </div>
        </div>
      )}
    </div>
  );
}
