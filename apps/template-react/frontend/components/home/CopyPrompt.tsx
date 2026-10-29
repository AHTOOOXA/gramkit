'use client';

import { useEffect, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { SiClaude } from 'react-icons/si';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';

/**
 * A ready-made Claude Code prompt with a copy button: the "or let the agent do
 * it" path next to a list of manual steps.
 */
export function CopyPrompt({ prompt }: { prompt: string }) {
  const t = useTranslations('homePage.quickStart.prompt');
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
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
    } catch {
      toast.error(t('copyFailed'));
    }
  };

  return (
    <div className="rounded-lg border border-primary/20 bg-primary/[0.03] p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-xs font-medium text-foreground">
          <SiClaude className="w-3.5 h-3.5 text-[#D97757]" />
          {t('label')}
        </p>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-2 text-xs"
          onClick={() => void copy()}
          aria-label={t('copy')}
        >
          {copied ? <Check className="w-3.5 h-3.5 text-primary" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? t('copied') : t('copy')}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{prompt}</p>
    </div>
  );
}
