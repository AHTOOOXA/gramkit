/**
 * Telegram-HTML helpers for message composers (admin broadcasts and the like).
 *
 * Telegram's `parse_mode=HTML` accepts a small set of inline tags. One list
 * (`TELEGRAM_HTML_TAGS`) drives both the auto-detect regex and the preview
 * sanitizer, so a tag that switches a message to HTML is also a tag the preview
 * renders.
 */

/** Tags Telegram renders with `parse_mode=HTML` (lowercase). */
export const TELEGRAM_HTML_TAGS = [
  'b',
  'strong',
  'i',
  'em',
  'u',
  'ins',
  's',
  'strike',
  'del',
  'a',
  'code',
  'pre',
  'span',
  'tg-spoiler',
  'blockquote',
] as const;

/**
 * Matches an opening or closing Telegram-supported tag. Composers use it to
 * switch a message to HTML when the admin has typed tags; otherwise the tags
 * would ship literally.
 */
export const TELEGRAM_HTML_TAG_RE = new RegExp(
  `</?(?:${TELEGRAM_HTML_TAGS.join('|')})\\b[^>]*>`,
  'i',
);

// The preview also keeps <br> (Telegram ignores it; text newlines carry the breaks).
const ALLOWED_TAGS = new Set<string>([...TELEGRAM_HTML_TAGS.map((tag) => tag.toUpperCase()), 'BR']);
const ALLOWED_URL_SCHEMES = ['http:', 'https:', 'tg:'];

/**
 * Strict allowlist sanitizer for previewing Telegram HTML in the browser.
 *
 * SECURITY: message HTML is admin-authored but still UNTRUSTED input. Never
 * pass it to `v-html` raw; run it through this first. It parses the HTML, walks
 * the tree and rebuilds it keeping ONLY the Telegram tags, a vetted `href`
 * (http/https/tg) on `<a>` and `class="tg-spoiler"` on `<span>`. Scripts,
 * styles, event handlers, unknown tags (their text is kept) and every other
 * attribute are dropped.
 * There is no DOMPurify dependency, so this allowlist is the sanitizer.
 *
 * Without a DOM (SSR/SSG) it returns an empty string rather than guess.
 */
export function sanitizeTelegramHtml(input: string): string {
  if (typeof window === 'undefined' || typeof DOMParser === 'undefined') return '';

  const doc = new DOMParser().parseFromString(input, 'text/html');
  const clean = (node: Node): string => {
    let out = '';
    node.childNodes.forEach((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        out += escapeText(child.textContent ?? '');
        return;
      }
      if (child.nodeType !== Node.ELEMENT_NODE) return;
      const el = child as Element;
      const tag = el.tagName;
      if (!ALLOWED_TAGS.has(tag)) {
        // Unknown tag: drop the tag but keep its (sanitized) children.
        out += clean(el);
        return;
      }
      if (tag === 'BR') {
        out += '<br>';
        return;
      }
      const name = tag.toLowerCase();
      out += `<${name}${safeAttrs(el, tag)}>${clean(el)}</${name}>`;
    });
    return out;
  };
  return clean(doc.body);
}

function safeAttrs(el: Element, tag: string): string {
  if (tag === 'A') {
    const href = el.getAttribute('href') ?? '';
    return isSafeUrl(href) ? ` href="${escapeAttr(href)}"` : '';
  }
  if (tag === 'SPAN') {
    return el.getAttribute('class') === 'tg-spoiler' ? ' class="tg-spoiler"' : '';
  }
  return '';
}

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url, window.location.origin);
    return ALLOWED_URL_SCHEMES.includes(parsed.protocol);
  } catch {
    return false;
  }
}

function escapeText(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escapeAttr(s: string): string {
  return escapeText(s).replace(/"/g, '&quot;');
}
