'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Loader2, Mail, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

import { useEmailLink } from '@/hooks/useEmailAuth';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface AddEmailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function AddEmailDialog({ open, onOpenChange, onSuccess }: AddEmailDialogProps) {
  const t = useTranslations('profile.addEmail');
  const tAuth = useTranslations('auth.email');
  const tCommon = useTranslations('common');
  const emailLink = useEmailLink();

  const [emailInput, setEmailInput] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const canSubmitEmail = emailRegex.test(emailInput);
  const canSubmitVerify = code.length === 6 && password.length >= 8;

  const displayError = (() => {
    if (emailLink.startError) {
      const err = emailLink.startError as { response?: { data?: { detail?: string } } };
      return err.response?.data?.detail ?? t('error');
    }
    if (emailLink.completeError) {
      const err = emailLink.completeError as { response?: { data?: { detail?: string } } };
      return err.response?.data?.detail ?? t('error');
    }
    return null;
  })();

  useEffect(() => {
    if (emailLink.step === 'complete') {
      toast.success(t('success'));
      onSuccess();
      handleClose();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [emailLink.step]);

  const handleSendCode = async () => {
    if (!canSubmitEmail) return;
    try {
      await emailLink.start(emailInput);
    } catch {
      // Error handled by hook
    }
  };

  const handleVerify = async () => {
    if (!canSubmitVerify) return;
    try {
      await emailLink.verify(code, password);
    } catch {
      // Error handled by hook
    }
  };

  const handleResend = async () => {
    try {
      await emailLink.resend();
      toast.success(tAuth('signup.codeSent', { email: emailLink.email }));
    } catch {
      // Error handled by hook
    }
  };

  const handleBack = () => {
    emailLink.reset();
    setCode('');
    setPassword('');
  };

  const handleClose = () => {
    emailLink.reset();
    setEmailInput('');
    setCode('');
    setPassword('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t('title')}</DialogTitle>
          <DialogDescription>
            {emailLink.step === 'email' ? t('step1') : t('step2')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {displayError && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{displayError}</AlertDescription>
            </Alert>
          )}

          {emailLink.step === 'email' ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">{tAuth('email')}</Label>
                <Input
                  id="email"
                  type="email"
                  value={emailInput}
                  onChange={(e) => { setEmailInput(e.target.value); }}
                  placeholder={tAuth('emailPlaceholder')}
                  disabled={emailLink.isStarting}
                  onKeyUp={(e) => e.key === 'Enter' && handleSendCode()}
                />
              </div>

              <Button
                className="w-full"
                disabled={!canSubmitEmail || emailLink.isStarting}
                onClick={handleSendCode}
              >
                {emailLink.isStarting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Mail className="w-4 h-4 mr-2" />
                )}
                {tAuth('link.sendCode')}
              </Button>

              <Button variant="outline" className="w-full" onClick={handleClose}>
                {tCommon('cancel')}
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground text-center">
                {t('codeSent', { email: emailLink.email })}
              </p>

              <div className="space-y-2">
                <Label htmlFor="code">{tAuth('code')}</Label>
                <Input
                  id="code"
                  value={code}
                  onChange={(e) => { setCode(e.target.value); }}
                  placeholder={tAuth('codePlaceholder')}
                  maxLength={6}
                  className="text-center text-2xl tracking-widest font-mono"
                  disabled={emailLink.isCompleting}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">{tAuth('password')}</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); }}
                  placeholder={tAuth('newPasswordPlaceholder')}
                  disabled={emailLink.isCompleting}
                  onKeyUp={(e) => e.key === 'Enter' && handleVerify()}
                />
                <p className="text-xs text-muted-foreground">
                  {tAuth('passwordRequirements')}
                </p>
              </div>

              <Button
                className="w-full"
                disabled={!canSubmitVerify || emailLink.isCompleting}
                onClick={handleVerify}
              >
                {emailLink.isCompleting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {tAuth('link.linkEmail')}
              </Button>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  disabled={emailLink.isCompleting}
                  onClick={handleBack}
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  {tCommon('back')}
                </Button>
                <Button
                  variant="link"
                  className="flex-1"
                  disabled={emailLink.isResending}
                  onClick={handleResend}
                >
                  {tAuth('resendCode')}
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
