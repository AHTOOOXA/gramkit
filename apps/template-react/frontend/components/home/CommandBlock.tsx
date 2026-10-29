'use client';

import { useEffect, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

/**
 * Shell commands with one copy button for all of them. Lines starting with
 * `#` render as comments. Always dark, like a terminal.
 */
export function CommandBlock({ commands }: { commands: string[] }) {
  const t = useTranslations('homePage.quickStart');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => {
      setCopied(false);
    }, 2000);
    return () => {
      clearTimeout(timer);
    };
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(commands.join('\n'));
      setCopied(true);
    } catch {
      toast.error(t('prompt.copyFailed'));
    }
  };

  return (
    <div className="relative overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-100">
      <pre className="overflow-x-auto py-3 pr-12 pl-4 font-mono text-xs leading-6">
        {commands.map((line) =>
          line.startsWith('#') ? (
            <div key={line} className="text-zinc-500">
              {line}
            </div>
          ) : (
            <div key={line}>
              <span className="text-sky-400 select-none">$ </span>
              {line}
            </div>
          )
        )}
      </pre>
      {/* Opaque strip: long lines scroll under the button instead of peeking past it */}
      <div className="absolute inset-y-0 right-0 bg-zinc-950 pt-1.5 pr-1.5 shadow-[-12px_0_12px_-2px_var(--color-zinc-950)]">
        <button
          type="button"
          onClick={() => void copy()}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100 focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:outline-none"
          aria-label={copied ? t('prompt.copied') : t('copy')}
        >
          {copied ? <Check className="h-4 w-4 text-sky-400" /> : <Copy className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}
