<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useScheduleNotificationDemoNotifyPost } from '@/gen/hooks'
import ProfileSection from './ProfileSection.vue'
import { Button } from '@/components/ui/button'
import { Check } from 'lucide-vue-next'

const { t } = useI18n()

const { mutate: notify, isPending } = useScheduleNotificationDemoNotifyPost()

const lastSent = ref<number | null>(null)
const status = ref<'idle' | 'sent'>('idle')

const handleNotify = (delaySeconds: number) => {
  notify(
    { data: { delay_seconds: delaySeconds } },
    {
      onSuccess: () => {
        lastSent.value = delaySeconds
        status.value = 'sent'
        setTimeout(() => { status.value = 'idle' }, 3000)
      },
    }
  )
}

const delays = [1, 5, 10]
</script>

<template>
  <ProfileSection icon="&#128276;" :title="t('profile.notification.title')">
    <div class="space-y-4">
      <p class="text-sm text-muted-foreground">
        {{ t('profile.notification.description') }}
      </p>

      <!-- Delay buttons -->
      <div class="flex gap-2">
        <Button
          v-for="delay in delays"
          :key="delay"
          :disabled="isPending"
          variant="outline"
          class="flex-1"
          @click="handleNotify(delay)"
        >
          {{ delay }}{{ t('profile.notification.seconds') }}
        </Button>
      </div>

      <!-- Status -->
      <div
        v-if="status === 'sent'"
        class="flex items-center gap-2 text-sm text-green-500 bg-green-500/10 rounded-lg p-3"
      >
        <Check class="w-4 h-4" />
        {{ t('profile.notification.sent', { seconds: lastSent }) }}
      </div>

      <p class="text-xs text-muted-foreground">
        {{ t('profile.notification.note') }}
      </p>
    </div>
  </ProfileSection>
</template>
