'use client';

import { useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useLocale } from 'next-intl';

import {
  useStartSignupAuthSignupEmailStartPost,
  useCompleteSignupAuthSignupEmailCompletePost,
  useLoginAuthLoginEmailPost,
  useStartLinkAuthLinkEmailStartPost,
  useCompleteLinkAuthLinkEmailCompletePost,
  useResendCodeAuthSignupEmailResendPost,
  getCurrentUserUsersMeGetQueryKey,
} from '@/src/gen/hooks';
import { useAppInit } from '@/providers';

export type EmailAuthStep = 'email' | 'verify' | 'complete';

/**
 * Hook for email signup flow (2-step: email -> verify with code + password + name).
 */
export function useEmailSignup() {
  const locale = useLocale();
  const { reinitialize } = useAppInit();

  const [step, setStep] = useState<EmailAuthStep>('email');
  const [signupToken, setSignupToken] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [expiresIn, setExpiresIn] = useState(0);

  const startSignup = useStartSignupAuthSignupEmailStartPost({
    mutation: {
      onSuccess: (data) => {
        setSignupToken(data.signup_token);
        setExpiresIn(data.expires_in ?? 600);
        setStep('verify');
      },
    },
  });

  const completeSignup = useCompleteSignupAuthSignupEmailCompletePost({
    mutation: {
      onSuccess: () => {
        // Trigger app re-initialization (handles /process_start, PostHog, cache update)
        reinitialize();
        setStep('complete');
        setSignupToken(null);
      },
    },
  });

  const clearStartError = useCallback(() => {
    startSignup.reset();
  }, [startSignup]);

  const clearCompleteError = useCallback(() => {
    completeSignup.reset();
  }, [completeSignup]);

  const resendCode = useResendCodeAuthSignupEmailResendPost();

  const start = useCallback(
    async (emailAddress: string) => {
      setEmail(emailAddress);
      await startSignup.mutateAsync({ data: { email: emailAddress } });
    },
    [startSignup]
  );

  const verify = useCallback(
    async (code: string, password: string, username: string) => {
      if (!signupToken) throw new Error('No signup token');

      await completeSignup.mutateAsync({
        data: {
          signup_token: signupToken,
          code,
          password,
          username,
          language_code: locale,
        },
      });
    },
    [completeSignup, signupToken, locale]
  );

  const resend = useCallback(async () => {
    if (!signupToken) throw new Error('No signup token');
    const result = await resendCode.mutateAsync({
      data: { signup_token: signupToken },
    });
    setExpiresIn(result.expires_in);
  }, [resendCode, signupToken]);

  const reset = useCallback(() => {
    setStep('email');
    setSignupToken(null);
    setEmail('');
    setExpiresIn(0);
  }, []);

  return {
    step,
    email,
    expiresIn,

    isStarting: startSignup.isPending,
    isCompleting: completeSignup.isPending,
    isResending: resendCode.isPending,

    startError: startSignup.error,
    completeError: completeSignup.error,
    resendError: resendCode.error,

    start,
    verify,
    resend,
    reset,
    clearStartError,
    clearCompleteError,
  };
}

/**
 * Hook for email login.
 */
export function useEmailLogin() {
  const { reinitialize } = useAppInit();

  const login = useLoginAuthLoginEmailPost({
    mutation: {
      onSuccess: () => {
        // Trigger app re-initialization (handles /process_start, PostHog, cache update)
        reinitialize();
      },
    },
  });

  const submit = useCallback(
    async (emailOrUsername: string, password: string) => {
      await login.mutateAsync({ data: { email_or_username: emailOrUsername, password } });
    },
    [login]
  );

  const clearError = useCallback(() => {
    login.reset();
  }, [login]);

  return {
    isLoading: login.isPending,
    error: login.error,
    submit,
    clearError,
  };
}

/**
 * Hook for linking email to existing Telegram account.
 */
export function useEmailLink() {
  const queryClient = useQueryClient();

  const [step, setStep] = useState<'email' | 'verify' | 'complete'>('email');
  const [email, setEmail] = useState('');
  const [expiresIn, setExpiresIn] = useState(0);

  const startLink = useStartLinkAuthLinkEmailStartPost({
    mutation: {
      onSuccess: (data) => {
        setExpiresIn(data.expires_in);
        setStep('verify');
      },
    },
  });

  const completeLink = useCompleteLinkAuthLinkEmailCompletePost({
    mutation: {
      onSuccess: () => {
        void queryClient.invalidateQueries({
          queryKey: getCurrentUserUsersMeGetQueryKey(),
        });
        setStep('complete');
      },
    },
  });

  const resendCode = useResendCodeAuthSignupEmailResendPost();

  const start = useCallback(
    async (emailAddress: string) => {
      setEmail(emailAddress);
      await startLink.mutateAsync({ data: { email: emailAddress } });
    },
    [startLink]
  );

  const verify = useCallback(
    async (code: string, password: string) => {
      await completeLink.mutateAsync({ data: { code, password } });
    },
    [completeLink]
  );

  const resend = useCallback(async () => {
    const result = await resendCode.mutateAsync({ data: {} });
    setExpiresIn(result.expires_in);
  }, [resendCode]);

  const reset = useCallback(() => {
    setStep('email');
    setEmail('');
    setExpiresIn(0);
  }, []);

  return {
    step,
    email,
    expiresIn,

    isStarting: startLink.isPending,
    isCompleting: completeLink.isPending,
    isResending: resendCode.isPending,

    startError: startLink.error,
    completeError: completeLink.error,

    start,
    verify,
    resend,
    reset,
  };
}
