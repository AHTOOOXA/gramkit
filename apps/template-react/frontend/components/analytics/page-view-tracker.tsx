'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { usePostHog } from '@tma-platform/core-react/analytics';

/**
 * PageView tracking component.
 * Captures PostHog $pageview event on route changes.
 */
export function PageViewTracker() {
  const pathname = usePathname();
  const posthog = usePostHog();

  useEffect(() => {
    if (pathname) {
      posthog.capture('$pageview', { path: pathname });
    }
  }, [pathname, posthog]);

  return null;
}
