'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

import { useAppTheme } from '@/hooks/useAppTheme';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const { resolvedTheme, applyTheme } = useAppTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  const toggleTheme = () => {
    applyTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  };

  return (
    <Button variant="outline" size="icon" onClick={toggleTheme}>
      <Sun className="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
      <Moon className="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
