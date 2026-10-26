<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { toast } from 'vue-sonner';
import { AlertTriangle, ArrowLeft, Eye, Loader2, Rocket, Save } from '@lucide/vue';
import { getErrorMessage, isApiError } from '@core/errors';
import { TELEGRAM_HTML_TAG_RE } from '@core/utils';
import { useAdminLabels } from '@app/admin/useAdminLabels';
import { useAuth } from '@app/composables/useAuth';
import { useBroadcasts, type BroadcastMediaType } from '@app/composables/useBroadcasts';
import { useGetBroadcast } from '@gen/hooks/useGetBroadcast';
import { usePreviewBroadcast } from '@gen/hooks/usePreviewBroadcast';
import type { BroadcastDetail } from '@gen/models/BroadcastDetail';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import AdminActionDialog from '@app/presentation/components/admin/AdminActionDialog.vue';
import AdminStateBlock from '@app/presentation/components/admin/AdminStateBlock.vue';
import KeyboardBuilder from '@app/presentation/components/admin/broadcasts/KeyboardBuilder.vue';
import MediaUploadField from '@app/presentation/components/admin/broadcasts/MediaUploadField.vue';
import TelegramMessagePreview from '@app/presentation/components/admin/broadcasts/TelegramMessagePreview.vue';

type MessageType = 'text' | BroadcastMediaType;
type TimeSlot = 'morning' | 'evening' | 'both';
type KeyboardType = 'none' | 'main' | 'daily';

/**
 * BroadcastComposer — create (`/admin/broadcasts/new`) and edit
 * (`/admin/broadcasts/:id/edit`). Message type, media upload, text or caption
 * with optional HTML formatting, inline keyboard, time slot, deadline and
 * priority, a live sanitized preview, and preview-to-self.
 *
 * Create with slot 'both' makes two independent rows (morning + evening); edit
 * acts on one row and returns to its detail page. "Send now" (owner only) is
 * offered in create mode for an unsaved message; a saved broadcast is sent from
 * its detail page so the delivery counters land on the row.
 *
 * The stored HTML is the text as typed (the backend keeps `message_html` =
 * `message_text`), so the preview sanitizes the raw text; no `/format` call.
 */
const { t } = useI18n();
const { isOwner, isAdminOrOwner } = useAuth();
const { broadcastKeyboardButtons } = useAdminLabels();
const route = useRoute();
const router = useRouter();
const { create, edit, sendNow, invalidateList, invalidateOne } = useBroadcasts();
const previewMut = usePreviewBroadcast();

const editId = computed<number | null>(() => {
  const raw = route.params.id;
  if (raw === undefined) return null;
  const n = Number(raw);
  return Number.isInteger(n) ? n : null;
});
const isEdit = computed(() => route.name === 'admin-broadcast-edit');

/** Local `YYYY-MM-DDTHH:mm` for `<input type="datetime-local">`. */
const toLocalInput = (d: Date): string => {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const form = reactive({
  message_type: 'text' as MessageType,
  time_slot: 'morning' as TimeSlot,
  // Default deadline: a week from now.
  deadline: toLocalInput(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)),
  priority: 80,
  message_text: '',
  has_text_formatting: false,
  media_file_id: null as string | null,
  caption: '',
  has_caption_formatting: false,
  keyboard_type: 'none' as KeyboardType,
  keyboard_button_text: null as string | null,
});

const isText = computed(() => form.message_type === 'text');

// A Telegram file id belongs to one media kind: a photo's id sent through send_video fails for
// every recipient. So a type change made by the admin drops the uploaded file (hydrate() sets the
// type directly and keeps the stored file).
const setMessageType = (next: MessageType) => {
  if (next === form.message_type) return;
  form.message_type = next;
  form.media_file_id = null;
};
const mediaKind = computed(() => form.message_type as BroadcastMediaType);

// ── Edit: load the row and fill the form once per id ────────────────────────
const {
  data: existing,
  isLoading: existingLoading,
  error: existingError,
  refetch: refetchExisting,
} = useGetBroadcast(
  () => editId.value ?? 0,
  { query: { enabled: () => isEdit.value && editId.value !== null && isAdminOrOwner.value } },
);

const notFound = computed(
  () => isEdit.value && (editId.value === null || (isApiError(existingError.value) && existingError.value.status === 404)),
);

const hydratedId = ref<number | null>(null);
const hydrate = (b: BroadcastDetail) => {
  form.message_type = b.message_type as MessageType;
  form.time_slot = b.time_slot.toLowerCase() === 'evening' ? 'evening' : 'morning';
  form.priority = b.priority;
  form.message_text = b.message_text ?? '';
  form.has_text_formatting = b.has_text_formatting;
  form.media_file_id = b.media_file_id ?? null;
  form.caption = b.caption ?? '';
  form.has_caption_formatting = b.has_caption_formatting;
  form.keyboard_type = (b.keyboard_type as KeyboardType | null) ?? 'none';
  form.keyboard_button_text = b.keyboard_button_text ?? null;
  form.deadline = toLocalInput(new Date(b.deadline));
};

// Hydrate once, so a background refetch never overwrites what the admin typed.
watch(
  existing,
  (b) => {
    if (!b || !isEdit.value || hydratedId.value === b.id) return;
    hydrate(b);
    hydratedId.value = b.id;
  },
  { immediate: true },
);

// Telegram renders a small set of inline HTML tags. If the admin typed one,
// switch the message to HTML; otherwise the tags would ship literally.
watch(
  () => form.message_text,
  (v) => {
    if (TELEGRAM_HTML_TAG_RE.test(v)) form.has_text_formatting = true;
  },
);
watch(
  () => form.caption,
  (v) => {
    if (TELEGRAM_HTML_TAG_RE.test(v)) form.has_caption_formatting = true;
  },
);

const keyboardButtons = computed(() =>
  broadcastKeyboardButtons(form.keyboard_type, form.keyboard_button_text),
);

// ── Validation and payloads ────────────────────────────────────────────────
const validationError = computed<string | null>(() => {
  if (isText.value && !form.message_text.trim()) return t('admin.broadcasts.composer.errorNoText');
  if (!isText.value && !form.media_file_id) return t('admin.broadcasts.composer.errorNoMedia');
  if (!form.deadline) return t('admin.broadcasts.composer.errorNoDeadline');
  return null;
});

/** Fields of the saved row (create / edit). */
const rowBody = () => ({
  message_type: form.message_type,
  deadline: new Date(form.deadline).toISOString(),
  priority: Number(form.priority),
  message_text: isText.value ? form.message_text : null,
  has_text_formatting: isText.value ? form.has_text_formatting : false,
  media_file_id: isText.value ? null : form.media_file_id,
  caption: isText.value ? null : form.caption || null,
  has_caption_formatting: isText.value ? false : form.has_caption_formatting,
  keyboard_type: form.keyboard_type,
  keyboard_button_text: form.keyboard_type === 'main' ? form.keyboard_button_text : null,
});

/** Inline content for preview-to-self and send-now (no row). */
const contentBody = () => ({
  message_type: form.message_type,
  message_text: isText.value ? form.message_text : null,
  message_html: isText.value ? form.message_text : null,
  has_text_formatting: isText.value && form.has_text_formatting,
  media_file_id: isText.value ? null : form.media_file_id,
  caption: isText.value ? null : form.caption || null,
  caption_html: isText.value ? null : form.caption || null,
  has_caption_formatting: !isText.value && form.has_caption_formatting,
  keyboard_type: form.keyboard_type,
  keyboard_button_text: form.keyboard_type === 'main' ? form.keyboard_button_text : null,
});

const ensureValid = (): boolean => {
  if (!validationError.value) return true;
  toast.error(validationError.value);
  return false;
};

// ── Actions ────────────────────────────────────────────────────────────────
const saving = computed(() => create.isPending.value || edit.isPending.value);

const onSave = async () => {
  if (!ensureValid()) return;
  try {
    if (isEdit.value && editId.value !== null) {
      const id = editId.value;
      await edit.mutateAsync({ broadcast_id: id, data: rowBody() });
      toast.success(t('admin.broadcasts.composer.savedEdit'));
      void invalidateOne(id);
      void invalidateList();
      void router.push({ name: 'admin-broadcast-detail', params: { id } });
    } else {
      await create.mutateAsync({ data: { ...rowBody(), time_slot: form.time_slot } });
      toast.success(
        form.time_slot === 'both'
          ? t('admin.broadcasts.composer.savedBoth')
          : t('admin.broadcasts.composer.savedCreate'),
      );
      void invalidateList();
      void router.push({ name: 'admin-broadcasts' });
    }
  } catch (e) {
    toast.error(getErrorMessage(e));
  }
};

const onPreviewToSelf = async () => {
  if (!ensureValid()) return;
  try {
    const res = await previewMut.mutateAsync({ data: contentBody() });
    if (res.sent) toast.success(t('admin.broadcasts.composer.previewSent'));
    else toast.error(t('admin.broadcasts.composer.previewFailed'));
  } catch (e) {
    toast.error(getErrorMessage(e));
  }
};

const showSendNow = ref(false);

const onSendNowClick = () => {
  if (ensureValid()) showSendNow.value = true;
};

const onSendNowConfirm = async () => {
  try {
    await sendNow.mutateAsync({ data: contentBody() });
    toast.success(t('admin.broadcasts.composer.sentNow'));
    showSendNow.value = false;
  } catch (e) {
    // Keep the dialog open so the owner can retry.
    toast.error(getErrorMessage(e));
  }
};

const goBack = () => {
  if (isEdit.value && editId.value !== null) {
    void router.push({ name: 'admin-broadcast-detail', params: { id: editId.value } });
  } else {
    void router.push({ name: 'admin-broadcasts' });
  }
};
</script>

<template>
  <div class="flex flex-col gap-4">
    <Button
      variant="ghost"
      size="sm"
      class="-ml-2 w-fit"
      @click="goBack"
    >
      <ArrowLeft class="h-4 w-4" />
      {{ isEdit ? t('admin.broadcasts.detail.back') : t('admin.broadcasts.backToList') }}
    </Button>

    <h2 class="text-lg font-semibold">
      {{ isEdit ? t('admin.broadcasts.composer.editTitle') : t('admin.broadcasts.composer.newTitle') }}
    </h2>

    <div
      v-if="notFound"
      class="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-12 text-center text-sm text-muted-foreground"
    >
      {{ t('admin.broadcasts.detail.notFound') }}
    </div>

    <AdminStateBlock
      v-else
      :is-loading="isEdit && existingLoading"
      :error="isEdit ? existingError : null"
      @retry="refetchExisting()"
    >
      <template #loading>
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Skeleton class="h-96 w-full rounded-xl" />
          <Skeleton class="h-48 w-full rounded-xl" />
        </div>
      </template>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <!-- Form -->
        <section class="flex min-w-0 flex-col gap-4 rounded-xl border bg-card p-4">
          <div class="flex flex-col gap-1.5">
            <Label>{{ t('admin.broadcasts.composer.messageType') }}</Label>
            <Select :model-value="form.message_type" @update:model-value="setMessageType($event as MessageType)">
              <SelectTrigger class="w-full sm:w-56">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="text">{{ t('admin.broadcasts.type.text') }}</SelectItem>
                <SelectItem value="photo">{{ t('admin.broadcasts.type.photo') }}</SelectItem>
                <SelectItem value="video">{{ t('admin.broadcasts.type.video') }}</SelectItem>
                <SelectItem value="animation">{{ t('admin.broadcasts.type.animation') }}</SelectItem>
                <SelectItem value="document">{{ t('admin.broadcasts.type.document') }}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <MediaUploadField
            v-if="!isText"
            :message-type="mediaKind"
            :file-id="form.media_file_id"
            @update:file-id="form.media_file_id = $event"
          />

          <div class="flex flex-col gap-1.5">
            <Label for="broadcast-body">
              {{ isText ? t('admin.broadcasts.composer.text') : t('admin.broadcasts.composer.caption') }}
            </Label>
            <Textarea
              v-if="isText"
              id="broadcast-body"
              v-model="form.message_text"
              :rows="6"
              :placeholder="t('admin.broadcasts.composer.textPlaceholder')"
            />
            <Textarea
              v-else
              id="broadcast-body"
              v-model="form.caption"
              :rows="4"
              :placeholder="t('admin.broadcasts.composer.captionPlaceholder')"
            />
            <label class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
              <Checkbox
                v-if="isText"
                :model-value="form.has_text_formatting"
                @update:model-value="form.has_text_formatting = $event === true"
              />
              <Checkbox
                v-else
                :model-value="form.has_caption_formatting"
                @update:model-value="form.has_caption_formatting = $event === true"
              />
              {{ t('admin.broadcasts.composer.htmlFormatting') }}
            </label>
            <p class="text-xs text-muted-foreground">{{ t('admin.broadcasts.composer.htmlAutoHint') }}</p>
          </div>

          <KeyboardBuilder
            :keyboard-type="form.keyboard_type"
            :button-text="form.keyboard_button_text"
            @update:keyboard-type="form.keyboard_type = $event"
            @update:button-text="form.keyboard_button_text = $event"
          />

          <!-- Time slot: create only (edit acts on a single row). -->
          <div
            v-if="!isEdit"
            class="flex flex-col gap-1.5"
          >
            <Label>{{ t('admin.broadcasts.composer.timeSlot') }}</Label>
            <Select v-model="form.time_slot">
              <SelectTrigger class="w-full sm:w-56">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="morning">{{ t('admin.broadcasts.slot.morning') }}</SelectItem>
                <SelectItem value="evening">{{ t('admin.broadcasts.slot.evening') }}</SelectItem>
                <SelectItem value="both">{{ t('admin.broadcasts.slot.both') }}</SelectItem>
              </SelectContent>
            </Select>
            <p
              v-if="form.time_slot === 'both'"
              class="text-xs text-muted-foreground"
            >
              {{ t('admin.broadcasts.composer.bothHint') }}
            </p>
          </div>

          <div class="flex flex-col gap-4 sm:flex-row">
            <div class="flex flex-col gap-1.5">
              <Label for="broadcast-deadline">{{ t('admin.broadcasts.composer.deadline') }}</Label>
              <Input
                id="broadcast-deadline"
                v-model="form.deadline"
                type="datetime-local"
                class="w-full sm:w-56"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <Label for="broadcast-priority">{{ t('admin.broadcasts.composer.priority') }}</Label>
              <Input
                id="broadcast-priority"
                v-model.number="form.priority"
                type="number"
                min="0"
                max="1000"
                class="w-full sm:w-28"
              />
            </div>
          </div>

          <p class="flex items-start gap-1.5 text-xs text-muted-foreground">
            <AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {{ t('admin.broadcasts.composer.targetingNote') }}
          </p>

          <div class="flex flex-col gap-2 border-t border-border pt-4 sm:flex-row sm:flex-wrap">
            <Button
              :disabled="saving"
              @click="onSave"
            >
              <Loader2
                v-if="saving"
                class="h-4 w-4 animate-spin"
              />
              <Save
                v-else
                class="h-4 w-4"
              />
              {{ isEdit ? t('admin.broadcasts.composer.save') : t('admin.broadcasts.composer.schedule') }}
            </Button>
            <Button
              variant="outline"
              :disabled="previewMut.isPending.value"
              @click="onPreviewToSelf"
            >
              <Loader2
                v-if="previewMut.isPending.value"
                class="h-4 w-4 animate-spin"
              />
              <Eye
                v-else
                class="h-4 w-4"
              />
              {{ t('admin.broadcasts.composer.previewToSelf') }}
            </Button>
            <Button
              v-if="isOwner && !isEdit"
              variant="destructive"
              :disabled="sendNow.isPending.value"
              @click="onSendNowClick"
            >
              <Rocket class="h-4 w-4" />
              {{ t('admin.broadcasts.composer.sendNow') }}
            </Button>
          </div>
        </section>

        <!-- Live preview -->
        <div class="min-w-0 lg:sticky lg:top-4 lg:self-start">
          <TelegramMessagePreview
            :text="form.message_text"
            :html="form.message_text"
            :text-is-html="isText && form.has_text_formatting"
            :media-type="isText ? null : form.message_type"
            :caption="form.caption"
            :caption-is-html="!isText && form.has_caption_formatting"
            :keyboard-buttons="keyboardButtons"
          />
        </div>
      </div>
    </AdminStateBlock>

    <AdminActionDialog
      :open="showSendNow"
      :title="t('admin.broadcasts.composer.sendNowConfirmTitle')"
      :description="t('admin.broadcasts.composer.sendNowConfirmDesc')"
      :pending="sendNow.isPending.value"
      :confirm-label="t('admin.broadcasts.composer.sendNow')"
      @update:open="(v) => { if (!v) showSendNow = false; }"
      @confirm="onSendNowConfirm"
    />
  </div>
</template>
