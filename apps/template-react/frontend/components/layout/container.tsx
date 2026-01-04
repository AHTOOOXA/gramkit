import type { PropsWithChildren } from 'react';

import { cn } from '@/lib/utils';

interface ContainerProps extends PropsWithChildren {
  className?: string;
}

export function Container({ children, className }: ContainerProps) {
  return (
    <div
      className={cn('container mx-auto max-w-screen-2xl px-4 py-6', className)}
    >
      {children}
    </div>
  );
}
