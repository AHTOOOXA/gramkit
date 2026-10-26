<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { toast } from 'vue-sonner';
import { CheckCircle2, Loader2, Upload } from '@lucide/vue';
import { getErrorMessage } from '@core/errors';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { useBroadcasts, type BroadcastMediaType } from '@app/composables/useBroadcasts';

/**
 * MediaUploadField — uploads a media file through the raw multipart util
 * (`useBroadcasts().uploadMedia` → `apiFetch`). The backend sends the file to
 * the acting admin's Telegram chat to mint a `file_id` (then deletes that
 * message); the field emits the `file_id` up to the composer, and sends reuse it.
 * The backend caps uploads (10 MB for photos, 50 MB otherwise) and answers 400.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = defineProps<{
  messageType: BroadcastMediaType;
  fileId: string | null;
}>();

const emit = defineEmits<{ 'update:fileId': [value: string | null] }>();

const { t } = useI18n();
const { uploadMedia } = useBroadcasts();

const isUploading = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

// File-picker hint only; the backend decides what Telegram accepts.
const accept = computed(() => {
  if (props.messageType === 'photo') return 'image/*';
  if (props.messageType === 'video') return 'video/*';
  if (props.messageType === 'animation') return 'image/gif,video/mp4';
  return undefined;
});

const pickFile = () => fileInput.value?.click();

const onFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  isUploading.value = true;
  try {
    const result = await uploadMedia(file, props.messageType);
    emit('update:fileId', result.file_id);
    toast.success(t('admin.broadcasts.composer.uploadDone'));
  } catch (e) {
    toast.error(getErrorMessage(e));
  } finally {
    isUploading.value = false;
    // Allow re-uploading the same file.
    if (fileInput.value) fileInput.value.value = '';
  }
};
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <Label>{{ t('admin.broadcasts.composer.media') }}</Label>
    <div class="flex flex-wrap items-center gap-2">
      <Button
        type="button"
        variant="outline"
        :disabled="isUploading"
        @click="pickFile"
      >
        <Loader2
          v-if="isUploading"
          class="h-4 w-4 animate-spin"
        />
        <Upload
          v-else
          class="h-4 w-4"
        />
        {{ isUploading ? t('admin.broadcasts.composer.uploading') : t('admin.broadcasts.composer.upload') }}
      </Button>
      <span
        v-if="fileId"
        class="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400"
      >
        <CheckCircle2 class="h-3.5 w-3.5" />
        {{ t('admin.broadcasts.composer.uploaded') }}
      </span>
    </div>
    <input
      ref="fileInput"
      type="file"
      class="hidden"
      :accept="accept"
      @change="onFileChange"
    />
  </div>
</template>
