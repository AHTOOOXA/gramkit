'use client';

import { useState, useCallback } from 'react';
import {
  useStartResetAuthPasswordResetStartPost,
  useCompleteResetAuthPasswordResetCompletePost,
} from '@/src/gen/hooks';

export type ResetStep = 'email' | 'verify' | 'complete';

/**
 * Hook for password reset flow (2-step: email -> verify with code + new password).
 */
export function usePasswordReset() {
  const [step, setStep] = useState<ResetStep>('email');
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [expiresIn, setExpiresIn] = useState(0);

  const startReset = useStartResetAuthPasswordResetStartPost({
    mutation: {
      onSuccess: (data) => {
        setResetToken(data.reset_token);
        setExpiresIn(data.expires_in);
        setStep('verify');
      },
    },
  });

  const completeReset = useCompleteResetAuthPasswordResetCompletePost({
    mutation: {
      onSuccess: () => {
        setStep('complete');
        setResetToken(null);
      },
    },
  });

  const start = useCallback(
    async (emailAddress: string) => {
      setEmail(emailAddress);
      await startReset.mutateAsync({ data: { email: emailAddress } });
    },
    [startReset]
  );

  const complete = useCallback(
    async (code: string, newPassword: string) => {
      if (!resetToken) throw new Error('No reset token');
      await completeReset.mutateAsync({
        data: {
          reset_token: resetToken,
          code,
          new_password: newPassword,
        },
      });
    },
    [completeReset, resetToken]
  );

  const reset = useCallback(() => {
    setStep('email');
    setResetToken(null);
    setEmail('');
    setExpiresIn(0);
  }, []);

  const clearStartError = useCallback(() => {
    startReset.reset();
  }, [startReset]);

  const clearCompleteError = useCallback(() => {
    completeReset.reset();
  }, [completeReset]);

  return {
    step,
    email,
    expiresIn,
    isStarting: startReset.isPending,
    isCompleting: completeReset.isPending,
    startError: startReset.error,
    completeError: completeReset.error,
    start,
    complete,
    reset,
    clearStartError,
    clearCompleteError,
  };
}
