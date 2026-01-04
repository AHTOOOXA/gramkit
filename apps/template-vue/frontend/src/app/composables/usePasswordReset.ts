import { ref, computed } from 'vue';
import {
  useStartResetAuthPasswordResetStartPost,
  useCompleteResetAuthPasswordResetCompletePost,
} from '@/gen/hooks';

export type ResetStep = 'email' | 'verify' | 'complete';

/**
 * Hook for password reset flow (2-step: email -> verify with code + new password).
 */
export function usePasswordReset() {
  const step = ref<ResetStep>('email');
  const resetToken = ref<string | null>(null);
  const email = ref('');
  const expiresIn = ref(0);

  const startReset = useStartResetAuthPasswordResetStartPost({
    mutation: {
      onSuccess: (data) => {
        resetToken.value = data.reset_token;
        expiresIn.value = data.expires_in;
        step.value = 'verify';
      },
    },
  });

  const completeReset = useCompleteResetAuthPasswordResetCompletePost({
    mutation: {
      onSuccess: () => {
        step.value = 'complete';
        resetToken.value = null;
      },
    },
  });

  const start = async (emailAddress: string) => {
    email.value = emailAddress;
    await startReset.mutateAsync({ data: { email: emailAddress } });
  };

  const complete = async (code: string, newPassword: string) => {
    if (!resetToken.value) throw new Error('No reset token');
    await completeReset.mutateAsync({
      data: {
        reset_token: resetToken.value,
        code,
        new_password: newPassword,
      },
    });
  };

  const reset = () => {
    step.value = 'email';
    resetToken.value = null;
    email.value = '';
    expiresIn.value = 0;
  };

  const clearStartError = () => {
    startReset.reset();
  };

  const clearCompleteError = () => {
    completeReset.reset();
  };

  return {
    step,
    email: computed(() => email.value),
    expiresIn: computed(() => expiresIn.value),
    isStarting: computed(() => startReset.isPending.value),
    isCompleting: computed(() => completeReset.isPending.value),
    startError: computed(() => startReset.error.value),
    completeError: computed(() => completeReset.error.value),
    start,
    complete,
    reset,
    clearStartError,
    clearCompleteError,
  };
}
