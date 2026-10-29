<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { Check, Copy } from '@lucide/vue';
import { Button } from '@/components/ui/button';
import BrandIcon from './BrandIcon.vue';
import { useCopyText } from './useCopyText';

/**
 * A ready-made Claude Code prompt with a copy button: the "or let the agent do
 * it" path next to a list of manual steps.
 */
defineProps<{ prompt: string }>();

const { t } = useI18n();
const { copied, copy } = useCopyText(() => t('homePage.quickStart.prompt.copyFailed'));
</script>

<template>
  <div class="space-y-2 rounded-lg border border-primary/20 bg-primary/[0.03] p-3">
    <div class="flex items-center justify-between gap-2">
      <p class="flex min-w-0 items-center gap-1.5 text-sm font-medium text-foreground">
        <BrandIcon name="claude" class="h-3.5 w-3.5 text-[#D97757]" />
        {{ t('homePage.quickStart.prompt.label') }}
      </p>
      <Button variant="ghost" size="sm" class="h-8 shrink-0 px-2 text-xs" @click="copy(prompt)">
        <Check v-if="copied" class="h-3.5 w-3.5 text-primary" />
        <Copy v-else class="h-3.5 w-3.5" />
        {{ copied ? t('homePage.quickStart.prompt.copied') : t('homePage.quickStart.prompt.copy') }}
      </Button>
    </div>
    <p class="text-sm leading-relaxed text-muted-foreground">{{ prompt }}</p>
  </div>
</template>
