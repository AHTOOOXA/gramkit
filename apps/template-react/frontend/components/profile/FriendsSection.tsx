'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Copy, Check, UserPlus, Users } from 'lucide-react';
import { toast } from 'sonner';

import { getErrorMessage } from '@tma-platform/core-react/errors';
import {
  useGetFriendsFriendsGet,
  useCreateInviteCreateInviteGet,
} from '@/src/gen/hooks';
import { ProfileSection } from './ProfileSection';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function FriendsSection() {
  const t = useTranslations('profile.friends');

  const { data: friends, isPending, error, refetch } = useGetFriendsFriendsGet();
  const { refetch: createInvite, isFetching: isCreatingInvite } =
    useCreateInviteCreateInviteGet({
      query: { enabled: false },
    });

  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCreateInvite = async () => {
    try {
      const { data } = await createInvite();
      if (data) {
        setInviteLink(data.telegram_link);
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  const copyInvite = async () => {
    if (!inviteLink) return;
    await navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => { setCopied(false); }, 2000);
  };

  // Show error state
  if (error) {
    return (
      <ProfileSection icon="&#128101;" title={t('title')}>
        <Alert variant="destructive">
          <AlertDescription className="flex items-center justify-between gap-2">
            <span className="text-sm">{getErrorMessage(error)}</span>
            <Button size="sm" variant="outline" onClick={() => refetch()}>
              {t('retry', { defaultValue: 'Retry' })}
            </Button>
          </AlertDescription>
        </Alert>
      </ProfileSection>
    );
  }

  return (
    <ProfileSection icon="&#128101;" title={t('title')}>
      <div className="space-y-4">
        {/* Count with icon */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Users className="w-4 h-4" />
          <span
            className="motion-preset-pop motion-duration-[0.2s]"
            key={friends?.length}
          >
            {t('count', { count: friends?.length ?? 0 })}
          </span>
        </div>

        {/* Friends list with staggered animation */}
        {friends?.length ? (
          <div className="space-y-2">
            {friends.slice(0, 5).map((friend, index) => (
              <div
                key={friend.id ?? index}
                className="flex items-center gap-3 p-2 bg-muted rounded-lg transition-all duration-200 hover:bg-muted/80 hover:scale-[1.02]"
                style={{ animationDelay: `${String(index * 60)}ms` }}
              >
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="text-xs">
                    {(friend.display_name ?? 'U').charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span className="text-sm">
                  {friend.display_name ?? 'User'}
                </span>
              </div>
            ))}
            {friends.length > 5 && (
              <p className="text-xs text-muted-foreground text-center">
                {t('andMore', { count: friends.length - 5 })}
              </p>
            )}
          </div>
        ) : (
          !isPending && (
            <div className="text-sm text-muted-foreground flex items-center gap-2 p-3 bg-muted/50 rounded-lg">
              <Users className="w-4 h-4 opacity-50" />
              {t('noFriends')}
            </div>
          )
        )}

        {/* Invite section */}
        <div className="pt-2 border-t space-y-2">
          <Button
            disabled={isCreatingInvite}
            variant="outline"
            className="w-full active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
            onClick={handleCreateInvite}
          >
            <UserPlus className={`w-4 h-4 mr-2 ${isCreatingInvite ? 'animate-spin' : ''}`} />
            {t('createInvite')}
          </Button>

          {/* Invite link with slide-in */}
          {inviteLink && (
            <div className="flex gap-2 motion-preset-slide-up-sm motion-preset-fade motion-duration-[0.3s]">
              <input
                value={inviteLink}
                readOnly
                className="flex-1 px-3 py-2 text-xs bg-muted rounded-lg font-mono transition-colors duration-200 focus:ring-2 focus:ring-primary/20"
              />
              <Button
                size="icon"
                variant="outline"
                onClick={copyInvite}
                className="active:scale-90 transition-transform duration-150"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-green-500 motion-preset-pop motion-duration-[0.15s]" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </Button>
            </div>
          )}
        </div>
      </div>
    </ProfileSection>
  );
}
