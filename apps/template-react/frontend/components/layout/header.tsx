'use client';

import { ThemeToggle } from '@/components/shared/theme-toggle';

interface HeaderProps {
  title: string;
}

export function Header({ title }: HeaderProps) {
  return (
    <header className="border-border/40 bg-background/95 supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50 w-full border-b backdrop-blur">
      <div className="container flex h-14 max-w-screen-2xl items-center">
        <div className="mr-4 flex flex-1">
          <h1 className="text-lg font-semibold">{title}</h1>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
