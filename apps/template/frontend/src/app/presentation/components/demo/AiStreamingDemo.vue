<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { apiFetch } from '@/config/kubb-config'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'

const { t } = useI18n()

const text = ref('')
const isStreaming = ref(false)

async function startStream() {
  text.value = ''
  isStreaming.value = true

  try {
    const res = await apiFetch('/demo/stream')
    const reader = res.body?.getReader()
    const decoder = new TextDecoder()

    while (reader) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ') && !line.includes('[DONE]')) {
          text.value += line.slice(6)
        }
      }
    }
  } catch (err) {
    console.error(err)
  } finally {
    isStreaming.value = false
  }
}
</script>

<template>
  <DemoSection icon="🤖" :title="t('demo.aiStreaming.title')">
    <div class="space-y-4">
      <Button :disabled="isStreaming" @click="startStream">
        {{ isStreaming ? 'Streaming...' : t('demo.aiStreaming.startButton') }}
      </Button>
      <div class="bg-muted/50 rounded-lg p-4 min-h-[120px] font-mono text-sm whitespace-pre-wrap">
        {{ text }}
        <span v-if="isStreaming" class="animate-pulse">▊</span>
      </div>
      <p class="text-xs text-muted-foreground">
        {{ t('demo.aiStreaming.description') }}
      </p>
    </div>
  </DemoSection>
</template>
