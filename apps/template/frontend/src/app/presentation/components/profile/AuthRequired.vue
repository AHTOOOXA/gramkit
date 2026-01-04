<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Lock } from 'lucide-vue-next'

defineProps<{
  locked: boolean
}>()

const { t } = useI18n()
</script>

<template>
  <div class="relative">
    <!-- Content (blurred when locked) -->
    <div :class="locked ? 'blur-sm pointer-events-none select-none' : ''">
      <slot />
    </div>

    <!-- Lock overlay -->
    <div
      v-if="locked"
      class="absolute inset-0 flex items-center justify-center bg-background/50 rounded-xl"
    >
      <div class="flex flex-col items-center gap-2 text-muted-foreground">
        <Lock class="w-6 h-6" />
        <span class="text-sm font-medium">{{ t('profile.authRequired') }}</span>
      </div>
    </div>
  </div>
</template>
