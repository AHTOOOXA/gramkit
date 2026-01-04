'use client';

import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { Toaster, type ToasterProps } from 'sonner';

const DESKTOP_BREAKPOINT = 768;

export function ResponsiveToaster(props: Omit<ToasterProps, 'position' | 'theme'>) {
  const { resolvedTheme } = useTheme();
  const [position, setPosition] = useState<ToasterProps['position']>('top-center');

  useEffect(() => {
    const updatePosition = () => {
      setPosition(window.innerWidth >= DESKTOP_BREAKPOINT ? 'bottom-right' : 'top-center');
    };

    updatePosition();
    window.addEventListener('resize', updatePosition);
    return () => { window.removeEventListener('resize', updatePosition); };
  }, []);

  return (
    <Toaster
      position={position}
      theme={(resolvedTheme as 'light' | 'dark' | undefined) ?? 'light'}
      {...props}
    />
  );
}
