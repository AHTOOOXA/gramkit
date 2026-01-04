<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { useEmailLink } from '@app/composables/useEmailAuth'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, ArrowLeft } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'success'): void
}>()

const { t } = useI18n()
const emailLink = useEmailLink()

const email = ref('')
const code = ref('')
const password = ref('')

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value),
})

const canSubmitEmail = computed(() => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email.value)
})

const canSubmitVerify = computed(() => {
  return code.value.length === 6 && password.value.length >= 8
})

const displayError = computed(() => {
  if (emailLink.startError.value) {
    const err = emailLink.startError.value as { response?: { data?: { detail?: string } } }
    return err.response?.data?.detail || t('profile.addEmail.error')
  }
  if (emailLink.completeError.value) {
    const err = emailLink.completeError.value as { response?: { data?: { detail?: string } } }
    return err.response?.data?.detail || t('profile.addEmail.error')
  }
  return null
})

watch(() => emailLink.step.value, (step) => {
  if (step === 'complete') {
    toast.success(t('profile.addEmail.success'))
    emit('success')
    handleClose()
  }
})

const handleSendCode = async () => {
  if (!canSubmitEmail.value) return
  try {
    await emailLink.start(email.value)
  } catch {
    // Error handled by composable
  }
}

const handleVerify = async () => {
  if (!canSubmitVerify.value) return
  try {
    await emailLink.verify(code.value, password.value)
  } catch {
    // Error handled by composable
  }
}

const handleResend = async () => {
  try {
    await emailLink.resend()
    toast.success(t('auth.email.signup.codeSent', { email: emailLink.email.value }))
  } catch {
    // Error handled by composable
  }
}

const handleBack = () => {
  emailLink.reset()
  code.value = ''
  password.value = ''
}

const handleClose = () => {
  emailLink.reset()
  email.value = ''
  code.value = ''
  password.value = ''
  isOpen.value = false
}
</script>

<template>
  <Dialog v-model:open="isOpen">
    <DialogContent class="sm:max-w-md" @close="handleClose">
      <DialogHeader>
        <DialogTitle>{{ t('profile.addEmail.title') }}</DialogTitle>
        <DialogDescription>
          {{ emailLink.step.value === 'email' ? t('profile.addEmail.step1') : t('profile.addEmail.step2') }}
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4 py-4">
        <Alert v-if="displayError" variant="destructive" class="mb-4">
          <AlertDescription>{{ displayError }}</AlertDescription>
        </Alert>

        <div v-if="emailLink.step.value === 'email'" class="space-y-4">
          <div class="space-y-2">
            <Label for="email">{{ t('auth.email.email') }}</Label>
            <Input
              id="email"
              v-model="email"
              type="email"
              :placeholder="t('auth.email.emailPlaceholder')"
              :disabled="emailLink.isStarting.value"
              @keyup.enter="handleSendCode"
            />
          </div>

          <Button
            class="w-full"
            :disabled="!canSubmitEmail || emailLink.isStarting.value"
            @click="handleSendCode"
          >
            <Loader2 v-if="emailLink.isStarting.value" class="w-4 h-4 mr-2 animate-spin" />
            <Mail v-else class="w-4 h-4 mr-2" />
            {{ t('auth.email.link.sendCode') }}
          </Button>

          <Button variant="outline" class="w-full" @click="handleClose">
            {{ t('common.cancel') }}
          </Button>
        </div>

        <div v-else class="space-y-4">
          <p class="text-sm text-muted-foreground text-center">
            {{ t('profile.addEmail.codeSent', { email: emailLink.email.value }) }}
          </p>

          <div class="space-y-2">
            <Label for="code">{{ t('auth.email.code') }}</Label>
            <Input
              id="code"
              v-model="code"
              :placeholder="t('auth.email.codePlaceholder')"
              maxlength="6"
              class="text-center text-2xl tracking-widest font-mono"
              :disabled="emailLink.isCompleting.value"
            />
          </div>

          <div class="space-y-2">
            <Label for="password">{{ t('auth.email.password') }}</Label>
            <Input
              id="password"
              v-model="password"
              type="password"
              :placeholder="t('auth.email.newPasswordPlaceholder')"
              :disabled="emailLink.isCompleting.value"
              @keyup.enter="handleVerify"
            />
            <p class="text-xs text-muted-foreground">
              {{ t('auth.email.passwordRequirements') }}
            </p>
          </div>

          <Button
            class="w-full"
            :disabled="!canSubmitVerify || emailLink.isCompleting.value"
            @click="handleVerify"
          >
            <Loader2 v-if="emailLink.isCompleting.value" class="w-4 h-4 mr-2 animate-spin" />
            {{ t('auth.email.link.linkEmail') }}
          </Button>

          <div class="flex gap-2">
            <Button
              variant="outline"
              class="flex-1"
              :disabled="emailLink.isCompleting.value"
              @click="handleBack"
            >
              <ArrowLeft class="w-4 h-4 mr-2" />
              {{ t('common.back') }}
            </Button>
            <Button
              variant="link"
              class="flex-1"
              :disabled="emailLink.isResending.value"
              @click="handleResend"
            >
              {{ t('auth.email.resendCode') }}
            </Button>
          </div>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
