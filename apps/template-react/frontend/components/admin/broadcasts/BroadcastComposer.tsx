'use client';

import { useEffect, useRef, useState } from 'react';
import { getErrorMessage, isApiError } from '@tma-platform/core-react/errors';
import {
  AlertTriangle,
  ArrowLeft,
  Eye,
  Loader2,
  Rocket,
  Save,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { TELEGRAM_HTML_TAG_RE } from '@/lib/admin/telegramHtml';
import { useAdminLabels } from '@/hooks/useAdminLabels';
import { useBroadcasts, type BroadcastMediaType } from '@/hooks/useBroadcasts';
import { AdminActionDialog } from '@/components/admin/AdminActionDialog';
import {
  AdminEmptyState,
  AdminStateBlock,
} from '@/components/admin/AdminStateBlock';
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
import { useAuth } from '@/hooks';
import { useRouter } from '@/i18n/navigation';
import { useGetBroadcast } from '@/src/gen/hooks/useGetBroadcast';
import { usePreviewBroadcast } from '@/src/gen/hooks/usePreviewBroadcast';
import {
  broadcastCreateRequestMessageTypeEnum,
  broadcastCreateRequestTimeSlotEnum,
  type BroadcastCreateRequestMessageTypeEnum,
  type BroadcastCreateRequestTimeSlotEnum,
} from '@/src/gen/models/BroadcastCreateRequest';
import type { BroadcastDetail } from '@/src/gen/models/BroadcastDetail';

import { KeyboardBuilder, type KeyboardType } from './KeyboardBuilder';
import { MediaUploadField } from './MediaUploadField';
import { TelegramMessagePreview } from './TelegramMessagePreview';

type MessageType = BroadcastCreateRequestMessageTypeEnum;
type TimeSlot = BroadcastCreateRequestTimeSlotEnum;

interface ComposerForm {
  message_type: MessageType;
  time_slot: TimeSlot;
  deadline: string;
  /** '' while the field is cleared (sent as 0, like Vue's v-model.number). */
  priority: number | '';
  message_text: string;
  has_text_formatting: boolean;
  media_file_id: string | null;
  caption: string;
  has_caption_formatting: boolean;
  keyboard_type: KeyboardType;
  keyboard_button_text: string | null;
}

/** Local `YYYY-MM-DDTHH:mm` for `<input type="datetime-local">`. */
const toLocalInput = (d: Date): string => {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${String(d.getFullYear())}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const initialForm = (): ComposerForm => ({
  message_type: 'text',
  time_slot: 'morning',
  // Default deadline: a week from now.
  deadline: toLocalInput(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)),
  priority: 80,
  message_text: '',
  has_text_formatting: false,
  media_file_id: null,
  caption: '',
  has_caption_formatting: false,
  keyboard_type: 'none',
  keyboard_button_text: null,
});

const fromBroadcast = (b: BroadcastDetail): ComposerForm => ({
  message_type: b.message_type as MessageType,
  time_slot: b.time_slot.toLowerCase() === 'evening' ? 'evening' : 'morning',
  priority: b.priority,
  message_text: b.message_text ?? '',
  has_text_formatting: b.has_text_formatting,
  media_file_id: b.media_file_id ?? null,
  caption: b.caption ?? '',
  has_caption_formatting: b.has_caption_formatting,
  keyboard_type: (b.keyboard_type as KeyboardType | null) ?? 'none',
  keyboard_button_text: b.keyboard_button_text ?? null,
  deadline: toLocalInput(new Date(b.deadline)),
});

/**
 * BroadcastComposer — create (`/admin/broadcasts/new`, no `editId`) and edit
 * (`/admin/broadcasts/[id]/edit`). Message type, media upload, text or caption
 * with optional HTML formatting, inline keyboard, time slot, deadline and
 * priority, a live sanitized preview, and preview-to-self.
 *
 * Create with slot 'both' makes two independent rows (morning + evening); edit
 * acts on one row and returns to its detail page. "Send now" (owner only) is
 * offered in create mode for an unsaved message; a saved broadcast is sent
 * from its detail page so the delivery counters land on the row.
 *
 * The stored HTML is the text as typed (the backend keeps `message_html` =
 * `message_text`), so the preview sanitizes the raw text; no `/format` call.
 * Message type, time slot and keyboard options come from the generated enums.
 *
 * Port of template-vue's `BroadcastComposer.vue`.
 */
export function BroadcastComposer({
  editId,
}: {
  /** The broadcast to edit (`null` when the route id isn't a number); omit to create. */
  editId?: number | null;
}) {
  const t = useTranslations('admin');
  const { isOwner, isAdminOrOwner } = useAuth();
  const { broadcastKeyboardButtons, broadcastSlotLabel, broadcastTypeLabel } =
    useAdminLabels();
  const router = useRouter();
  const { create, edit, sendNow, invalidateList, invalidateOne } =
    useBroadcasts();
  const previewMut = usePreviewBroadcast();

  const isEdit = editId !== undefined;
  const [form, setForm] = useState<ComposerForm>(initialForm);
  const update = (patch: Partial<ComposerForm>) => {
    setForm((prev) => ({ ...prev, ...patch }));
  };

  const isText = form.message_type === 'text';

  // A Telegram file id belongs to one media kind: a photo's id sent through
  // send_video fails for every recipient. So a type change made by the admin
  // drops the uploaded file (hydration sets the type directly and keeps it).
  const setMessageType = (next: MessageType) => {
    if (next === form.message_type) return;
    update({ message_type: next, media_file_id: null });
  };

  // ── Edit: load the row and fill the form once per id ─────────────────────
  const {
    data: existing,
    isLoading: existingLoading,
    error: existingError,
    refetch: refetchExisting,
  } = useGetBroadcast(editId ?? 0, {
    query: {
      enabled: isEdit && editId !== null && isAdminOrOwner,
    },
  });

  const notFound =
    isEdit &&
    (editId === null ||
      (isApiError(existingError) && existingError.status === 404));

  // Hydrate once, so a background refetch never overwrites what the admin typed.
  const hydratedId = useRef<number | null>(null);
  useEffect(() => {
    if (!existing || !isEdit || hydratedId.current === existing.id) return;
    hydratedId.current = existing.id;
    setForm(fromBroadcast(existing));
  }, [existing, isEdit]);

  // Telegram renders a small set of inline HTML tags. If the admin typed one,
  // switch the message to HTML; otherwise the tags would ship literally.
  const onTextChange = (value: string) => {
    update(
      TELEGRAM_HTML_TAG_RE.test(value)
        ? { message_text: value, has_text_formatting: true }
        : { message_text: value }
    );
  };
  const onCaptionChange = (value: string) => {
    update(
      TELEGRAM_HTML_TAG_RE.test(value)
        ? { caption: value, has_caption_formatting: true }
        : { caption: value }
    );
  };

  const keyboardButtons = broadcastKeyboardButtons(
    form.keyboard_type,
    form.keyboard_button_text
  );

  // ── Validation and payloads ──────────────────────────────────────────────
  const validationError = (): string | null => {
    if (isText && !form.message_text.trim())
      return t('broadcasts.composer.errorNoText');
    if (!isText && !form.media_file_id)
      return t('broadcasts.composer.errorNoMedia');
    if (!form.deadline) return t('broadcasts.composer.errorNoDeadline');
    return null;
  };

  /** Fields of the saved row (create / edit). */
  const rowBody = () => ({
    message_type: form.message_type,
    deadline: new Date(form.deadline).toISOString(),
    priority: Number(form.priority),
    message_text: isText ? form.message_text : null,
    has_text_formatting: isText ? form.has_text_formatting : false,
    media_file_id: isText ? null : form.media_file_id,
    caption: isText ? null : form.caption || null,
    has_caption_formatting: isText ? false : form.has_caption_formatting,
    keyboard_type: form.keyboard_type,
    keyboard_button_text:
      form.keyboard_type === 'main' ? form.keyboard_button_text : null,
  });

  /** Inline content for preview-to-self and send-now (no row). */
  const contentBody = () => ({
    message_type: form.message_type,
    message_text: isText ? form.message_text : null,
    message_html: isText ? form.message_text : null,
    has_text_formatting: isText && form.has_text_formatting,
    media_file_id: isText ? null : form.media_file_id,
    caption: isText ? null : form.caption || null,
    caption_html: isText ? null : form.caption || null,
    has_caption_formatting: !isText && form.has_caption_formatting,
    keyboard_type: form.keyboard_type,
    keyboard_button_text:
      form.keyboard_type === 'main' ? form.keyboard_button_text : null,
  });

  const ensureValid = (): boolean => {
    const error = validationError();
    if (!error) return true;
    toast.error(error);
    return false;
  };

  // ── Actions ──────────────────────────────────────────────────────────────
  const saving = create.isPending || edit.isPending;

  const onSave = async () => {
    if (!ensureValid()) return;
    try {
      if (isEdit && editId !== null) {
        await edit.mutateAsync({ broadcast_id: editId, data: rowBody() });
        toast.success(t('broadcasts.composer.savedEdit'));
        void invalidateOne(editId);
        void invalidateList();
        router.push(`/admin/broadcasts/${String(editId)}`);
      } else {
        await create.mutateAsync({
          data: { ...rowBody(), time_slot: form.time_slot },
        });
        toast.success(
          form.time_slot === 'both'
            ? t('broadcasts.composer.savedBoth')
            : t('broadcasts.composer.savedCreate')
        );
        void invalidateList();
        router.push('/admin/broadcasts');
      }
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  const onPreviewToSelf = async () => {
    if (!ensureValid()) return;
    try {
      const res = await previewMut.mutateAsync({ data: contentBody() });
      if (res.sent) toast.success(t('broadcasts.composer.previewSent'));
      else toast.error(t('broadcasts.composer.previewFailed'));
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  const [showSendNow, setShowSendNow] = useState(false);

  const onSendNowConfirm = async () => {
    try {
      await sendNow.mutateAsync({ data: contentBody() });
      toast.success(t('broadcasts.composer.sentNow'));
      setShowSendNow(false);
    } catch (e) {
      // Keep the dialog open so the owner can retry.
      toast.error(getErrorMessage(e));
    }
  };

  const goBack = () => {
    if (isEdit && editId !== null) {
      router.push(`/admin/broadcasts/${String(editId)}`);
    } else {
      router.push('/admin/broadcasts');
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2 w-fit"
        onClick={goBack}
      >
        <ArrowLeft className="h-4 w-4" />
        {isEdit ? t('broadcasts.detail.back') : t('broadcasts.backToList')}
      </Button>

      <h2 className="text-lg font-semibold">
        {isEdit
          ? t('broadcasts.composer.editTitle')
          : t('broadcasts.composer.newTitle')}
      </h2>

      {notFound ? (
        <AdminEmptyState>{t('broadcasts.detail.notFound')}</AdminEmptyState>
      ) : (
        <AdminStateBlock
          isLoading={isEdit && existingLoading}
          error={isEdit ? existingError : null}
          onRetry={() => void refetchExisting()}
          loading={
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Skeleton className="h-96 w-full rounded-xl" />
              <Skeleton className="h-48 w-full rounded-xl" />
            </div>
          }
        >
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Form */}
            <section className="bg-card flex min-w-0 flex-col gap-4 rounded-xl border p-4">
              <div className="flex flex-col gap-1.5">
                <Label>{t('broadcasts.composer.messageType')}</Label>
                <Select
                  value={form.message_type}
                  onValueChange={(value) => {
                    setMessageType(value as MessageType);
                  }}
                >
                  <SelectTrigger className="w-full sm:w-56">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.values(broadcastCreateRequestMessageTypeEnum).map(
                      (value) => (
                        <SelectItem key={value} value={value}>
                          {broadcastTypeLabel(value)}
                        </SelectItem>
                      )
                    )}
                  </SelectContent>
                </Select>
              </div>

              {!isText && (
                <MediaUploadField
                  messageType={form.message_type as BroadcastMediaType}
                  fileId={form.media_file_id}
                  onFileIdChange={(value) => {
                    update({ media_file_id: value });
                  }}
                />
              )}

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="broadcast-body">
                  {isText
                    ? t('broadcasts.composer.text')
                    : t('broadcasts.composer.caption')}
                </Label>
                {isText ? (
                  <Textarea
                    id="broadcast-body"
                    rows={6}
                    value={form.message_text}
                    placeholder={t('broadcasts.composer.textPlaceholder')}
                    onChange={(e) => {
                      onTextChange(e.target.value);
                    }}
                  />
                ) : (
                  <Textarea
                    id="broadcast-body"
                    rows={4}
                    value={form.caption}
                    placeholder={t('broadcasts.composer.captionPlaceholder')}
                    onChange={(e) => {
                      onCaptionChange(e.target.value);
                    }}
                  />
                )}
                <label className="text-muted-foreground mt-1 flex items-center gap-2 text-xs">
                  <Checkbox
                    checked={
                      isText
                        ? form.has_text_formatting
                        : form.has_caption_formatting
                    }
                    onCheckedChange={(checked) => {
                      update(
                        isText
                          ? { has_text_formatting: checked === true }
                          : { has_caption_formatting: checked === true }
                      );
                    }}
                  />
                  {t('broadcasts.composer.htmlFormatting')}
                </label>
                <p className="text-muted-foreground text-xs">
                  {t('broadcasts.composer.htmlAutoHint')}
                </p>
              </div>

              <KeyboardBuilder
                keyboardType={form.keyboard_type}
                buttonText={form.keyboard_button_text}
                onKeyboardTypeChange={(value) => {
                  update({ keyboard_type: value });
                }}
                onButtonTextChange={(value) => {
                  update({ keyboard_button_text: value });
                }}
              />

              {/* Time slot: create only (edit acts on a single row). */}
              {!isEdit && (
                <div className="flex flex-col gap-1.5">
                  <Label>{t('broadcasts.composer.timeSlot')}</Label>
                  <Select
                    value={form.time_slot}
                    onValueChange={(value) => {
                      update({ time_slot: value as TimeSlot });
                    }}
                  >
                    <SelectTrigger className="w-full sm:w-56">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.values(broadcastCreateRequestTimeSlotEnum).map(
                        (value) => (
                          <SelectItem key={value} value={value}>
                            {broadcastSlotLabel(value)}
                          </SelectItem>
                        )
                      )}
                    </SelectContent>
                  </Select>
                  {form.time_slot === 'both' && (
                    <p className="text-muted-foreground text-xs">
                      {t('broadcasts.composer.bothHint')}
                    </p>
                  )}
                </div>
              )}

              <div className="flex flex-col gap-4 sm:flex-row">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="broadcast-deadline">
                    {t('broadcasts.composer.deadline')}
                  </Label>
                  <Input
                    id="broadcast-deadline"
                    type="datetime-local"
                    className="w-full sm:w-56"
                    value={form.deadline}
                    onChange={(e) => {
                      update({ deadline: e.target.value });
                    }}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="broadcast-priority">
                    {t('broadcasts.composer.priority')}
                  </Label>
                  <Input
                    id="broadcast-priority"
                    type="number"
                    min={0}
                    max={1000}
                    className="w-full sm:w-28"
                    value={form.priority}
                    onChange={(e) => {
                      update({
                        priority:
                          e.target.value === '' ? '' : e.target.valueAsNumber,
                      });
                    }}
                  />
                </div>
              </div>

              <p className="text-muted-foreground flex items-start gap-1.5 text-xs">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {t('broadcasts.composer.targetingNote')}
              </p>

              <div className="border-border flex flex-col gap-2 border-t pt-4 sm:flex-row sm:flex-wrap">
                <Button disabled={saving} onClick={() => void onSave()}>
                  {saving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  {isEdit
                    ? t('broadcasts.composer.save')
                    : t('broadcasts.composer.schedule')}
                </Button>
                <Button
                  variant="outline"
                  disabled={previewMut.isPending}
                  onClick={() => void onPreviewToSelf()}
                >
                  {previewMut.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                  {t('broadcasts.composer.previewToSelf')}
                </Button>
                {isOwner && !isEdit && (
                  <Button
                    variant="destructive"
                    disabled={sendNow.isPending}
                    onClick={() => {
                      if (ensureValid()) setShowSendNow(true);
                    }}
                  >
                    <Rocket className="h-4 w-4" />
                    {t('broadcasts.composer.sendNow')}
                  </Button>
                )}
              </div>
            </section>

            {/* Live preview */}
            <div className="min-w-0 lg:sticky lg:top-4 lg:self-start">
              <TelegramMessagePreview
                text={form.message_text}
                html={form.message_text}
                textIsHtml={isText && form.has_text_formatting}
                mediaType={isText ? null : form.message_type}
                caption={form.caption}
                captionIsHtml={!isText && form.has_caption_formatting}
                keyboardButtons={keyboardButtons}
              />
            </div>
          </div>
        </AdminStateBlock>
      )}

      <AdminActionDialog
        open={showSendNow}
        onOpenChange={setShowSendNow}
        title={t('broadcasts.composer.sendNowConfirmTitle')}
        description={t('broadcasts.composer.sendNowConfirmDesc')}
        pending={sendNow.isPending}
        confirmLabel={t('broadcasts.composer.sendNow')}
        onConfirm={() => void onSendNowConfirm()}
      />
    </div>
  );
}
