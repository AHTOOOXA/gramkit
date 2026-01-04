<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { mode } from '@app/store/theme'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Sun, Moon, Monitor } from 'lucide-vue-next'

const { t } = useI18n()

const themes = [
  { id: 'light', icon: Sun, labelKey: 'demo.theme.light' },
  { id: 'dark', icon: Moon, labelKey: 'demo.theme.dark' },
  { id: 'auto', icon: Monitor, labelKey: 'demo.theme.system' },
] as const

const setTheme = (theme: 'light' | 'dark' | 'auto') => {
  mode.value = theme
}
</script>

<template>
  <DemoSection icon="&#127912;" :title="t('demo.theme.title')">
    <div class="space-y-4">
      <div class="flex flex-col gap-2">
        <Button
          v-for="theme in themes"
          :key="theme.id"
          :variant="mode === theme.id ? 'default' : 'outline'"
          class="w-full justify-start"
          @click="setTheme(theme.id)"
        >
          <component :is="theme.icon" class="w-4 h-4 mr-2" />
          {{ t(theme.labelKey) }}
        </Button>
      </div>

      <p class="text-xs text-muted-foreground">
        {{ t('demo.theme.current') }}: {{ mode }}
      </p>
    </div>
  </DemoSection>
</template>
