'use client';

import { useState, useEffect, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Loader2, Send } from 'lucide-react';

import { getErrorMessage } from '@tma-platform/core-react/errors';
import {
  useSendVerificationCodeAuthLoginTelegramCodeSendPost,
  useVerifyCodeAndLoginAuthLoginTelegramCodeVerifyPost,
  useCheckEmailAuthEmailCheckPost,
} from '@/src/gen/hooks';
import { useTelegramDeeplinkLogin } from '@/hooks/useTelegramDeeplinkLogin';
import { useEmailLogin, useEmailSignup } from '@/hooks/useEmailAuth';
import { usePasswordReset } from '@/hooks/usePasswordReset';
import { useAuthRedirect } from '@/hooks/useAuthRedirect';
import { useAppInit } from '@/providers';

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PasswordInput } from '@/components/ui/password-input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

type EmailFlow = 'email' | 'checking' | 'login' | 'signup_code' | 'signup_complete';
type CodeFlow = 'username' | 'code';
type ResetFlow = 'email' | 'verify' | 'complete';

export default function LoginPage() {
  const router = useRouter();
  const t = useTranslations('login');
  const tAuth = useTranslations('auth.email');
  const tCommon = useTranslations('common');
  const { reinitialize } = useAppInit();
  const { isGuest, isLoading: isAuthLoading } = useAuthRedirect();

  // Telegram code flow
  const { mutateAsync: sendCode, isPending: isSendingCode } =
    useSendVerificationCodeAuthLoginTelegramCodeSendPost();
  const { mutateAsync: verifyCode, isPending: isVerifyingCode } =
    useVerifyCodeAndLoginAuthLoginTelegramCodeVerifyPost();

  const telegramLogin = useTelegramDeeplinkLogin();
  const emailLogin = useEmailLogin();
  const emailSignup = useEmailSignup();
  const passwordReset = usePasswordReset();
  const checkEmail = useCheckEmailAuthEmailCheckPost();

  // Main flow state
  const [flow, setFlow] = useState<'email' | 'telegram' | 'code'>('email');

  // Email flow
  const [emailFlow, setEmailFlow] = useState<EmailFlow>('email');
  const [email, setEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [signupCode, setSignupCode] = useState('');
  const [signupUsername, setSignupUsername] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);

  // Password reset flow
  const [showResetForm, setShowResetForm] = useState(false);
  const [resetFlow, setResetFlow] = useState<ResetFlow>('email');
  const [resetEmail, setResetEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [resetPassword, setResetPassword] = useState('');

  // Code flow
  const [codeFlow, setCodeFlow] = useState<CodeFlow>('username');
  const [username, setUsername] = useState('');
  const [code, setCode] = useState('');
  const [codeError, setCodeError] = useState<string | null>(null);

  const isLoading = isSendingCode || isVerifyingCode;
  const canSubmitUsername = username.length >= 3;
  const canSubmitCode = code.length === 6;

  const displayError = codeError ?? telegramLogin.error;

  // Watch for successful Telegram deeplink login
  useEffect(() => {
    if (!telegramLogin.isPolling && !telegramLogin.error && telegramLogin.botUrl) {
      router.push('/');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [telegramLogin.isPolling]);

  const handleOpenTelegram = async () => {
    setCodeError(null);
    try {
      await telegramLogin.start();
    } catch {
      // Error handled in hook
    }
  };

  // Email flow handlers
  const handleEmailContinue = async (e: FormEvent) => {
    e.preventDefault();
    setEmailError(null);
    setEmailFlow('checking');

    try {
      const result = await checkEmail.mutateAsync({ data: { email } });

      if (result.exists) {
        // Email exists - show login form
        setEmailFlow('login');
      } else {
        // Email doesn't exist - start signup flow
        await emailSignup.start(email);
        setEmailFlow('signup_code');
      }
    } catch (e: unknown) {
      setEmailError(getErrorMessage(e));
      setEmailFlow('email');
    }
  };

  const handleEmailLogin = async (e: FormEvent) => {
    e.preventDefault();
    setEmailError(null);

    try {
      await emailLogin.submit(email, loginPassword);
      reinitialize();
      router.push('/');
    } catch (e: unknown) {
      setEmailError(getErrorMessage(e));
    }
  };

  const handleCompleteSignup = async (e: FormEvent) => {
    e.preventDefault();
    setEmailError(null);

    try {
      await emailSignup.verify(signupCode, signupPassword, signupUsername);
      reinitialize();
      router.push('/');
    } catch (e: unknown) {
      setEmailError(getErrorMessage(e));
    }
  };

  const handleBackToEmail = () => {
    setEmailFlow('email');
    setLoginPassword('');
    setSignupCode('');
    setSignupUsername('');
    setSignupPassword('');
    setEmailError(null);
    emailSignup.reset();
  };

  // Password reset handlers
  const handleStartReset = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await passwordReset.start(resetEmail);
      setResetFlow('verify');
    } catch {
      // Error handled by hook
    }
  };

  const handleCompleteReset = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await passwordReset.complete(resetCode, resetPassword);
      setResetFlow('complete');
    } catch {
      // Error handled by hook
    }
  };

  const handleBackToLogin = () => {
    setShowResetForm(false);
    setResetFlow('email');
    setResetEmail('');
    setResetCode('');
    setResetPassword('');
    setFlow('email');
    setEmailFlow('email');
  };

  // Telegram code flow handlers
  const handleSendCode = async () => {
    if (!canSubmitUsername) return;
    setCodeError(null);

    try {
      await sendCode({
        data: { username: username.replace('@', '') },
      });
      setCodeFlow('code');
    } catch (e: unknown) {
      setCodeError(getErrorMessage(e));
    }
  };

  const handleVerifyCode = async () => {
    if (!canSubmitCode) return;
    setCodeError(null);

    try {
      await verifyCode({
        data: {
          username: username.replace('@', ''),
          code: code,
        },
      });

      reinitialize();
      router.push('/');
    } catch (e: unknown) {
      setCodeError(getErrorMessage(e));
    }
  };

  const goBackFromCode = () => {
    setCodeFlow('username');
    setCode('');
    setCodeError(null);
  };

  const getPasswordResetError = () => {
    const error = passwordReset.startError ?? passwordReset.completeError;
    if (error) {
      return (
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ??
        tAuth('reset.error')
      );
    }
    return null;
  };

  const resetError = getPasswordResetError();

  // Show loading while checking auth state or redirecting
  if (isAuthLoading || !isGuest) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Password reset view (when in verify or complete state)
  if (flow === 'email' && (resetFlow === 'verify' || resetFlow === 'complete')) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{tAuth('reset.title')}</CardTitle>
            <CardDescription>
              {resetFlow === 'verify' && tAuth('reset.codeSent', { email: passwordReset.email })}
              {resetFlow === 'complete' && tAuth('reset.success')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {resetFlow === 'verify' && (
              <form onSubmit={handleCompleteReset} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="reset-code">{tAuth('code')}</Label>
                  <Input
                    id="reset-code"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    value={resetCode}
                    onChange={(e) => {
                      setResetCode(e.target.value);
                      passwordReset.clearCompleteError();
                    }}
                    placeholder={tAuth('codePlaceholder')}
                    required
                    autoComplete="one-time-code"
                    disabled={passwordReset.isCompleting}
                    autoFocus
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="reset-password">{tAuth('reset.newPassword')}</Label>
                  <PasswordInput
                    id="reset-password"
                    value={resetPassword}
                    onChange={(e) => {
                      setResetPassword(e.target.value);
                      passwordReset.clearCompleteError();
                    }}
                    placeholder={tAuth('newPasswordPlaceholder')}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    disabled={passwordReset.isCompleting}
                    showRequirements
                    requirementsText={tAuth('passwordRequirements')}
                  />
                </div>

                {resetError && (
                  <Alert variant="destructive">
                    <AlertDescription role="alert">{resetError}</AlertDescription>
                  </Alert>
                )}

                <Button
                  type="submit"
                  className="w-full"
                  disabled={passwordReset.isCompleting || !resetPassword}
                >
                  {passwordReset.isCompleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {passwordReset.isCompleting ? tCommon('loading') : tAuth('reset.resetPassword')}
                </Button>

                <button
                  type="button"
                  className="text-sm text-muted-foreground hover:underline"
                  onClick={() => { setResetFlow('email'); }}
                >
                  {tCommon('back')}
                </button>
              </form>
            )}

            {resetFlow === 'complete' && (
              <div className="space-y-4 text-center">
                <Button onClick={handleBackToLogin}>
                  {tAuth('reset.backToLogin')}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{t('title')}</CardTitle>
          {/* Only show description for sub-flows, not initial email screen */}
          {!(flow === 'email' && emailFlow === 'email') && (
            <CardDescription>
              {flow === 'email' && emailFlow === 'login' && tAuth('login.description')}
              {flow === 'email' && emailFlow === 'signup_code' && tAuth('signup.description')}
              {flow === 'telegram' && telegramLogin.isPolling && t('telegram.waiting')}
              {flow === 'code' && codeFlow === 'username' && t('usernameStep.description')}
              {flow === 'code' && codeFlow === 'code' && t('codeStep.description')}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Email-first flow */}
            {flow === 'email' && (
              <>
                {/* Step 1: Email input - always visible at top */}
                {emailFlow === 'email' && (
                  <form onSubmit={handleEmailContinue} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="email">{tAuth('email')}</Label>
                      <Input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          setEmailError(null);
                        }}
                        placeholder={tAuth('emailPlaceholder')}
                        required
                        autoComplete="email"
                        disabled={checkEmail.isPending}
                        autoFocus
                      />
                    </div>

                    {emailError && (
                      <Alert variant="destructive">
                        <AlertDescription role="alert">{emailError}</AlertDescription>
                      </Alert>
                    )}

                    <Button type="submit" variant="secondary" className="w-full" disabled={checkEmail.isPending}>
                      {checkEmail.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {checkEmail.isPending ? tCommon('loading') : tAuth('continue')}
                    </Button>

                    {/* Divider */}
                    <div className="relative">
                      <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t" />
                      </div>
                      <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-background px-2 text-muted-foreground">
                          {t('or')}
                        </span>
                      </div>
                    </div>

                    {/* Telegram button - primary (faster/recommended) */}
                    <Button
                      type="button"
                      className="w-full flex items-center gap-2"
                      onClick={() => { setFlow('telegram'); }}
                    >
                      <Send className="h-4 w-4" />
                      {t('telegram.continueWith')}
                    </Button>
                  </form>
                )}

                {/* Step 2a: Login form (email exists) */}
                {emailFlow === 'login' && !showResetForm && (
                  <form onSubmit={handleEmailLogin} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="login-email">{tAuth('email')}</Label>
                      <Input
                        id="login-email"
                        type="email"
                        value={email}
                        disabled
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="login-password">{tAuth('password')}</Label>
                      <PasswordInput
                        id="login-password"
                        value={loginPassword}
                        onChange={(e) => {
                          setLoginPassword(e.target.value);
                          setEmailError(null);
                        }}
                        placeholder={tAuth('passwordPlaceholder')}
                        required
                        autoComplete="current-password"
                        disabled={emailLogin.isLoading}
                        autoFocus
                      />
                    </div>

                    {emailError && (
                      <Alert variant="destructive">
                        <AlertDescription role="alert">{emailError}</AlertDescription>
                      </Alert>
                    )}

                    <Button type="submit" className="w-full" disabled={emailLogin.isLoading}>
                      {emailLogin.isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {emailLogin.isLoading ? tCommon('loading') : tAuth('login.submit')}
                    </Button>

                    <button
                      type="button"
                      className="text-sm text-primary hover:underline"
                      onClick={() => {
                        setResetEmail(email);
                        setShowResetForm(true);
                      }}
                    >
                      {tAuth('reset.forgotPassword')}
                    </button>

                    <Button
                      variant="ghost"
                      className="w-full"
                      onClick={handleBackToEmail}
                    >
                      {tCommon('back')}
                    </Button>
                  </form>
                )}

                {/* Step 2c: Password reset email form */}
                {emailFlow === 'login' && showResetForm && (
                  <form onSubmit={handleStartReset} className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                      {tAuth('reset.emailDescription')}
                    </p>

                    <div className="space-y-2">
                      <Label htmlFor="reset-email">{tAuth('email')}</Label>
                      <Input
                        id="reset-email"
                        type="email"
                        value={resetEmail}
                        onChange={(e) => {
                          setResetEmail(e.target.value);
                          passwordReset.clearStartError();
                        }}
                        placeholder={tAuth('emailPlaceholder')}
                        required
                        autoComplete="email"
                        disabled={passwordReset.isStarting}
                        autoFocus
                      />
                    </div>

                    {resetError && (
                      <Alert variant="destructive">
                        <AlertDescription role="alert">{resetError}</AlertDescription>
                      </Alert>
                    )}

                    <Button type="submit" className="w-full" disabled={passwordReset.isStarting}>
                      {passwordReset.isStarting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {passwordReset.isStarting ? tCommon('loading') : tAuth('reset.sendCode')}
                    </Button>

                    <Button
                      variant="ghost"
                      className="w-full"
                      onClick={() => {
                        setShowResetForm(false);
                        setResetEmail('');
                      }}
                    >
                      {tAuth('reset.backToLogin')}
                    </Button>
                  </form>
                )}

                {/* Step 2d: Signup form (email doesn't exist) */}
                {emailFlow === 'signup_code' && (
                  <form onSubmit={handleCompleteSignup} className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                      {tAuth('signup.codeSent', { email: emailSignup.email })}
                    </p>

                    <div className="space-y-2">
                      <Label htmlFor="signup-code">{tAuth('code')}</Label>
                      <Input
                        id="signup-code"
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]{6}"
                        maxLength={6}
                        value={signupCode}
                        onChange={(e) => {
                          setSignupCode(e.target.value);
                          setEmailError(null);
                        }}
                        placeholder={tAuth('codePlaceholder')}
                        required
                        autoComplete="one-time-code"
                        disabled={emailSignup.isCompleting}
                        autoFocus
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="signup-username">{tAuth('username')}</Label>
                      <Input
                        id="signup-username"
                        type="text"
                        value={signupUsername}
                        onChange={(e) => {
                          setSignupUsername(e.target.value);
                          setEmailError(null);
                        }}
                        placeholder={tAuth('usernamePlaceholder')}
                        required
                        minLength={3}
                        maxLength={32}
                        pattern="[a-zA-Z0-9_]+"
                        autoComplete="username"
                        disabled={emailSignup.isCompleting}
                      />
                      <p className="text-xs text-muted-foreground">
                        {tAuth('usernameRequirements')}
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="signup-password">{tAuth('password')}</Label>
                      <PasswordInput
                        id="signup-password"
                        value={signupPassword}
                        onChange={(e) => {
                          setSignupPassword(e.target.value);
                          setEmailError(null);
                        }}
                        placeholder={tAuth('newPasswordPlaceholder')}
                        required
                        minLength={8}
                        autoComplete="new-password"
                        disabled={emailSignup.isCompleting}
                        showRequirements
                        requirementsText={tAuth('passwordRequirements')}
                      />
                    </div>

                    {emailError && (
                      <Alert variant="destructive">
                        <AlertDescription role="alert">{emailError}</AlertDescription>
                      </Alert>
                    )}

                    <Button
                      type="submit"
                      className="w-full"
                      disabled={emailSignup.isCompleting || !signupPassword}
                    >
                      {emailSignup.isCompleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {emailSignup.isCompleting ? tCommon('loading') : tAuth('signup.createAccount')}
                    </Button>

                    <div className="flex justify-between text-sm">
                      <button
                        type="button"
                        className="text-muted-foreground hover:underline"
                        onClick={handleBackToEmail}
                      >
                        {tCommon('back')}
                      </button>
                      <button
                        type="button"
                        className="text-primary hover:underline"
                        disabled={emailSignup.isResending}
                        onClick={() => void emailSignup.resend()}
                      >
                        {emailSignup.isResending ? tCommon('loading') : tAuth('resendCode')}
                      </button>
                    </div>
                  </form>
                )}

                {/* Checking state */}
                {emailFlow === 'checking' && (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                )}
              </>
            )}

            {/* Telegram deeplink flow */}
            {flow === 'telegram' && (
              <>
                {displayError && (
                  <Alert variant="destructive">
                    <AlertDescription role="alert">{displayError}</AlertDescription>
                  </Alert>
                )}

                {telegramLogin.isPolling ? (
                  <div className="space-y-4 py-4">
                    <div className="flex flex-col items-center space-y-4">
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                      <p className="text-center text-sm">
                        {t('telegram.waiting')}
                      </p>
                      <p className="text-center text-xs text-muted-foreground">
                        {t('telegram.hint')}
                      </p>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        className="flex-1"
                        onClick={telegramLogin.reset}
                      >
                        {tCommon('cancel')}
                      </Button>
                      <Button
                        variant="outline"
                        className="flex-1"
                        onClick={telegramLogin.openTelegram}
                      >
                        {t('telegram.reopen')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <Button
                      className="w-full"
                      disabled={telegramLogin.isStarting || isLoading}
                      onClick={handleOpenTelegram}
                    >
                      {telegramLogin.isStarting ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4 mr-2" />
                      )}
                      {t('telegram.openButton')}
                    </Button>
                    <p className="text-xs text-center text-muted-foreground">
                      {t('telegram.canRegister')}
                    </p>

                    <Button
                      variant="ghost"
                      className="w-full"
                      onClick={() => { setFlow('email'); }}
                    >
                      {tCommon('back')}
                    </Button>
                  </>
                )}
              </>
            )}

            {/* Telegram code fallback flow */}
            {flow === 'code' && (
              <>
                {displayError && (
                  <Alert variant="destructive">
                    <AlertDescription role="alert">{displayError}</AlertDescription>
                  </Alert>
                )}

                {codeFlow === 'username' ? (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="username">{t('usernameStep.label')}</Label>
                      <Input
                        id="username"
                        value={username}
                        onChange={(e) => {
                          setUsername(e.target.value);
                          setCodeError(null);
                        }}
                        placeholder={t('usernameStep.placeholder')}
                        disabled={isLoading}
                        onKeyUp={(e) => e.key === 'Enter' && handleSendCode()}
                        autoFocus
                      />
                      <p className="text-xs text-muted-foreground">
                        {t('usernameStep.hint')}
                      </p>
                    </div>

                    <Button
                      disabled={!canSubmitUsername || isLoading}
                      className="w-full"
                      onClick={handleSendCode}
                    >
                      {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      {t('usernameStep.submit')}
                    </Button>

                    <Button
                      variant="ghost"
                      className="w-full"
                      onClick={() => { setFlow('email'); }}
                    >
                      {tCommon('back')}
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="code">{t('codeStep.label')}</Label>
                      <Input
                        id="code"
                        value={code}
                        onChange={(e) => {
                          setCode(e.target.value);
                          setCodeError(null);
                        }}
                        placeholder={t('codeStep.placeholder')}
                        maxLength={6}
                        className="text-center text-2xl tracking-widest font-mono"
                        disabled={isLoading}
                        onKeyUp={(e) => e.key === 'Enter' && handleVerifyCode()}
                        autoFocus
                      />
                      <p className="text-xs text-muted-foreground">
                        {t('codeStep.hint', { username })}
                      </p>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        disabled={isLoading}
                        className="flex-1"
                        onClick={goBackFromCode}
                      >
                        {t('codeStep.back')}
                      </Button>
                      <Button
                        disabled={!canSubmitCode || isLoading}
                        className="flex-1"
                        onClick={handleVerifyCode}
                      >
                        {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        {t('codeStep.submit')}
                      </Button>
                    </div>

                    <Button
                      variant="link"
                      disabled={isLoading}
                      className="w-full"
                      onClick={handleSendCode}
                    >
                      {t('codeStep.resend')}
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
