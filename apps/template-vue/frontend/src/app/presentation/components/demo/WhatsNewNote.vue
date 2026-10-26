<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Sparkles } from '@lucide/vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useWhatsNew } from '@app/composables/useSeenFeatures'

/**
 * Versioned "what's new" note, gated on `user.seen_features` (key `whatsnew.demo`).
 * Shows to signed-in users until they dismiss this version; never to the shared GUEST user.
 * To log impressions, pair it with an analytics event (see the seen-features rule:
 * gate on seen_features, capture the impression separately).
 */

// Bump to show it again to everyone who dismissed an older version.
const WHATS_NEW_VERSION = 1

const { t } = useI18n()
const { show, dismiss } = useWhatsNew('whatsnew.demo', WHATS_NEW_VERSION)
</script>

<template>
  <Transition
    enter-active-class="motion-opacity-in-[0%] motion-translate-y-in-[8px] motion-duration-[0.3s] motion-ease-spring-smooth"
    leave-active-class="motion-opacity-out-[0%] motion-duration-[0.2s]"
  >
    <!-- role="status": a non-urgent note shouldn't interrupt screen readers like role="alert" does -->
    <Alert v-if="show" role="status" class="border-primary/30 bg-primary/[0.03]">
      <Sparkles class="h-4 w-4" />
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div class="space-y-1">
          <p class="font-medium leading-none tracking-tight">{{ t('demo.whatsNew.title') }}</p>
          <AlertDescription class="text-muted-foreground">{{ t('demo.whatsNew.body') }}</AlertDescription>
        </div>
        <Button variant="ghost" size="sm" class="self-end sm:self-auto shrink-0" @click="dismiss">
          {{ t('demo.whatsNew.dismiss') }}
        </Button>
      </div>
    </Alert>
  </Transition>
</template>
