'use client';

import { useEffect, useState } from 'react';
import { getErrorMessage } from '@tma-platform/core-react/errors';
import { AlertTriangle, Ban, Gift, ShieldCheck, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { AdminActionDialog } from '@/components/admin/AdminActionDialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useAuth } from '@/hooks';
import { useChangeUserRoleAdminUsersUserIdRolePost } from '@/src/gen/hooks/useChangeUserRoleAdminUsersUserIdRolePost';
import { useGiftUserSubscriptionAdminUsersUserIdGiftSubscriptionPost } from '@/src/gen/hooks/useGiftUserSubscriptionAdminUsersUserIdGiftSubscriptionPost';
import { useResetUserDataAdminUsersUserIdResetPost } from '@/src/gen/hooks/useResetUserDataAdminUsersUserIdResetPost';
import { useRevokeUserSubscriptionAdminUsersUserIdRevokeSubscriptionPost } from '@/src/gen/hooks/useRevokeUserSubscriptionAdminUsersUserIdRevokeSubscriptionPost';
import type { AdminUserDetail } from '@/src/gen/models/AdminUserDetail';
import {
  changeRoleRequestNewRoleEnum,
  type ChangeRoleRequestNewRoleEnum,
} from '@/src/gen/models/ChangeRoleRequest';
import {
  giftSubscriptionRequestDurationEnum,
  type GiftSubscriptionRequestDurationEnum,
} from '@/src/gen/models/GiftSubscriptionRequest';

type ActionKey = 'gift' | 'revoke' | 'role' | 'reset';

// Duration labels (`admin.users.actions.duration<Week|Month|…>`) for the
// generated enum values.
const durationKey = (value: string) =>
  `users.actions.duration${value.charAt(0).toUpperCase()}${value.slice(1)}`;

/**
 * AdminUserActions — the mutating-action panel on the user detail page.
 *
 * gift / revoke are AdminUser actions; role change and reset are OWNER-only
 * (hidden unless `useAuth().isOwner`; the backend enforces it either way). Each
 * goes through AdminActionDialog (confirm) → the generated mutation hook →
 * `onMutated` so the parent refetches. The RBAC caveat (a config owner's role
 * change won't stick) is shown inline under the role control.
 *
 * Reset hard-deletes the user and only works when the backend runs in debug
 * mode (it answers 404 otherwise); after a reset the parent should leave the
 * page, so it gets a separate `onReset`.
 *
 * Port of template-vue's `AdminUserActions.vue`.
 */
export function AdminUserActions({
  user,
  onMutated,
  onReset,
}: {
  user: AdminUserDetail;
  onMutated: () => void;
  onReset: () => void;
}) {
  const t = useTranslations('admin');
  const { isOwner, user: me } = useAuth();
  // Core rejects resetting your own account (400), so don't offer it.
  const canReset = user.id !== me?.id;

  // `action` is kept after the dialog closes so its title, description and
  // confirm colour don't flip to empty/default during the exit animation.
  const [dialogOpen, setDialogOpen] = useState(false);
  const [action, setAction] = useState<ActionKey>('gift');
  const openAction = (key: ActionKey) => {
    setAction(key);
    setDialogOpen(true);
  };

  // Local inputs for the parameterised actions.
  const [giftDuration, setGiftDuration] =
    useState<GiftSubscriptionRequestDurationEnum>('week');
  const [newRole, setNewRole] = useState<ChangeRoleRequestNewRoleEnum>(
    user.role as ChangeRoleRequestNewRoleEnum
  );
  // Keep the role picker in sync after a refetch or when the page switches user.
  useEffect(() => {
    setNewRole(user.role as ChangeRoleRequestNewRoleEnum);
  }, [user.role]);

  const gift = useGiftUserSubscriptionAdminUsersUserIdGiftSubscriptionPost();
  const revoke =
    useRevokeUserSubscriptionAdminUsersUserIdRevokeSubscriptionPost();
  const changeRole = useChangeUserRoleAdminUsersUserIdRolePost();
  const reset = useResetUserDataAdminUsersUserIdResetPost();

  const pending =
    gift.isPending ||
    revoke.isPending ||
    changeRole.isPending ||
    reset.isPending;

  const close = () => {
    setDialogOpen(false);
  };

  const onConfirm = async () => {
    const userId = user.id;
    try {
      switch (action) {
        case 'gift':
          await gift.mutateAsync({
            user_id: userId,
            data: { duration: giftDuration },
          });
          toast.success(t('users.actions.giftDone'));
          onMutated();
          break;
        case 'revoke':
          await revoke.mutateAsync({ user_id: userId });
          toast.success(t('users.actions.revokeDone'));
          onMutated();
          break;
        case 'role':
          await changeRole.mutateAsync({
            user_id: userId,
            data: { new_role: newRole },
          });
          toast.success(t('users.actions.roleDone'));
          onMutated();
          break;
        case 'reset':
          await reset.mutateAsync({ user_id: userId });
          toast.success(t('users.actions.resetDone'));
          onReset();
          break;
      }
      close();
    } catch (e) {
      // Keep the dialog open so the admin can retry.
      toast.error(getErrorMessage(e));
    }
  };

  const dialogTitle = {
    gift: t('users.actions.giftConfirmTitle'),
    revoke: t('users.actions.revokeConfirmTitle'),
    role: t('users.actions.roleConfirmTitle'),
    reset: t('users.actions.resetConfirmTitle'),
  }[action];

  const dialogDescription = {
    gift: t('users.actions.giftConfirmDesc'),
    revoke: t('users.actions.revokeConfirmDesc'),
    role: t('users.actions.roleConfirmDesc'),
    reset: t('users.actions.resetConfirmDesc'),
  }[action];

  return (
    <section className="bg-card flex flex-col gap-4 rounded-xl border p-4">
      <h2 className="text-lg font-semibold">{t('users.actions.title')}</h2>

      {/* Subscription: gift (with duration) + revoke */}
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
        <div className="flex flex-col gap-1">
          <Label
            htmlFor="admin-gift-duration"
            className="text-muted-foreground text-xs"
          >
            {t('users.actions.giftDuration')}
          </Label>
          <Select
            value={giftDuration}
            onValueChange={(value) => {
              setGiftDuration(value as GiftSubscriptionRequestDurationEnum);
            }}
          >
            <SelectTrigger id="admin-gift-duration" className="w-full sm:w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.values(giftSubscriptionRequestDurationEnum).map(
                (value) => (
                  <SelectItem key={value} value={value}>
                    {t.has(durationKey(value)) ? t(durationKey(value)) : value}
                  </SelectItem>
                )
              )}
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline"
          onClick={() => {
            openAction('gift');
          }}
        >
          <Gift className="h-4 w-4" />
          {t('users.actions.gift')}
        </Button>
        <Button
          variant="outline"
          disabled={
            !user.has_active_subscription ||
            user.active_subscription?.status === 'CANCELED'
          }
          onClick={() => {
            openAction('revoke');
          }}
        >
          <Ban className="h-4 w-4" />
          {t('users.actions.revoke')}
        </Button>
      </div>

      {/* Owner-only: role change + reset */}
      {isOwner && (
        <div className="flex flex-col gap-2 border-t pt-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
            <div className="flex flex-col gap-1">
              <Label
                htmlFor="admin-new-role"
                className="text-muted-foreground text-xs"
              >
                {t('users.actions.role')}
              </Label>
              <Select
                value={newRole}
                onValueChange={(value) => {
                  setNewRole(value as ChangeRoleRequestNewRoleEnum);
                }}
              >
                <SelectTrigger id="admin-new-role" className="w-full sm:w-36">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(changeRoleRequestNewRoleEnum).map((value) => (
                    <SelectItem key={value} value={value}>
                      {t.has(`users.role.${value}`)
                        ? t(`users.role.${value}`)
                        : value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              variant="outline"
              disabled={newRole === user.role}
              onClick={() => {
                openAction('role');
              }}
            >
              <ShieldCheck className="h-4 w-4" />
              {t('users.actions.changeRole')}
            </Button>
            {canReset && (
              <Button
                variant="destructive"
                className="sm:ml-auto"
                onClick={() => {
                  openAction('reset');
                }}
              >
                <Trash2 className="h-4 w-4" />
                {t('users.actions.reset')}
              </Button>
            )}
          </div>

          {/* RBAC reality caveat: config-forced owners revert on restart. */}
          {user.is_config_owner && (
            <p className="flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-400">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {t('users.actions.configOwnerWarning')}
            </p>
          )}
        </div>
      )}

      <AdminActionDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          if (!open) close();
        }}
        title={dialogTitle}
        description={dialogDescription}
        pending={pending}
        destructive={action === 'reset' || action === 'revoke'}
        onConfirm={() => void onConfirm()}
      />
    </section>
  );
}
