<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { Loader2, Send } from 'lucide-vue-next';
import { useEmailLogin, useEmailSignup } from '@app/composables/useEmailAuth';
import { useTelegramDeeplinkLogin } from '@app/composables/useTelegramDeeplinkLogin';
import { usePasswordReset } from '@app/composables/usePasswordReset';
import { useAuth } from '@app/composables/useAuth';
import { useAuthRedirect } from '@app/composables/useAuthRedirect';
import { useCheckEmailAuthEmailCheckPost } from '@/gen/hooks';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

type EmailFlow = 'email' | 'checking' | 'login' | 'signup_code';
type ResetFlow = 'email' | 'verify' | 'complete';

const router = useRouter();
const { t } = useI18n();
const { reinitialize } = useAuth();
const { isGuest, isLoading: isAuthLoading } = useAuthRedirect();

// Telegram deeplink flow
const telegramLogin = useTelegramDeeplinkLogin();

// Email auth
const emailLogin = useEmailLogin();
const emailSignup = useEmailSignup();
const passwordReset = usePasswordReset();
const checkEmail = useCheckEmailAuthEmailCheckPost();

// Main flow state
const flow = ref<'email' | 'telegram'>('email');

// Email flow
const emailFlow = ref<EmailFlow>('email');
const email = ref('');
const loginPassword = ref('');
const signupCode = ref('');
const signupUsername = ref('');
const signupPassword = ref('');
const emailError = ref<string | null>(null);

// Password reset flow
const showResetForm = ref(false);
const resetFlow = ref<ResetFlow>('email');
const resetEmail = ref('');
const resetCode = ref('');
const resetPassword = ref('');

// Watch for successful Telegram deeplink login
watch(() => telegramLogin.isPolling.value, (isPolling, wasPolling) => {
  if (wasPolling && !isPolling && !telegramLogin.error.value && telegramLogin.botUrl.value) {
    router.push('/');
  }
});

const handleOpenTelegram = async () => {
  try {
    await telegramLogin.start();
  } catch {
    // Error handled in hook
  }
};

// Email flow handlers
const handleEmailContinue = async () => {
  emailError.value = null;
  emailFlow.value = 'checking';

  try {
    const result = await checkEmail.mutateAsync({ data: { email: email.value } });

    if (result.exists) {
      // Email exists - show login form
      emailFlow.value = 'login';
    } else {
      // Email doesn't exist - start signup flow
      await emailSignup.start(email.value);
      emailFlow.value = 'signup_code';
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    emailError.value = err?.response?.data?.detail || t('auth.email.error');
    emailFlow.value = 'email';
  }
};

const handleEmailLogin = async () => {
  emailError.value = null;

  try {
    await emailLogin.submit(email.value, loginPassword.value);
    reinitialize();
    router.push('/');
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    emailError.value = err?.response?.data?.detail || t('auth.email.login.error');
  }
};

const handleCompleteSignup = async () => {
  emailError.value = null;

  try {
    await emailSignup.verify(signupCode.value, signupPassword.value, signupUsername.value);
    reinitialize();
    router.push('/');
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } };
    emailError.value = err?.response?.data?.detail || t('auth.email.signup.error');
  }
};

const handleBackToEmail = () => {
  emailFlow.value = 'email';
  loginPassword.value = '';
  signupCode.value = '';
  signupUsername.value = '';
  signupPassword.value = '';
  emailError.value = null;
  emailSignup.reset();
};

// Password reset handlers
const handleStartReset = async () => {
  try {
    await passwordReset.start(resetEmail.value);
    resetFlow.value = 'verify';
  } catch {
    // Error handled by hook
  }
};

const handleCompleteReset = async () => {
  try {
    await passwordReset.complete(resetCode.value, resetPassword.value);
    resetFlow.value = 'complete';
  } catch {
    // Error handled by hook
  }
};

const handleBackToLogin = () => {
  showResetForm.value = false;
  resetFlow.value = 'email';
  resetEmail.value = '';
  resetCode.value = '';
  resetPassword.value = '';
  flow.value = 'email';
  emailFlow.value = 'email';
};

const getPasswordResetError = () => {
  const error = passwordReset.startError.value ?? passwordReset.completeError.value;
  if (error) {
    const err = error as { response?: { data?: { detail?: string } } };
    return err?.response?.data?.detail ?? t('auth.email.reset.error');
  }
  return null;
};

const resetError = computed(() => getPasswordResetError());
</script>

<template>
  <!-- Loading while checking auth state -->
  <div v-if="isAuthLoading || !isGuest" class="flex min-h-[60vh] items-center justify-center">
    <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" />
  </div>

  <!-- Password reset view (when in verify or complete state) -->
  <div v-else-if="flow === 'email' && (resetFlow === 'verify' || resetFlow === 'complete')" class="flex min-h-[60vh] items-center justify-center">
    <Card class="w-full max-w-md">
      <CardHeader>
        <CardTitle>{{ t('auth.email.reset.title') }}</CardTitle>
        <CardDescription>
          <span v-if="resetFlow === 'verify'">{{ t('auth.email.reset.codeSent', { email: passwordReset.email.value }) }}</span>
          <span v-else>{{ t('auth.email.reset.success') }}</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form v-if="resetFlow === 'verify'" class="space-y-4" @submit.prevent="handleCompleteReset">
          <div class="space-y-2">
            <Label for="reset-code">{{ t('auth.email.code') }}</Label>
            <Input
              id="reset-code"
              v-model="resetCode"
              type="text"
              inputmode="numeric"
              pattern="[0-9]{6}"
              maxlength="6"
              :placeholder="t('auth.email.codePlaceholder')"
              required
              autocomplete="one-time-code"
              :disabled="passwordReset.isCompleting.value"
              autofocus
              @input="passwordReset.clearCompleteError()"
            />
          </div>

          <div class="space-y-2">
            <Label for="reset-password">{{ t('auth.email.reset.newPassword') }}</Label>
            <Input
              id="reset-password"
              v-model="resetPassword"
              type="password"
              :placeholder="t('auth.email.newPasswordPlaceholder')"
              required
              minlength="8"
              autocomplete="new-password"
              :disabled="passwordReset.isCompleting.value"
              @input="passwordReset.clearCompleteError()"
            />
            <p class="text-xs text-muted-foreground">
              {{ t('auth.email.passwordRequirements') }}
            </p>
          </div>

          <Alert v-if="resetError" variant="destructive">
            <AlertDescription role="alert">{{ resetError }}</AlertDescription>
          </Alert>

          <Button
            type="submit"
            class="w-full"
            :disabled="passwordReset.isCompleting.value || !resetPassword"
          >
            <Loader2 v-if="passwordReset.isCompleting.value" class="mr-2 h-4 w-4 animate-spin" />
            {{ passwordReset.isCompleting.value ? t('common.loading') : t('auth.email.reset.resetPassword') }}
          </Button>

          <button
            type="button"
            class="text-sm text-muted-foreground hover:underline"
            @click="resetFlow = 'email'"
          >
            {{ t('common.back') }}
          </button>
        </form>

        <div v-else-if="resetFlow === 'complete'" class="space-y-4 text-center">
          <Button @click="handleBackToLogin">
            {{ t('auth.email.reset.backToLogin') }}
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>

  <!-- Main login view -->
  <div v-else class="flex min-h-[60vh] items-center justify-center">
    <Card class="w-full max-w-md">
      <CardHeader>
        <CardTitle>{{ t('login.title') }}</CardTitle>
        <CardDescription v-if="!(flow === 'email' && emailFlow === 'email')">
          <span v-if="flow === 'email' && emailFlow === 'login'">{{ t('auth.email.login.description') }}</span>
          <span v-else-if="flow === 'email' && emailFlow === 'signup_code'">{{ t('auth.email.signup.description') }}</span>
          <span v-else-if="flow === 'telegram' && telegramLogin.isPolling.value">{{ t('login.telegram.waiting') }}</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div class="space-y-4">
          <!-- Email-first flow -->
          <div v-if="flow === 'email'">
            <!-- Step 1: Email input -->
            <form v-if="emailFlow === 'email'" class="space-y-4" @submit.prevent="handleEmailContinue">
              <div class="space-y-2">
                <Label for="email">{{ t('auth.email.email') }}</Label>
                <Input
                  id="email"
                  v-model="email"
                  type="email"
                  :placeholder="t('auth.email.emailPlaceholder')"
                  required
                  autocomplete="email"
                  :disabled="checkEmail.isPending.value"
                  autofocus
                  @input="emailError = null"
                />
              </div>

              <Alert v-if="emailError" variant="destructive">
                <AlertDescription role="alert">{{ emailError }}</AlertDescription>
              </Alert>

              <Button type="submit" variant="secondary" class="w-full" :disabled="checkEmail.isPending.value">
                <Loader2 v-if="checkEmail.isPending.value" class="mr-2 h-4 w-4 animate-spin" />
                {{ checkEmail.isPending.value ? t('common.loading') : t('auth.email.continue') }}
              </Button>

              <!-- Divider -->
              <div class="relative">
                <div class="absolute inset-0 flex items-center">
                  <span class="w-full border-t" />
                </div>
                <div class="relative flex justify-center text-xs uppercase">
                  <span class="bg-background px-2 text-muted-foreground">
                    {{ t('login.or') }}
                  </span>
                </div>
              </div>

              <!-- Telegram button -->
              <Button
                type="button"
                class="w-full flex items-center gap-2"
                @click="flow = 'telegram'"
              >
                <Send class="h-4 w-4" />
                {{ t('login.telegram.continueWith') }}
              </Button>
            </form>

            <!-- Step 2a: Login form -->
            <form v-else-if="emailFlow === 'login' && !showResetForm" class="space-y-4" @submit.prevent="handleEmailLogin">
              <div class="space-y-2">
                <Label for="login-email">{{ t('auth.email.email') }}</Label>
                <Input
                  id="login-email"
                  v-model="email"
                  type="email"
                  disabled
                />
              </div>

              <div class="space-y-2">
                <Label for="login-password">{{ t('auth.email.password') }}</Label>
                <Input
                  id="login-password"
                  v-model="loginPassword"
                  type="password"
                  :placeholder="t('auth.email.passwordPlaceholder')"
                  required
                  autocomplete="current-password"
                  :disabled="emailLogin.isLoading.value"
                  autofocus
                  @input="emailError = null"
                />
              </div>

              <Alert v-if="emailError" variant="destructive">
                <AlertDescription role="alert">{{ emailError }}</AlertDescription>
              </Alert>

              <Button type="submit" class="w-full" :disabled="emailLogin.isLoading.value">
                <Loader2 v-if="emailLogin.isLoading.value" class="mr-2 h-4 w-4 animate-spin" />
                {{ emailLogin.isLoading.value ? t('common.loading') : t('auth.email.login.submit') }}
              </Button>

              <button
                type="button"
                class="text-sm text-primary hover:underline"
                @click="resetEmail = email; showResetForm = true"
              >
                {{ t('auth.email.reset.forgotPassword') }}
              </button>

              <Button
                variant="ghost"
                class="w-full"
                @click="handleBackToEmail"
              >
                {{ t('common.back') }}
              </Button>
            </form>

            <!-- Step 2b: Password reset email form -->
            <form v-else-if="emailFlow === 'login' && showResetForm" class="space-y-4" @submit.prevent="handleStartReset">
              <p class="text-sm text-muted-foreground">
                {{ t('auth.email.reset.emailDescription') }}
              </p>

              <div class="space-y-2">
                <Label for="reset-email">{{ t('auth.email.email') }}</Label>
                <Input
                  id="reset-email"
                  v-model="resetEmail"
                  type="email"
                  :placeholder="t('auth.email.emailPlaceholder')"
                  required
                  autocomplete="email"
                  :disabled="passwordReset.isStarting.value"
                  autofocus
                  @input="passwordReset.clearStartError()"
                />
              </div>

              <Alert v-if="resetError" variant="destructive">
                <AlertDescription role="alert">{{ resetError }}</AlertDescription>
              </Alert>

              <Button type="submit" class="w-full" :disabled="passwordReset.isStarting.value">
                <Loader2 v-if="passwordReset.isStarting.value" class="mr-2 h-4 w-4 animate-spin" />
                {{ passwordReset.isStarting.value ? t('common.loading') : t('auth.email.reset.sendCode') }}
              </Button>

              <Button
                variant="ghost"
                class="w-full"
                @click="showResetForm = false; resetEmail = ''"
              >
                {{ t('auth.email.reset.backToLogin') }}
              </Button>
            </form>

            <!-- Step 2c: Signup form -->
            <form v-else-if="emailFlow === 'signup_code'" class="space-y-4" @submit.prevent="handleCompleteSignup">
              <p class="text-sm text-muted-foreground">
                {{ t('auth.email.signup.codeSent', { email: emailSignup.email.value }) }}
              </p>

              <div class="space-y-2">
                <Label for="signup-code">{{ t('auth.email.code') }}</Label>
                <Input
                  id="signup-code"
                  v-model="signupCode"
                  type="text"
                  inputmode="numeric"
                  pattern="[0-9]{6}"
                  maxlength="6"
                  :placeholder="t('auth.email.codePlaceholder')"
                  required
                  autocomplete="one-time-code"
                  :disabled="emailSignup.isCompleting.value"
                  autofocus
                  @input="emailError = null"
                />
              </div>

              <div class="space-y-2">
                <Label for="signup-username">{{ t('auth.email.username') }}</Label>
                <Input
                  id="signup-username"
                  v-model="signupUsername"
                  type="text"
                  :placeholder="t('auth.email.usernamePlaceholder')"
                  required
                  minlength="3"
                  maxlength="32"
                  pattern="[a-zA-Z0-9_]+"
                  autocomplete="username"
                  :disabled="emailSignup.isCompleting.value"
                  @input="emailError = null"
                />
                <p class="text-xs text-muted-foreground">
                  {{ t('auth.email.usernameRequirements') }}
                </p>
              </div>

              <div class="space-y-2">
                <Label for="signup-password">{{ t('auth.email.password') }}</Label>
                <Input
                  id="signup-password"
                  v-model="signupPassword"
                  type="password"
                  :placeholder="t('auth.email.newPasswordPlaceholder')"
                  required
                  minlength="8"
                  autocomplete="new-password"
                  :disabled="emailSignup.isCompleting.value"
                  @input="emailError = null"
                />
                <p class="text-xs text-muted-foreground">
                  {{ t('auth.email.passwordRequirements') }}
                </p>
              </div>

              <Alert v-if="emailError" variant="destructive">
                <AlertDescription role="alert">{{ emailError }}</AlertDescription>
              </Alert>

              <Button
                type="submit"
                class="w-full"
                :disabled="emailSignup.isCompleting.value || !signupPassword"
              >
                <Loader2 v-if="emailSignup.isCompleting.value" class="mr-2 h-4 w-4 animate-spin" />
                {{ emailSignup.isCompleting.value ? t('common.loading') : t('auth.email.signup.createAccount') }}
              </Button>

              <div class="flex justify-between text-sm">
                <button
                  type="button"
                  class="text-muted-foreground hover:underline"
                  @click="handleBackToEmail"
                >
                  {{ t('common.back') }}
                </button>
                <button
                  type="button"
                  class="text-primary hover:underline"
                  :disabled="emailSignup.isResending.value"
                  @click="emailSignup.resend()"
                >
                  {{ emailSignup.isResending.value ? t('common.loading') : t('auth.email.resendCode') }}
                </button>
              </div>
            </form>

            <!-- Checking state -->
            <div v-else-if="emailFlow === 'checking'" class="flex items-center justify-center py-8">
              <Loader2 class="h-8 w-8 animate-spin text-primary" />
            </div>
          </div>

          <!-- Telegram deeplink flow -->
          <div v-else-if="flow === 'telegram'">
            <Alert v-if="telegramLogin.error.value" variant="destructive">
              <AlertDescription role="alert">{{ telegramLogin.error.value }}</AlertDescription>
            </Alert>

            <div v-if="telegramLogin.isPolling.value" class="space-y-4 py-4">
              <div class="flex flex-col items-center space-y-4">
                <Loader2 class="h-8 w-8 animate-spin text-primary" />
                <p class="text-center text-sm">
                  {{ t('login.telegram.waiting') }}
                </p>
                <p class="text-center text-xs text-muted-foreground">
                  {{ t('login.telegram.hint') }}
                </p>
              </div>

              <div class="flex gap-2">
                <Button
                  variant="outline"
                  class="flex-1"
                  @click="telegramLogin.reset()"
                >
                  {{ t('common.cancel') }}
                </Button>
                <Button
                  variant="outline"
                  class="flex-1"
                  @click="telegramLogin.openTelegram()"
                >
                  {{ t('login.telegram.reopen') }}
                </Button>
              </div>
            </div>
            <div v-else>
              <Button
                class="w-full"
                :disabled="telegramLogin.isStarting.value"
                @click="handleOpenTelegram"
              >
                <Loader2 v-if="telegramLogin.isStarting.value" class="w-4 h-4 mr-2 animate-spin" />
                <Send v-else class="w-4 h-4 mr-2" />
                {{ t('login.telegram.openButton') }}
              </Button>
              <p class="text-xs text-center text-muted-foreground mt-2">
                {{ t('login.telegram.canRegister') }}
              </p>

              <Button
                variant="ghost"
                class="w-full mt-4"
                @click="flow = 'email'"
              >
                {{ t('common.back') }}
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
