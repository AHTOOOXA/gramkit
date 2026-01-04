'use client';

import { useState, useEffect, useRef } from 'react';
import { RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

const COMMANDS = [
  { text: '$ ', color: 'text-green-500', delay: 0 },
  { text: 'pnpm install', color: 'text-white', delay: 0 },
  { text: '\n$ ', color: 'text-green-500', delay: 800 },
  { text: 'make up APP=template-react', color: 'text-white', delay: 0 },
  { text: '\n\n✓ ', color: 'text-green-500', delay: 1200 },
  { text: 'Localhost  ', color: 'text-gray-400', delay: 0 },
  { text: 'http://localhost:3001/template-react', color: 'text-blue-400', delay: 0 },
  { text: '\n  ', color: 'text-gray-400', delay: 400 },
  { text: 'Tunnel     ', color: 'text-gray-500', delay: 0 },
  { text: 'https://local.yourdomain.com/template-react', color: 'text-gray-500', delay: 0 },
] as const;

export function AnimatedTerminal() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const resetAnimation = () => {
    setCurrentIndex(0);
    setCharIndex(0);
    setIsComplete(false);
    setHasStarted(true);
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !hasStarted) {
          setHasStarted(true);
        }
      },
      { threshold: 0.2 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => {
      observer.disconnect();
    };
  }, [hasStarted]);

  useEffect(() => {
    if (!hasStarted) return;

    if (currentIndex >= COMMANDS.length) {
      setIsComplete(true);
      return;
    }

    const currentCommand = COMMANDS[currentIndex];
    if (!currentCommand) return;

    if (charIndex === 0 && currentCommand.delay > 0) {
      const delayTimer = setTimeout(() => {
        setCharIndex(1);
      }, currentCommand.delay);
      return () => {
        clearTimeout(delayTimer);
      };
    }

    if (charIndex < currentCommand.text.length) {
      const typingSpeed = currentCommand.text.startsWith('\n') ? 0 : 50;
      const timer = setTimeout(() => {
        setCharIndex((prev) => prev + 1);
      }, typingSpeed);

      return () => {
        clearTimeout(timer);
      };
    } else {
      setCurrentIndex((prev) => prev + 1);
      setCharIndex(0);
    }
  }, [currentIndex, charIndex, hasStarted]);

  const renderText = () => {
    const result: React.ReactElement[] = [];

    for (let i = 0; i <= currentIndex && i < COMMANDS.length; i++) {
      const cmd = COMMANDS[i];
      if (!cmd) continue;

      const isCurrentCommand = i === currentIndex;
      const text = isCurrentCommand
        ? cmd.text.slice(0, charIndex)
        : cmd.text;

      if (text) {
        result.push(
          <span key={i} className={cmd.color}>
            {text}
          </span>
        );
      }
    }

    return result;
  };

  return (
    <div ref={containerRef} className="relative group">
      {/* Terminal Window */}
      <div className="bg-gray-900 rounded-lg shadow-2xl overflow-hidden border border-gray-800">
        {/* Title Bar */}
        <div className="bg-gray-800 px-4 py-3 flex items-center justify-between border-b border-gray-700">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          <div className="text-gray-400 text-xs font-medium">terminal</div>
          <div className="w-16" />
        </div>

        {/* Terminal Content */}
        <div className="p-6 font-mono text-sm min-h-[180px] relative">
          <div className="whitespace-pre-wrap">
            {renderText()}
            {!isComplete && hasStarted && (
              <span className="inline-block w-2 h-4 bg-white ml-0.5 animate-pulse" />
            )}
          </div>
        </div>
      </div>

      {/* Replay Button */}
      {isComplete && (
        <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            onClick={resetAnimation}
            variant="outline"
            size="sm"
            className="bg-gray-800/90 border-gray-700 hover:bg-gray-700 text-white"
          >
            <RotateCcw className="w-3 h-3 mr-2" />
            Replay
          </Button>
        </div>
      )}
    </div>
  );
}
