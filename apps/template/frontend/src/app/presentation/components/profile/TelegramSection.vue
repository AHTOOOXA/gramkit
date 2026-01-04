<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { usePlatform } from '@core/platform'
import ProfileSection from './ProfileSection.vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Smartphone, Globe, Vibrate, X } from 'lucide-vue-next'

const { t } = useI18n()
const platform = usePlatform()

const handleVibrate = () => {
  platform.vibrate('medium')
}

const handleShowAlert = () => {
  platform.showAlert(t('profile.telegram.alertMessage'))
}
</script>

<template>
  <ProfileSection icon="&#128241;" :title="t('profile.telegram.title')">
    <div class="space-y-4">
      <!-- Platform Status -->
      <div class="flex items-center justify-between p-3 bg-muted rounded-lg">
        <div class="flex items-center gap-3">
          <component
            :is="platform.isTelegram ? Smartphone : Globe"
            class="w-5 h-5"
            :class="platform.isTelegram ? 'text-blue-500' : 'text-gray-500'"
          />
          <div>
            <p class="font-medium">{{ t('profile.telegram.platform') }}</p>
            <p class="text-sm text-muted-foreground">
              {{ platform.isTelegram ? t('profile.telegram.telegramApp') : t('profile.telegram.webBrowser') }}
            </p>
          </div>
        </div>
        <Badge :variant="platform.isTelegram ? 'default' : 'secondary'">
          {{ platform.isTelegram ? 'Telegram' : 'Web' }}
        </Badge>
      </div>

      <!-- Platform Details (Telegram only) -->
      <div v-if="platform.isTelegram" class="grid grid-cols-2 gap-2 text-sm">
        <div class="bg-muted rounded-lg p-3">
          <p class="text-muted-foreground text-xs">{{ t('profile.telegram.client') }}</p>
          <p class="font-mono capitalize">{{ platform.telegramPlatform }}</p>
        </div>
        <div class="bg-muted rounded-lg p-3">
          <p class="text-muted-foreground text-xs">{{ t('profile.telegram.colorScheme') }}</p>
          <p class="capitalize">{{ platform.colorScheme || 'system' }}</p>
        </div>
      </div>

      <!-- Telegram-only Actions -->
      <div class="space-y-2">
        <p class="text-sm font-medium text-muted-foreground">
          {{ t('profile.telegram.actionsTitle') }}
        </p>

        <!-- Vibrate button - Telegram only -->
        <Button
          v-if="platform.isTelegram"
          variant="outline"
          class="w-full justify-start gap-2"
          @click="handleVibrate"
        >
          <Vibrate class="w-4 h-4" />
          {{ t('profile.telegram.vibrate') }}
        </Button>

        <!-- Show Alert button - Telegram only -->
        <Button
          v-if="platform.isTelegram"
          variant="outline"
          class="w-full justify-start gap-2"
          @click="handleShowAlert"
        >
          <Smartphone class="w-4 h-4" />
          {{ t('profile.telegram.showAlert') }}
        </Button>

        <!-- Web user message -->
        <div v-if="platform.isWeb" class="flex items-center gap-2 p-3 bg-muted/50 rounded-lg text-sm text-muted-foreground">
          <X class="w-4 h-4 shrink-0" />
          <span>{{ t('profile.telegram.webOnlyMessage') }}</span>
        </div>
      </div>
    </div>
  </ProfileSection>
</template>
