<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useQueryClient } from '@tanstack/vue-query'
import { i18n } from '@app/i18n'
import { useUpdateCurrentUserUsersMePatch, getCurrentUserUsersMeGetQueryKey } from '@/gen/hooks'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'

// Use global scope for t()
const { t } = useI18n({ useScope: 'global' })
const queryClient = useQueryClient()

// Access global locale directly (this is the source of truth)
const locale = i18n.global.locale

// Mutation to persist language preference to backend
const { mutate: updateUser } = useUpdateCurrentUserUsersMePatch()

const languages = [
  { id: 'en' as const, label: 'English', flag: '\u{1F1FA}\u{1F1F8}' },
  { id: 'ru' as const, label: '\u0420\u0443\u0441\u0441\u043a\u0438\u0439', flag: '\u{1F1F7}\u{1F1FA}' },
]

const setLocale = (lang: 'en' | 'ru') => {
  // Change global locale directly
  locale.value = lang
  // Persist to backend (fire and forget)
  updateUser(
    { data: { language_code: lang } },
    { onSuccess: () => queryClient.invalidateQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() }) }
  )
}
</script>

<template>
  <DemoSection icon="&#127760;" :title="t('demo.i18n.title')">
    <div class="space-y-4">
      <div class="flex gap-2">
        <Button
          v-for="lang in languages"
          :key="lang.id"
          :variant="locale === lang.id ? 'default' : 'outline'"
          class="flex-1"
          @click="setLocale(lang.id)"
        >
          <span class="mr-2">{{ lang.flag }}</span>
          {{ lang.label }}
        </Button>
      </div>

      <div class="bg-muted rounded-lg p-4 text-sm">
        <p class="font-medium mb-2">{{ t('demo.i18n.preview') }}:</p>
        <p>{{ t('demo.i18n.sampleText') }}</p>
      </div>

      <p class="text-xs text-muted-foreground">
        {{ t('demo.i18n.current') }}: {{ locale }}
      </p>
    </div>
  </DemoSection>
</template>
