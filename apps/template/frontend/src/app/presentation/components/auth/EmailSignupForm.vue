<script setup lang="ts">
import { ref, computed } from 'vue';
import { useEmailSignup } from '@app/composables/useEmailAuth';
import { useI18n } from 'vue-i18n';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2 } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'success'): void;
  (e: 'switchToLogin'): void;
}>();

const { t } = useI18n();
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

// Form state
const email = ref('');
const code = ref('');
const password = ref('');
const username = ref('');

const isLoading = computed(() => isStarting.value || isCompleting.value);

const errorMessage = computed(() => {
  const err = (startError.value || completeError.value) as { response?: { data?: { detail?: string } } } | null;
  if (!err) return null;
  return err?.response?.data?.detail || t('auth.email.signup.error');
});

const handleStartSignup = async () => {
  try {
    await start(email.value);
  } catch {
    // Error handled by composable
  }
};

const handleVerify = async () => {
  try {
    await verify(code.value, password.value, username.value);
    emit('success');
  } catch {
    // Error handled by composable
  }
};

const handleResend = async () => {
  try {
    await resend();
  } catch {
    // Error handled by composable
  }
};

const handleBack = () => {
  reset();
};
</script>

<template>
  <!-- Step 1: Email -->
  <form v-if="step === 'email'" class="space-y-4" @submit.prevent="handleStartSignup">
    <div class="space-y-2">
      <Label for="signup-email">{{ t('auth.email.email') }}</Label>
      <Input
        id="signup-email"
        v-model="email"
        type="email"
        :placeholder="t('auth.email.emailPlaceholder')"
        required
        autocomplete="email"
      />
    </div>

    <Alert v-if="errorMessage" variant="destructive">
      <AlertDescription>{{ errorMessage }}</AlertDescription>
    </Alert>

    <Button type="submit" class="w-full" :disabled="isLoading">
      <Loader2 v-if="isStarting" class="w-4 h-4 mr-2 animate-spin" />
      {{ isStarting ? t('common.loading') : t('auth.email.signup.continue') }}
    </Button>

    <p class="text-center text-sm text-muted-foreground">
      {{ t('auth.email.signup.haveAccount') }}
      <button
        type="button"
        class="text-primary hover:underline"
        @click="emit('switchToLogin')"
      >
        {{ t('auth.email.signup.loginLink') }}
      </button>
    </p>
  </form>

  <!-- Step 2: Verify + Complete -->
  <form v-else-if="step === 'verify'" class="space-y-4" @submit.prevent="handleVerify">
    <p class="text-sm text-muted-foreground">
      {{ t('auth.email.signup.codeSent', { email: savedEmail }) }}
    </p>

    <div class="space-y-2">
      <Label for="signup-code">{{ t('auth.email.code') }}</Label>
      <Input
        id="signup-code"
        v-model="code"
        type="text"
        inputmode="numeric"
        pattern="[0-9]{6}"
        maxlength="6"
        :placeholder="t('auth.email.codePlaceholder')"
        required
        autocomplete="one-time-code"
        class="text-center text-2xl tracking-widest font-mono"
      />
    </div>

    <div class="space-y-2">
      <Label for="signup-username">{{ t('auth.email.username') }}</Label>
      <Input
        id="signup-username"
        v-model="username"
        type="text"
        :placeholder="t('auth.email.usernamePlaceholder')"
        required
        minlength="3"
        maxlength="32"
        pattern="[a-zA-Z0-9_]+"
        autocomplete="username"
      />
      <p class="text-xs text-muted-foreground">
        {{ t('auth.email.usernameRequirements') }}
      </p>
    </div>

    <div class="space-y-2">
      <Label for="signup-password">{{ t('auth.email.password') }}</Label>
      <Input
        id="signup-password"
        v-model="password"
        type="password"
        :placeholder="t('auth.email.newPasswordPlaceholder')"
        required
        minlength="8"
        autocomplete="new-password"
      />
      <p class="text-xs text-muted-foreground">
        {{ t('auth.email.passwordRequirements') }}
      </p>
    </div>

    <Alert v-if="errorMessage" variant="destructive">
      <AlertDescription>{{ errorMessage }}</AlertDescription>
    </Alert>

    <Button type="submit" class="w-full" :disabled="isLoading">
      <Loader2 v-if="isCompleting" class="w-4 h-4 mr-2 animate-spin" />
      {{ isCompleting ? t('common.loading') : t('auth.email.signup.createAccount') }}
    </Button>

    <div class="flex justify-between text-sm">
      <button
        type="button"
        class="text-muted-foreground hover:underline"
        @click="handleBack"
      >
        {{ t('common.back') }}
      </button>
      <button
        type="button"
        class="text-primary hover:underline"
        :disabled="isResending"
        @click="handleResend"
      >
        {{ isResending ? t('common.loading') : t('auth.email.resendCode') }}
      </button>
    </div>
  </form>
</template>
