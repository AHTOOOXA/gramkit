'use client';

import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Loader2, Send, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

import { useTelegramLink } from '@/hooks/useTelegramLink';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface LinkTelegramDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function LinkTelegramDialog({ open, onOpenChange, onSuccess }: LinkTelegramDialogProps) {
  const t = useTranslations('profile.linkTelegram');
  const tCommon = useTranslations('common');
  const tLogin = useTranslations('login.telegram');
  const telegramLink = useTelegramLink();

  useEffect(() => {
    if (!telegramLink.isPolling && !telegramLink.error && telegramLink.botUrl) {
      toast.success(t('success'));
      onSuccess();
      handleClose();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [telegramLink.isPolling]);

  const handleStart = async () => {
    try {
      await telegramLink.start();
    } catch {
      // Error handled in hook
    }
  };

  const handleClose = () => {
    telegramLink.reset();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t('title')}</DialogTitle>
          <DialogDescription>
            {t('description')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {telegramLink.error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{telegramLink.error}</AlertDescription>
            </Alert>
          )}

          {telegramLink.isPolling ? (
            <div className="space-y-4">
              <div className="flex flex-col items-center space-y-4">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-center text-sm">{t('waiting')}</p>
                <p className="text-center text-xs text-muted-foreground">
                  {tLogin('hint')}
                </p>
              </div>

              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={handleClose}>
                  {tCommon('cancel')}
                </Button>
                <Button variant="outline" className="flex-1" onClick={telegramLink.openTelegram}>
                  <ExternalLink className="w-4 h-4 mr-2" />
                  {tLogin('reopen')}
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-center text-sm text-muted-foreground">
                {t('scanQr')}
              </p>

              <Button
                className="w-full"
                disabled={telegramLink.isStarting}
                onClick={handleStart}
              >
                {telegramLink.isStarting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Send className="w-4 h-4 mr-2" />
                )}
                {t('openTelegram')}
              </Button>

              <Button variant="outline" className="w-full" onClick={handleClose}>
                {tCommon('cancel')}
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
