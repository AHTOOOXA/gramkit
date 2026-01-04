'use client';

import { useState, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';

import { useEmailLogin } from '@/hooks/useEmailAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface EmailLoginFormProps {
  onSuccess?: () => void;
  onSwitchToSignup?: () => void;
}

export function EmailLoginForm({
  onSuccess,
  onSwitchToSignup,
}: EmailLoginFormProps) {
  const t = useTranslations('auth.email');
  const tCommon = useTranslations('common');

  const { isLoading, error, submit } = useEmailLogin();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const errorMessage = error
    ? (error as { response?: { data?: { detail?: string } } }).response?.data
        ?.detail ?? t('login.error')
    : null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await submit(email, password);
      onSuccess?.();
    } catch {
      // Error handled by hook
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">{t('email')}</Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => { setEmail(e.target.value); }}
          placeholder={t('emailPlaceholder')}
          required
          autoComplete="email"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">{t('password')}</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => { setPassword(e.target.value); }}
          placeholder={t('passwordPlaceholder')}
          required
          autoComplete="current-password"
        />
      </div>

      {errorMessage && (
        <Alert variant="destructive">
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {isLoading ? tCommon('loading') : t('login.submit')}
      </Button>

      {onSwitchToSignup && (
        <p className="text-center text-sm text-muted-foreground">
          {t('login.noAccount')}{' '}
          <button
            type="button"
            className="text-primary hover:underline"
            onClick={onSwitchToSignup}
          >
            {t('login.signupLink')}
          </button>
        </p>
      )}
    </form>
  );
}
