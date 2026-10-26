<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { Loader2 } from '@lucide/vue';
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';

/**
 * AdminActionDialog — confirm wrapper around shadcn `AlertDialog` for
 * destructive / mutating admin actions (gift, revoke, role change, …). The
 * parent owns the open state (`v-model:open`) and the async work; this just
 * confirms and emits `confirm`. Set `:pending` while the mutation runs.
 *
 * The confirm control is a plain `Button`, not `AlertDialogAction`: the latter
 * is a DialogClose, which closes the dialog (and clears the parent's state)
 * before `confirm` is handled. Here the dialog stays open with a spinner until
 * the parent closes it on success; on failure it stays open for a retry.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    description?: string;
    confirmLabel?: string;
    pending?: boolean;
    destructive?: boolean;
  }>(),
  { description: undefined, confirmLabel: undefined, pending: false, destructive: true },
);

const emit = defineEmits<{
  'update:open': [value: boolean];
  confirm: [];
}>();

const { t } = useI18n();
</script>

<template>
  <AlertDialog
    :open="open"
    @update:open="emit('update:open', $event)"
  >
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>{{ title }}</AlertDialogTitle>
        <AlertDialogDescription v-if="description">
          {{ description }}
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="pending">
          {{ t('admin.actions.cancel') }}
        </AlertDialogCancel>
        <Button
          :variant="destructive ? 'destructive' : 'default'"
          :disabled="pending"
          @click="emit('confirm')"
        >
          <Loader2
            v-if="pending"
            class="h-4 w-4 animate-spin"
          />
          {{ confirmLabel ?? t('admin.actions.confirm') }}
        </Button>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
