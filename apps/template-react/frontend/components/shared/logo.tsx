'use client';

import { FlaskConical } from 'lucide-react';

import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';

interface LogoProps {
  size?: 'sm' | 'md';
  showText?: boolean;
}

export function Logo({ size = 'md', showText = true }: LogoProps) {
  const iconSize = size === 'sm' ? 'h-5 w-5' : 'h-6 w-6';
  const textSize = size === 'sm' ? 'text-base' : 'text-lg';

  return (
    <Link
      href="/"
      className="flex items-center gap-2 transition-opacity hover:opacity-80"
    >
      <FlaskConical className={cn(iconSize, 'text-primary')} />
      {showText && (
        <span className={cn(textSize, 'font-semibold text-foreground')}>
          Template
        </span>
      )}
    </Link>
  );
}
