<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { Check, Copy } from '@lucide/vue';
import { useCopyText } from './useCopyText';

/**
 * Shell commands with one copy button for all of them. Lines starting with
 * `#` render as comments. Always dark, like a terminal.
 */
const props = defineProps<{ commands: string[] }>();

const { t } = useI18n();
const { copied, copy } = useCopyText(() => t('homePage.quickStart.prompt.copyFailed'));
</script>

<template>
  <div class="relative overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-100">
    <pre class="overflow-x-auto py-3 pr-12 pl-4 font-mono text-xs leading-6"><template
      v-for="line in props.commands"
      :key="line"
    ><div v-if="line.startsWith('#')" class="text-zinc-500">{{ line }}</div><div v-else><span class="text-sky-400 select-none">$ </span>{{ line }}</div></template></pre>
    <!-- Opaque strip: long lines scroll under the button instead of peeking past it -->
    <div class="absolute inset-y-0 right-0 bg-zinc-950 pt-1.5 pr-1.5 shadow-[-12px_0_12px_-2px_var(--color-zinc-950)]">
      <button
        type="button"
        class="inline-flex h-9 w-9 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100 focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:outline-none"
        :aria-label="copied ? t('homePage.quickStart.prompt.copied') : t('homePage.quickStart.copy')"
        @click="copy(props.commands.join('\n'))"
      >
        <Check v-if="copied" class="h-4 w-4 text-sky-400" />
        <Copy v-else class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>
