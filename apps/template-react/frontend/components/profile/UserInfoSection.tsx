'use client';

import { useState, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useQueryClient } from '@tanstack/react-query';
import {
  LogOut,
  Smartphone,
  Mail,
  ChevronDown,
  ChevronUp,
  Flame,
  Trophy,
  Calendar,
  Check,
  Plus,
} from 'lucide-react';

import { usePlatform } from '@/hooks';
import { useLogoutAuthLogoutPost, getCurrentUserUsersMeGetQueryKey } from '@/src/gen/hooks';
import { ProfileSection } from './ProfileSection';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { LinkTelegramDialog } from './LinkTelegramDialog';
import { AddEmailDialog } from './AddEmailDialog';
import type { UserSchema } from '@/src/gen/models';

interface UserInfoSectionProps {
  user: UserSchema;
}

function StatCard({ icon: Icon, value, label }: { icon: React.ElementType; value: number; label: string }) {
  return (
    <div className="bg-muted rounded-lg p-3 text-center">
      <Icon className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function PreferenceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm">{value || '—'}</span>
    </div>
  );
}

function AuthMethodCard({
  icon: Icon,
  title,
  isLinked,
  subtitle,
  onLink,
  onShowDetails,
  showDetails,
  children,
}: {
  icon: React.ElementType;
  title: string;
  isLinked: boolean;
  subtitle?: string;
  onLink?: () => void;
  onShowDetails?: () => void;
  showDetails?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="border rounded-lg p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-muted rounded-full p-2">
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-medium">{title}</p>
            <p className="text-xs text-muted-foreground">
              {isLinked ? subtitle : 'Not connected'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isLinked ? (
            <>
              <Check className="h-4 w-4 text-green-500" />
              {onShowDetails && (
                <Button variant="ghost" size="sm" onClick={onShowDetails}>
                  {showDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </Button>
              )}
            </>
          ) : (
            onLink && (
              <Button variant="outline" size="sm" onClick={onLink}>
                <Plus className="h-3 w-3 mr-1" />
                Link
              </Button>
            )
          )}
        </div>
      </div>
      {showDetails && children && (
        <div className="mt-3 pt-3 border-t space-y-1">
          {children}
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value, mono = false }: { label: string; value: unknown; mono?: boolean }) {
  let formatted: string;
  if (value === null || value === undefined) {
    formatted = '—';
  } else if (typeof value === 'boolean') {
    formatted = value ? 'Yes' : 'No';
  } else if (typeof value === 'string' || typeof value === 'number') {
    formatted = String(value);
  } else {
    formatted = JSON.stringify(value);
  }

  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className={mono ? 'font-mono' : ''}>{formatted}</span>
    </div>
  );
}

export function UserInfoSection({ user }: UserInfoSectionProps) {
  const t = useTranslations('profile.user');
  const platform = usePlatform();
  const queryClient = useQueryClient();

  const [showLinkTelegramDialog, setShowLinkTelegramDialog] = useState(false);
  const [showAddEmailDialog, setShowAddEmailDialog] = useState(false);
  const [showTelegramDetails, setShowTelegramDetails] = useState(false);
  const [showEmailDetails, setShowEmailDetails] = useState(false);

  const displayName = user.display_name ?? 'User';

  const initials = useMemo(() => {
    const first = user.display_name?.[0] ?? user.username?.[0] ?? 'U';
    return first.toUpperCase();
  }, [user.display_name, user.username]);

  const authMethod = platform.isTelegram ? 'telegram' : 'web';
  const hasTelegram = !!user.telegram_id;
  const hasEmail = !!user.email;

  const memberSince = user.created_at
    ? new Date(user.created_at).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
    : null;

  const formatGender = (male: boolean | null | undefined) => {
    if (male === null || male === undefined) return '—';
    return male ? t('gender.male') : t('gender.female');
  };

  const { mutate: logout, isPending: isLoggingOut } = useLogoutAuthLogoutPost({
    mutation: {
      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() });
      },
    },
  });

  const handleLogout = () => {
    logout();
  };

  const handleLinkSuccess = () => {
    void queryClient.invalidateQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() });
  };

  return (
    <ProfileSection icon="&#128100;" title={t('title')}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Avatar className="h-16 w-16">
            {user.avatar_url && <AvatarImage src={user.avatar_url} alt={displayName} />}
            <AvatarFallback className="text-xl">{initials}</AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <p className="font-semibold text-lg">{displayName}</p>
            <p className="text-sm text-muted-foreground">@{user.username ?? 'user'}</p>
            {memberSince && (
              <p className="text-xs text-muted-foreground">{t('memberSince', { date: memberSince })}</p>
            )}
          </div>
        </div>

        {/* Activity Stats */}
        <div>
          <p className="text-xs font-semibold text-muted-foreground mb-3">{t('sections.activity')}</p>
          <div className="grid grid-cols-3 gap-2">
            <StatCard
              icon={Flame}
              value={user.current_streak ?? 0}
              label={t('stats.currentStreak')}
            />
            <StatCard
              icon={Trophy}
              value={user.best_streak ?? 0}
              label={t('stats.bestStreak')}
            />
            <StatCard
              icon={Calendar}
              value={user.total_active_days ?? 0}
              label={t('stats.totalDays')}
            />
          </div>
        </div>

        {/* Preferences */}
        <div>
          <p className="text-xs font-semibold text-muted-foreground mb-2">{t('sections.preferences')}</p>
          <div className="divide-y">
            <PreferenceRow label={t('prefs.language')} value={user.language_code ?? ''} />
            <PreferenceRow label={t('prefs.timezone')} value={user.timezone ?? ''} />
            <PreferenceRow label={t('prefs.birthDate')} value={user.birth_date ?? ''} />
            <PreferenceRow label={t('prefs.gender')} value={formatGender(user.male)} />
          </div>
        </div>

        {/* Auth Methods */}
        <div>
          <p className="text-xs font-semibold text-muted-foreground mb-3">{t('sections.authMethods')}</p>
          <div className="space-y-2">
            <AuthMethodCard
              icon={Smartphone}
              title="Telegram"
              isLinked={hasTelegram}
              subtitle={user.tg_username ? `@${user.tg_username}` : user.tg_first_name ?? undefined}
              onLink={() => { setShowLinkTelegramDialog(true); }}
              onShowDetails={hasTelegram ? () => { setShowTelegramDetails(!showTelegramDetails); } : undefined}
              showDetails={showTelegramDetails}
            >
              <DetailRow label="ID" value={user.telegram_id} mono />
              <DetailRow label={t('tg.firstName')} value={user.tg_first_name} />
              <DetailRow label={t('tg.lastName')} value={user.tg_last_name} />
              <DetailRow label={t('tg.username')} value={user.tg_username} />
              <DetailRow label={t('tg.languageCode')} value={user.tg_language_code} />
              <DetailRow label={t('tg.isPremium')} value={user.tg_is_premium} />
              <DetailRow label={t('tg.isBot')} value={user.tg_is_bot} />
            </AuthMethodCard>

            <AuthMethodCard
              icon={Mail}
              title="Email"
              isLinked={hasEmail}
              subtitle={user.email ?? undefined}
              onLink={() => { setShowAddEmailDialog(true); }}
              onShowDetails={hasEmail ? () => { setShowEmailDetails(!showEmailDetails); } : undefined}
              showDetails={showEmailDetails}
            >
              <DetailRow label={t('email.address')} value={user.email} />
              <DetailRow label={t('email.verified')} value={user.email_verified} />
              <DetailRow label={t('email.verifiedAt')} value={user.email_verified_at} />
              <DetailRow label={t('email.lastLogin')} value={user.last_login_at} />
            </AuthMethodCard>
          </div>
        </div>

        {/* Logout button (only for web auth) */}
        {authMethod === 'web' && (
          <Button
            variant="outline"
            className="w-full text-destructive hover:text-destructive hover:bg-destructive/10"
            disabled={isLoggingOut}
            onClick={handleLogout}
          >
            <LogOut className={`w-4 h-4 mr-2 ${isLoggingOut ? 'animate-spin' : ''}`} />
            {isLoggingOut ? t('loggingOut') : t('logout')}
          </Button>
        )}
      </div>

      <LinkTelegramDialog
        open={showLinkTelegramDialog}
        onOpenChange={setShowLinkTelegramDialog}
        onSuccess={handleLinkSuccess}
      />

      <AddEmailDialog
        open={showAddEmailDialog}
        onOpenChange={setShowAddEmailDialog}
        onSuccess={handleLinkSuccess}
      />
    </ProfileSection>
  );
}
