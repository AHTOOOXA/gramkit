'use client';

import { useTranslations } from 'next-intl';

import { getErrorMessage } from '@tma-platform/core-react/errors';
import { useGetCurrentUserUsersMeGet } from '@/src/gen/hooks';
import {
  UserInfoSection,
  TelegramSection,
  FriendsSection,
  NotificationSection,
  LoginPrompt,
  AuthRequired,
  RbacDemo,
} from '@/components/profile';
import { Link } from '@/i18n/navigation';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function ProfilePage() {
  const t = useTranslations('profile');

  const { data: user, isLoading, error, refetch } = useGetCurrentUserUsersMeGet();
  // User is authenticated if they have a registered account (not a guest)
  const isAuthenticated = user?.user_type === 'REGISTERED';

  if (isLoading) {
    return (
      <div className="py-6 text-center">
        <p className="text-muted-foreground animate-pulse">{t('loading', { defaultValue: 'Loading...' })}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-6 px-4">
        <Alert variant="destructive" className="motion-preset-shake motion-duration-[0.4s]">
          <AlertDescription className="flex items-center justify-between gap-4">
            <span>{getErrorMessage(error)}</span>
            <Button
              size="sm"
              variant="outline"
              className="shrink-0"
              onClick={() => refetch()}
            >
              {t('retry', { defaultValue: 'Retry' })}
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="py-6 space-y-4">
      {/* Header - Hero moment with dramatic emphasis */}
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold mb-2 motion-blur-in-[10px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.7s] motion-duration-[1s]/blur motion-ease-spring-smooth">
          {t('title')}
        </h1>
        <p className="text-muted-foreground motion-blur-in-[5px] motion-opacity-in-[0%] motion-translate-y-in-[10px] motion-duration-[0.5s] motion-delay-[0.25s] motion-ease-spring-smooth">
          {t('subtitle')}
        </p>
      </div>

      {/* User Info / Login Prompt */}
      <div className="motion-opacity-in-[0%] motion-scale-in-[0.98] motion-blur-in-[3px] motion-duration-[0.55s] motion-delay-[0.35s] motion-ease-spring-smooth">
        {isAuthenticated ? (
          <UserInfoSection user={user} />
        ) : (
          <LoginPrompt />
        )}
      </div>

      {/* Platform */}
      <div className="motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.5s] motion-ease-spring-smooth">
        <TelegramSection />
      </div>

      {/* Friends */}
      <div className="motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.6s] motion-ease-spring-smooth">
        <AuthRequired locked={!isAuthenticated}>
          <FriendsSection />
        </AuthRequired>
      </div>

      {/* Notifications */}
      <div className="motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.7s] motion-ease-spring-smooth">
        <AuthRequired locked={!isAuthenticated}>
          <NotificationSection />
        </AuthRequired>
      </div>

      {/* RBAC Demo */}
      <div className="motion-opacity-in-[0%] motion-translate-y-in-[30px] motion-blur-in-[4px] motion-duration-[0.5s] motion-delay-[0.8s] motion-ease-spring-smooth">
        <RbacDemo />
      </div>

      {/* CTA - Final flourish with glow effect */}
      <div className="motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.5s] motion-delay-[0.9s] motion-ease-spring-bouncy group relative overflow-hidden bg-muted/50 rounded-xl p-4 text-center transition-all duration-300 hover:bg-muted/70 hover:shadow-xl hover:shadow-primary/15">
        {/* Animated border glow on hover */}
        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-primary/0 via-primary/10 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

        <p className="relative text-sm text-muted-foreground mb-2">Want to copy these patterns?</p>
        <Link
          href="/demo"
          className="relative text-primary hover:underline font-medium inline-flex items-center gap-1"
        >
          See TanStack Query demos{' '}
          <span className="inline-block transition-transform duration-300 group-hover:translate-x-2">
            &rarr;
          </span>
        </Link>
      </div>
    </div>
  );
}
