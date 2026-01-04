<script setup lang="ts">
import { ref, computed } from 'vue';
import { useEmailLogin } from '@app/composables/useEmailAuth';
import { useI18n } from 'vue-i18n';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2 } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'success'): void;
  (e: 'switchToSignup'): void;
}>();

const { t } = useI18n();
const { isLoading, error, submit } = useEmailLogin();

const email = ref('');
const password = ref('');

const errorMessage = computed(() => {
  if (!error.value) return null;
  const err = error.value as { response?: { data?: { detail?: string } } };
  return err?.response?.data?.detail || t('auth.email.login.error');
});

const handleSubmit = async () => {
  try {
    await submit(email.value, password.value);
    emit('success');
  } catch {
    // Error handled by composable
  }
};
</script>

<template>
  <form class="space-y-4" @submit.prevent="handleSubmit">
    <div class="space-y-2">
      <Label for="email">{{ t('auth.email.email') }}</Label>
      <Input
        id="email"
        v-model="email"
        type="email"
        :placeholder="t('auth.email.emailPlaceholder')"
        required
        autocomplete="email"
      />
    </div>

    <div class="space-y-2">
      <Label for="password">{{ t('auth.email.password') }}</Label>
      <Input
        id="password"
        v-model="password"
        type="password"
        :placeholder="t('auth.email.passwordPlaceholder')"
        required
        autocomplete="current-password"
      />
    </div>

    <Alert v-if="errorMessage" variant="destructive">
      <AlertDescription>{{ errorMessage }}</AlertDescription>
    </Alert>

    <Button type="submit" class="w-full" :disabled="isLoading">
      <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
      {{ isLoading ? t('common.loading') : t('auth.email.login.submit') }}
    </Button>

    <p class="text-center text-sm text-muted-foreground">
      {{ t('auth.email.login.noAccount') }}
      <button
        type="button"
        class="text-primary hover:underline"
        @click="emit('switchToSignup')"
      >
        {{ t('auth.email.login.signupLink') }}
      </button>
    </p>
  </form>
</template>
