'use client';

import { useState } from 'react';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { apiFetch } from '@/config/kubb-config';

export function AiStreamingDemo() {
  const [text, setText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  const startStream = async () => {
    setText('');
    setIsStreaming(true);

    try {
      const res = await apiFetch('/demo/stream');
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ') && !line.includes('[DONE]')) {
            setText(prev => prev + line.slice(6));
          }
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <DemoSection icon="🤖" title="AI Streaming">
      <div className="space-y-4">
        <Button onClick={startStream} disabled={isStreaming}>
          {isStreaming ? 'Streaming...' : 'Start Stream'}
        </Button>
        <div className="bg-muted rounded-lg p-4 min-h-[120px] font-mono text-sm whitespace-pre-wrap">
          {text}
          {isStreaming && <span className="animate-pulse">▊</span>}
        </div>
        <p className="text-xs text-muted-foreground">
          Simulates AI streaming response using Server-Sent Events
        </p>
      </div>
    </DemoSection>
  );
}
