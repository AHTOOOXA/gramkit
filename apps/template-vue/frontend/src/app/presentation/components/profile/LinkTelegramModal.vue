<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import { useTelegramWebAuth } from '@app/composables/useTelegramWebAuth'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Send, ExternalLink } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'success'): void
}>()

const { t } = useI18n()
const telegramAuth = useTelegramWebAuth()

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value),
})

watch(() => telegramAuth.isPolling.value, (polling, wasPolling) => {
  if (wasPolling && !polling && !telegramAuth.error.value) {
    toast.success(t('profile.linkTelegram.success'))
    emit('success')
    handleClose()
  }
})

const handleStart = async () => {
  try {
    await telegramAuth.start()
  } catch {
    // Error handled in composable
  }
}

const handleClose = () => {
  telegramAuth.reset()
  isOpen.value = false
}
</script>

<template>
  <Dialog v-model:open="isOpen">
    <DialogContent class="sm:max-w-md" @close="handleClose">
      <DialogHeader>
        <DialogTitle>{{ t('profile.linkTelegram.title') }}</DialogTitle>
        <DialogDescription>
          {{ t('profile.linkTelegram.description') }}
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4 py-4">
        <Alert v-if="telegramAuth.error.value" variant="destructive" class="mb-4">
          <AlertDescription>{{ telegramAuth.error.value }}</AlertDescription>
        </Alert>

        <div v-if="telegramAuth.isPolling.value" class="space-y-4">
          <div class="flex flex-col items-center space-y-4">
            <Loader2 class="h-8 w-8 animate-spin text-primary" />
            <p class="text-center text-sm">{{ t('profile.linkTelegram.waiting') }}</p>
            <p class="text-center text-xs text-muted-foreground">
              {{ t('login.telegram.hint') }}
            </p>
          </div>

          <div class="flex gap-2">
            <Button variant="outline" class="flex-1" @click="handleClose">
              {{ t('common.cancel') }}
            </Button>
            <Button variant="outline" class="flex-1" @click="telegramAuth.openTelegram">
              <ExternalLink class="w-4 h-4 mr-2" />
              {{ t('login.telegram.reopen') }}
            </Button>
          </div>
        </div>

        <div v-else class="space-y-4">
          <p class="text-center text-sm text-muted-foreground">
            {{ t('profile.linkTelegram.scanQr') }}
          </p>

          <Button
            class="w-full"
            :disabled="telegramAuth.isStarting.value"
            @click="handleStart"
          >
            <Loader2 v-if="telegramAuth.isStarting.value" class="w-4 h-4 mr-2 animate-spin" />
            <Send v-else class="w-4 h-4 mr-2" />
            {{ t('profile.linkTelegram.openTelegram') }}
          </Button>

          <Button variant="outline" class="w-full" @click="handleClose">
            {{ t('common.cancel') }}
          </Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
