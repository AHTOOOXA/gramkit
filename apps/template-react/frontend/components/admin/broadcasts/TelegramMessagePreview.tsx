'use client';

import { useMemo, useSyncExternalStore } from 'react';
import { useTranslations } from 'next-intl';

import { sanitizeTelegramHtml } from '@/lib/admin/telegramHtml';

const subscribeNoop = () => () => undefined;

/**
 * TelegramMessagePreview — a chat-bubble preview of a broadcast: media
 * placeholder, text or caption, and the inline keyboard as button chips. Used
 * live by the composer and for the stored message on the detail page.
 *
 * SECURITY: the message HTML is admin-authored but still UNTRUSTED input. It is
 * never passed to `dangerouslySetInnerHTML` raw: it goes through
 * `sanitizeTelegramHtml` (`@/lib/admin/telegramHtml`), a strict allowlist of
 * the tags Telegram supports with http(s)/tg links only.
 *
 * The sanitizer needs a DOM, so the HTML is only built on the client: the
 * server render and hydration show the plain text, and React never has to
 * reconcile a `dangerouslySetInnerHTML` mismatch.
 *
 * Port of template-vue's `TelegramMessagePreview.vue`.
 */
export function TelegramMessagePreview({
  title,
  html,
  text,
  mediaType,
  caption,
  captionIsHtml = false,
  textIsHtml = false,
  keyboardButtons = [],
}: {
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
}) {
  const t = useTranslations('admin');
  // false on the server and during hydration, true for client renders.
  const isClient = useSyncExternalStore(
    subscribeNoop,
    () => true,
    () => false
  );

  const bodyHtml = useMemo(
    () => (isClient && textIsHtml && html ? sanitizeTelegramHtml(html) : ''),
    [isClient, textIsHtml, html]
  );
  const captionHtml = useMemo(
    () =>
      isClient && captionIsHtml && caption ? sanitizeTelegramHtml(caption) : '',
    [isClient, captionIsHtml, caption]
  );

  const hasMedia = !!mediaType && mediaType !== 'text';
  const mediaLabel =
    mediaType && t.has(`broadcasts.type.${mediaType}`)
      ? t(`broadcasts.type.${mediaType}`)
      : (mediaType ?? '');

  const textClass = 'text-sm leading-relaxed break-words whitespace-pre-wrap';

  return (
    <div className="flex flex-col gap-2">
      <span className="text-muted-foreground text-xs font-medium">
        {title ?? t('broadcasts.preview.title')}
      </span>
      <div className="border-border bg-card w-full max-w-sm rounded-2xl rounded-bl-sm border p-3 shadow-sm">
        {hasMedia ? (
          <>
            {/* Media placeholder */}
            <div className="bg-muted text-muted-foreground mb-2 flex h-32 items-center justify-center rounded-lg text-xs">
              {t('broadcasts.preview.mediaPlaceholder', { type: mediaLabel })}
            </div>
            {/* Caption: sanitized HTML (allowlist) or plain text */}
            {captionHtml ? (
              <div
                className={textClass}
                dangerouslySetInnerHTML={{ __html: captionHtml }}
              />
            ) : caption ? (
              <div className={textClass}>{caption}</div>
            ) : null}
          </>
        ) : bodyHtml ? (
          // Sanitized by sanitizeTelegramHtml (strict allowlist) above.
          <div
            className={textClass}
            dangerouslySetInnerHTML={{ __html: bodyHtml }}
          />
        ) : text ? (
          <div className={textClass}>{text}</div>
        ) : (
          <div className="text-muted-foreground text-sm italic">
            {t('broadcasts.preview.empty')}
          </div>
        )}

        {/* Inline keyboard preview */}
        {keyboardButtons.length > 0 && (
          <div className="mt-2 flex flex-col gap-1">
            {keyboardButtons.map((label, i) => (
              <div
                key={i}
                className="bg-primary/10 text-primary rounded-md px-3 py-1.5 text-center text-xs font-medium"
              >
                {label}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
