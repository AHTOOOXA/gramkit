'use client';

import { useState, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';

import { useEmailSignup } from '@/hooks/useEmailAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface EmailSignupFormProps {
  onSuccess?: () => void;
  onSwitchToLogin?: () => void;
}

export function EmailSignupForm({
  onSuccess,
  onSwitchToLogin,
}: EmailSignupFormProps) {
  const t = useTranslations('auth.email');
  const tCommon = useTranslations('common');

  const {
    step,
    email: savedEmail,
    isStarting,
    isCompleting,
    isResending,
    startError,
    completeError,
    start,
    verify,
    resend,
    reset,
  } = useEmailSignup();

  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');

  const isLoading = isStarting || isCompleting;

  const getErrorMessage = () => {
    const error = startError ?? completeError;
    if (!error) return null;
    return (
      (error as { response?: { data?: { detail?: string } } }).response?.data
        ?.detail ?? t('signup.error')
    );
  };

  const errorMessage = getErrorMessage();

  const handleStartSignup = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await start(email);
    } catch {
      // Error handled by hook
    }
  };

  const handleVerify = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await verify(code, password, username);
      onSuccess?.();
    } catch {
      // Error handled by hook
    }
  };

  if (step === 'email') {
    return (
      <form onSubmit={handleStartSignup} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="signup-email">{t('email')}</Label>
          <Input
            id="signup-email"
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); }}
            placeholder={t('emailPlaceholder')}
            required
            autoComplete="email"
          />
        </div>

        {errorMessage && (
          <Alert variant="destructive">
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        )}

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isStarting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isStarting ? tCommon('loading') : t('signup.continue')}
        </Button>

        {onSwitchToLogin && (
          <p className="text-center text-sm text-muted-foreground">
            {t('signup.haveAccount')}{' '}
            <button
              type="button"
              className="text-primary hover:underline"
              onClick={onSwitchToLogin}
            >
              {t('signup.loginLink')}
            </button>
          </p>
        )}
      </form>
    );
  }

  return (
    <form onSubmit={handleVerify} className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t('signup.codeSent', { email: savedEmail })}
      </p>

      <div className="space-y-2">
        <Label htmlFor="code">{t('code')}</Label>
        <Input
          id="code"
          type="text"
          inputMode="numeric"
          pattern="[0-9]{6}"
          maxLength={6}
          value={code}
          onChange={(e) => { setCode(e.target.value); }}
          placeholder={t('codePlaceholder')}
          required
          autoComplete="one-time-code"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="username">{t('username')}</Label>
        <Input
          id="username"
          type="text"
          value={username}
          onChange={(e) => { setUsername(e.target.value); }}
          placeholder={t('usernamePlaceholder')}
          required
          minLength={3}
          maxLength={32}
          pattern="[a-zA-Z0-9_]+"
          autoComplete="username"
        />
        <p className="text-xs text-muted-foreground">
          {t('usernameRequirements')}
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="signup-password">{t('password')}</Label>
        <Input
          id="signup-password"
          type="password"
          value={password}
          onChange={(e) => { setPassword(e.target.value); }}
          placeholder={t('newPasswordPlaceholder')}
          required
          minLength={8}
          autoComplete="new-password"
        />
        <p className="text-xs text-muted-foreground">
          {t('passwordRequirements')}
        </p>
      </div>

      {errorMessage && (
        <Alert variant="destructive">
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isCompleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {isCompleting ? tCommon('loading') : t('signup.createAccount')}
      </Button>

      <div className="flex justify-between text-sm">
        <button
          type="button"
          className="text-muted-foreground hover:underline"
          onClick={reset}
        >
          {tCommon('back')}
        </button>
        <button
          type="button"
          className="text-primary hover:underline"
          disabled={isResending}
          onClick={() => void resend()}
        >
          {isResending ? tCommon('loading') : t('resendCode')}
        </button>
      </div>
    </form>
  );
}
