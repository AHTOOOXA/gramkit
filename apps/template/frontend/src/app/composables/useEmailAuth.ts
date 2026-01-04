import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  useLoginAuthLoginEmailPost,
  useStartSignupAuthSignupEmailStartPost,
  useCompleteSignupAuthSignupEmailCompletePost,
  useStartLinkAuthLinkEmailStartPost,
  useCompleteLinkAuthLinkEmailCompletePost,
  useResendCodeAuthSignupEmailResendPost,
  getCurrentUserUsersMeGetQueryKey,
} from '@/gen/hooks';
import { useQueryClient } from '@tanstack/vue-query';
import { useAppInit } from './useAppInit';

export type EmailAuthStep = 'email' | 'verify' | 'complete';

export function useEmailSignup() {
  const { locale } = useI18n();
  const { reinitialize } = useAppInit();

  const step = ref<EmailAuthStep>('email');
  const signupToken = ref<string | null>(null);
  const email = ref('');
  const expiresIn = ref(0);

  const startSignup = useStartSignupAuthSignupEmailStartPost({
    mutation: {
      onSuccess: (data) => {
        signupToken.value = data.signup_token;
        expiresIn.value = data.expires_in ?? 600;
        step.value = 'verify';
      },
    },
  });

  const completeSignup = useCompleteSignupAuthSignupEmailCompletePost({
    mutation: {
      onSuccess: () => {
        // Trigger app re-initialization (handles /process_start, PostHog, cache update)
        reinitialize();
        step.value = 'complete';
        signupToken.value = null;
      },
    },
  });

  const resendCode = useResendCodeAuthSignupEmailResendPost();

  const start = async (emailAddress: string) => {
    email.value = emailAddress;
    await startSignup.mutateAsync({ data: { email: emailAddress } });
  };

  const verify = async (code: string, password: string, username: string) => {
    if (!signupToken.value) throw new Error('No signup token');

    await completeSignup.mutateAsync({
      data: {
        signup_token: signupToken.value,
        code,
        password,
        username,
        language_code: locale.value,
      },
    });
  };

  const resend = async () => {
    if (!signupToken.value) throw new Error('No signup token');
    const result = await resendCode.mutateAsync({
      data: { signup_token: signupToken.value },
    });
    expiresIn.value = result.expires_in;
  };

  const reset = () => {
    step.value = 'email';
    signupToken.value = null;
    email.value = '';
    expiresIn.value = 0;
    startSignup.reset();
    completeSignup.reset();
  };

  const clearStartError = () => {
    startSignup.reset();
  };

  const clearCompleteError = () => {
    completeSignup.reset();
  };

  return {
    step,
    email: computed(() => email.value),
    expiresIn: computed(() => expiresIn.value),

    isStarting: computed(() => startSignup.isPending.value),
    isCompleting: computed(() => completeSignup.isPending.value),
    isResending: computed(() => resendCode.isPending.value),

    startError: computed(() => startSignup.error.value),
    completeError: computed(() => completeSignup.error.value),
    resendError: computed(() => resendCode.error.value),

    start,
    verify,
    resend,
    reset,
    clearStartError,
    clearCompleteError,
  };
}

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

  const submit = async (emailOrUsername: string, password: string) => {
    await login.mutateAsync({ data: { email_or_username: emailOrUsername, password } });
  };

  const clearError = () => {
    login.reset();
  };

  return {
    isLoading: computed(() => login.isPending.value),
    error: computed(() => login.error.value),
    submit,
    clearError,
  };
}

export function useEmailLink() {
  const queryClient = useQueryClient();

  const step = ref<'email' | 'verify' | 'complete'>('email');
  const email = ref('');
  const expiresIn = ref(0);

  const startLink = useStartLinkAuthLinkEmailStartPost({
    mutation: {
      onSuccess: (data) => {
        expiresIn.value = data.expires_in;
        step.value = 'verify';
      },
    },
  });

  const completeLink = useCompleteLinkAuthLinkEmailCompletePost({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() });
        step.value = 'complete';
      },
    },
  });

  const resendCode = useResendCodeAuthSignupEmailResendPost();

  const start = async (emailAddress: string) => {
    email.value = emailAddress;
    await startLink.mutateAsync({ data: { email: emailAddress } });
  };

  const verify = async (code: string, password: string) => {
    await completeLink.mutateAsync({ data: { code, password } });
  };

  const resend = async () => {
    const result = await resendCode.mutateAsync({ data: {} });
    expiresIn.value = result.expires_in;
  };

  const reset = () => {
    step.value = 'email';
    email.value = '';
    expiresIn.value = 0;
  };

  return {
    step,
    email: computed(() => email.value),
    expiresIn: computed(() => expiresIn.value),

    isStarting: computed(() => startLink.isPending.value),
    isCompleting: computed(() => completeLink.isPending.value),
    isResending: computed(() => resendCode.isPending.value),

    startError: computed(() => startLink.error.value),
    completeError: computed(() => completeLink.error.value),

    start,
    verify,
    resend,
    reset,
  };
}
