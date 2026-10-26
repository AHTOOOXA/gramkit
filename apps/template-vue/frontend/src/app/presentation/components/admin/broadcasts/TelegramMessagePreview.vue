<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { sanitizeTelegramHtml } from '@core/utils';

/**
 * TelegramMessagePreview — a chat-bubble preview of a broadcast: media
 * placeholder, text or caption, and the inline keyboard as button chips. Used
 * live by the composer and for the stored message on the detail page.
 *
 * SECURITY: the message HTML is admin-authored but still UNTRUSTED input. It is
 * never bound to `v-html` raw: it goes through `sanitizeTelegramHtml`
 * (`@core/utils`), a strict allowlist of the tags Telegram supports with
 * http(s)/tg links only.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = defineProps<{
  /** Heading above the bubble; defaults to "Preview". */
  title?: string;
  /** Composed HTML (when formatting is on) — sanitized before rendering. */
  html?: string | null;
  /** Plain text fallback (when formatting is off) — rendered as text, never HTML. */
  text?: string | null;
  /** Media kind to show a placeholder for (photo/video/…); null or 'text' for none. */
  mediaType?: string | null;
  /** Caption shown under media (sanitized like `html` when `captionIsHtml`). */
  caption?: string | null;
  captionIsHtml?: boolean;
  textIsHtml?: boolean;
  /** Inline keyboard button labels to render as preview chips. */
  keyboardButtons?: string[];
}>();

const { t, te } = useI18n();

const bodyHtml = computed(() =>
  props.textIsHtml && props.html ? sanitizeTelegramHtml(props.html) : '',
);

const captionHtml = computed(() =>
  props.captionIsHtml && props.caption ? sanitizeTelegramHtml(props.caption) : '',
);

const hasMedia = computed(() => !!props.mediaType && props.mediaType !== 'text');
const mediaLabel = computed(() => {
  const key = `admin.broadcasts.type.${props.mediaType}`;
  return te(key) ? t(key) : (props.mediaType ?? '');
});
const buttons = computed(() => props.keyboardButtons ?? []);
</script>

<template>
  <!-- eslint-disable vue/no-v-html -- HTML is sanitized via sanitizeTelegramHtml (strict allowlist) before binding -->
  <div class="flex flex-col gap-2">
    <span class="text-xs font-medium text-muted-foreground">
      {{ title ?? t('admin.broadcasts.preview.title') }}
    </span>
    <div class="w-full max-w-sm rounded-2xl rounded-bl-sm border border-border bg-card p-3 shadow-sm">
      <!-- Media placeholder -->
      <div
        v-if="hasMedia"
        class="mb-2 flex h-32 items-center justify-center rounded-lg bg-muted text-xs text-muted-foreground"
      >
        {{ t('admin.broadcasts.preview.mediaPlaceholder', { type: mediaLabel }) }}
      </div>

      <!-- Caption (media) -->
      <template v-if="hasMedia">
        <div
          v-if="captionHtml"
          class="whitespace-pre-wrap break-words text-sm leading-relaxed"
          v-html="captionHtml"
        />
        <div
          v-else-if="caption"
          class="whitespace-pre-wrap break-words text-sm leading-relaxed"
        >
          {{ caption }}
        </div>
      </template>

      <!-- Text body -->
      <template v-else>
        <div
          v-if="bodyHtml"
          class="whitespace-pre-wrap break-words text-sm leading-relaxed"
          v-html="bodyHtml"
        />
        <div
          v-else-if="text"
          class="whitespace-pre-wrap break-words text-sm leading-relaxed"
        >
          {{ text }}
        </div>
        <div
          v-else
          class="text-sm italic text-muted-foreground"
        >
          {{ t('admin.broadcasts.preview.empty') }}
        </div>
      </template>

      <!-- Inline keyboard preview -->
      <div
        v-if="buttons.length"
        class="mt-2 flex flex-col gap-1"
      >
        <div
          v-for="(label, i) in buttons"
          :key="i"
          class="rounded-md bg-primary/10 px-3 py-1.5 text-center text-xs font-medium text-primary"
        >
          {{ label }}
        </div>
      </div>
    </div>
  </div>
</template>
