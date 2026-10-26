<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { toast } from 'vue-sonner';
import { Gift, Ban, ShieldCheck, Trash2, AlertTriangle } from '@lucide/vue';
import { getErrorMessage } from '@core/errors';
import { useAuth } from '@app/composables/useAuth';
import type { AdminUserDetail } from '@gen/models/AdminUserDetail';
import type { ChangeRoleRequestNewRoleEnumKey } from '@gen/models/ChangeRoleRequest';
import type { GiftSubscriptionRequestDurationEnumKey } from '@gen/models/GiftSubscriptionRequest';
import { useGiftUserSubscriptionAdminUsersUserIdGiftSubscriptionPost } from '@gen/hooks/useGiftUserSubscriptionAdminUsersUserIdGiftSubscriptionPost';
import { useRevokeUserSubscriptionAdminUsersUserIdRevokeSubscriptionPost } from '@gen/hooks/useRevokeUserSubscriptionAdminUsersUserIdRevokeSubscriptionPost';
import { useChangeUserRoleAdminUsersUserIdRolePost } from '@gen/hooks/useChangeUserRoleAdminUsersUserIdRolePost';
import { useResetUserDataAdminUsersUserIdResetPost } from '@gen/hooks/useResetUserDataAdminUsersUserIdResetPost';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import AdminActionDialog from '@app/presentation/components/admin/AdminActionDialog.vue';

/**
 * AdminUserActions — the mutating-action panel on the user detail page.
 *
 * gift / revoke are AdminUser actions; role change and reset are OWNER-only
 * (hidden unless `useAuth().isOwner`; the backend enforces it either way). Each
 * goes through AdminActionDialog (confirm) → the generated mutation hook → a
 * `mutated` emit so the parent refetches. The RBAC caveat (a config owner's role
 * change won't stick) is shown inline under the role control.
 *
 * Reset hard-deletes the user and only works when the backend runs in debug
 * mode (it answers 404 otherwise); after a reset the parent should leave the
 * page, so it gets a separate `reset` emit.
 */
const props = defineProps<{ user: AdminUserDetail }>();
const emit = defineEmits<{ mutated: []; reset: [] }>();

const { t } = useI18n();
const { isOwner, user: me } = useAuth();
// Core rejects resetting your own account (400), so don't offer it.
const canReset = computed(() => props.user.id !== me.value?.id);

type ActionKey = 'gift' | 'revoke' | 'role' | 'reset';

// `action` is kept after the dialog closes so its title, description and
// confirm colour don't flip to empty/default during the exit animation.
const dialogOpen = ref(false);
const action = ref<ActionKey>('gift');
const openAction = (key: ActionKey) => {
  action.value = key;
  dialogOpen.value = true;
};

// Local inputs for the parameterised actions.
const giftDuration = ref<GiftSubscriptionRequestDurationEnumKey>('week');
const newRole = ref<ChangeRoleRequestNewRoleEnumKey>(
  props.user.role as ChangeRoleRequestNewRoleEnumKey,
);
// Keep the role picker in sync after a refetch or when the page switches user.
watch(
  () => props.user.role,
  (role) => {
    newRole.value = role as ChangeRoleRequestNewRoleEnumKey;
  },
);

const gift = useGiftUserSubscriptionAdminUsersUserIdGiftSubscriptionPost();
const revoke = useRevokeUserSubscriptionAdminUsersUserIdRevokeSubscriptionPost();
const changeRole = useChangeUserRoleAdminUsersUserIdRolePost();
const reset = useResetUserDataAdminUsersUserIdResetPost();

const pending = computed(
  () =>
    gift.isPending.value ||
    revoke.isPending.value ||
    changeRole.isPending.value ||
    reset.isPending.value,
);

const close = () => {
  dialogOpen.value = false;
};

const onConfirm = async () => {
  const userId = props.user.id;
  try {
    switch (action.value) {
      case 'gift':
        await gift.mutateAsync({ user_id: userId, data: { duration: giftDuration.value } });
        toast.success(t('admin.users.actions.giftDone'));
        emit('mutated');
        break;
      case 'revoke':
        await revoke.mutateAsync({ user_id: userId });
        toast.success(t('admin.users.actions.revokeDone'));
        emit('mutated');
        break;
      case 'role':
        await changeRole.mutateAsync({ user_id: userId, data: { new_role: newRole.value } });
        toast.success(t('admin.users.actions.roleDone'));
        emit('mutated');
        break;
      case 'reset':
        await reset.mutateAsync({ user_id: userId });
        toast.success(t('admin.users.actions.resetDone'));
        emit('reset');
        break;
    }
    close();
  } catch (e) {
    toast.error(getErrorMessage(e));
  }
};

const dialogTitle = computed(
  () =>
    ({
      gift: t('admin.users.actions.giftConfirmTitle'),
      revoke: t('admin.users.actions.revokeConfirmTitle'),
      role: t('admin.users.actions.roleConfirmTitle'),
      reset: t('admin.users.actions.resetConfirmTitle'),
    })[action.value],
);

const dialogDescription = computed(
  () =>
    ({
      gift: t('admin.users.actions.giftConfirmDesc'),
      revoke: t('admin.users.actions.revokeConfirmDesc'),
      role: t('admin.users.actions.roleConfirmDesc'),
      reset: t('admin.users.actions.resetConfirmDesc'),
    })[action.value],
);
</script>

<template>
  <section class="flex flex-col gap-4 rounded-xl border bg-card p-4">
    <h2 class="text-lg font-semibold">{{ t('admin.users.actions.title') }}</h2>

    <!-- Subscription: gift (with duration) + revoke -->
    <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
      <div class="flex flex-col gap-1">
        <Label
          for="admin-gift-duration"
          class="text-xs text-muted-foreground"
        >
          {{ t('admin.users.actions.giftDuration') }}
        </Label>
        <Select v-model="giftDuration">
          <SelectTrigger
            id="admin-gift-duration"
            class="w-full sm:w-36"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="week">{{ t('admin.users.actions.durationWeek') }}</SelectItem>
            <SelectItem value="month">{{ t('admin.users.actions.durationMonth') }}</SelectItem>
            <SelectItem value="year">{{ t('admin.users.actions.durationYear') }}</SelectItem>
            <SelectItem value="max">{{ t('admin.users.actions.durationMax') }}</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Button
        variant="outline"
        @click="openAction('gift')"
      >
        <Gift class="h-4 w-4" />
        {{ t('admin.users.actions.gift') }}
      </Button>
      <Button
        variant="outline"
        :disabled="!user.has_active_subscription || user.active_subscription?.status === 'CANCELED'"
        @click="openAction('revoke')"
      >
        <Ban class="h-4 w-4" />
        {{ t('admin.users.actions.revoke') }}
      </Button>
    </div>

    <!-- Owner-only: role change + reset -->
    <div
      v-if="isOwner"
      class="flex flex-col gap-2 border-t pt-4"
    >
      <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
        <div class="flex flex-col gap-1">
          <Label
            for="admin-new-role"
            class="text-xs text-muted-foreground"
          >
            {{ t('admin.users.actions.role') }}
          </Label>
          <Select v-model="newRole">
            <SelectTrigger
              id="admin-new-role"
              class="w-full sm:w-36"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="user">{{ t('admin.users.role.user') }}</SelectItem>
              <SelectItem value="admin">{{ t('admin.users.role.admin') }}</SelectItem>
              <SelectItem value="owner">{{ t('admin.users.role.owner') }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline"
          :disabled="newRole === user.role"
          @click="openAction('role')"
        >
          <ShieldCheck class="h-4 w-4" />
          {{ t('admin.users.actions.changeRole') }}
        </Button>
        <Button
          v-if="canReset"
          variant="destructive"
          class="sm:ml-auto"
          @click="openAction('reset')"
        >
          <Trash2 class="h-4 w-4" />
          {{ t('admin.users.actions.reset') }}
        </Button>
      </div>

      <!-- RBAC reality caveat: config-forced owners revert on restart. -->
      <p
        v-if="user.is_config_owner"
        class="flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-400"
      >
        <AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
        {{ t('admin.users.actions.configOwnerWarning') }}
      </p>
    </div>

    <AdminActionDialog
      :open="dialogOpen"
      :title="dialogTitle"
      :description="dialogDescription"
      :pending="pending"
      :destructive="action === 'reset' || action === 'revoke'"
      @update:open="(v) => { if (!v) close(); }"
      @confirm="onConfirm"
    />
  </section>
</template>
