'use client';

import { useRef, useState, type ChangeEvent } from 'react';
import { getErrorMessage } from '@tma-platform/core-react/errors';
import { CheckCircle2, Loader2, Upload } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { useBroadcasts, type BroadcastMediaType } from '@/hooks/useBroadcasts';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

// File-picker hint only; the backend decides what Telegram accepts.
const ACCEPT: Partial<Record<BroadcastMediaType, string>> = {
  photo: 'image/*',
  video: 'video/*',
  animation: 'image/gif,video/mp4',
};

/**
 * MediaUploadField — uploads a media file through the raw multipart util
 * (`useBroadcasts().uploadMedia` → `apiFetch`). The backend sends the file to
 * the acting admin's Telegram chat to mint a `file_id` (then deletes that
 * message); the field reports the `file_id` up to the composer, and sends
 * reuse it. The backend caps uploads (10 MB for photos, 50 MB otherwise) and
 * answers 400.
 *
 * Port of template-vue's `MediaUploadField.vue`.
 */
export function MediaUploadField({
  messageType,
  fileId,
  onFileIdChange,
}: {
  messageType: BroadcastMediaType;
  fileId: string | null;
  onFileIdChange: (value: string | null) => void;
}) {
  const t = useTranslations('admin');
  const { uploadMedia } = useBroadcasts();

  const [isUploading, setIsUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const onFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const input = event.target;
    const file = input.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const result = await uploadMedia(file, messageType);
      onFileIdChange(result.file_id);
      toast.success(t('broadcasts.composer.uploadDone'));
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setIsUploading(false);
      // Allow re-uploading the same file.
      input.value = '';
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <Label>{t('broadcasts.composer.media')}</Label>
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={isUploading}
          onClick={() => fileInput.current?.click()}
        >
          {isUploading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Upload className="h-4 w-4" />
          )}
          {isUploading
            ? t('broadcasts.composer.uploading')
            : t('broadcasts.composer.upload')}
        </Button>
        {fileId && (
          <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {t('broadcasts.composer.uploaded')}
          </span>
        )}
      </div>
      <input
        ref={fileInput}
        type="file"
        className="hidden"
        accept={ACCEPT[messageType]}
        onChange={(e) => void onFileChange(e)}
      />
    </div>
  );
}
