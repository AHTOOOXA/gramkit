'use client';

import { Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

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

export interface AdminActionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  /** Set while the mutation runs: spinner on the confirm, cancel/Escape disabled. */
  pending?: boolean;
  /** Red confirm button (default). */
  destructive?: boolean;
  onConfirm: () => void;
}

/**
 * AdminActionDialog — confirm wrapper around shadcn `AlertDialog` for
 * destructive / mutating admin actions (gift, revoke, role change, …). The
 * parent owns the open state and the async work; this just confirms and calls
 * `onConfirm`. Pass `pending` while the mutation runs.
 *
 * The confirm control is a plain `Button`, NOT the alert dialog's Action part:
 * that one is a Radix close button, which closes the dialog (and clears the parent's
 * state) before `onConfirm` resolves. Here the dialog stays open with a spinner
 * until the parent closes it on success; on failure the parent toasts and the
 * dialog stays open for a retry. Escape is ignored while pending.
 *
 * Port of template-vue's `AdminActionDialog.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function AdminActionDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  pending = false,
  destructive = true,
  onConfirm,
}: AdminActionDialogProps) {
  const t = useTranslations('admin');

  return (
    <AlertDialog
      open={open}
      onOpenChange={(next) => {
        if (!next && pending) return;
        onOpenChange(next);
      }}
    >
      {/* Without a description, opt out of Radix's aria-describedby warning. */}
      <AlertDialogContent
        {...(description ? {} : { 'aria-describedby': undefined })}
      >
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          {description && (
            <AlertDialogDescription>{description}</AlertDialogDescription>
          )}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={pending}>
            {t('actions.cancel')}
          </AlertDialogCancel>
          <Button
            variant={destructive ? 'destructive' : 'default'}
            disabled={pending}
            onClick={onConfirm}
          >
            {pending && <Loader2 className="h-4 w-4 animate-spin" />}
            {confirmLabel ?? t('actions.confirm')}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
