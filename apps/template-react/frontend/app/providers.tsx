'use client';

// CRITICAL: Inject mock data BEFORE any Telegram SDK imports
// The @telegram-apps/sdk freezes window.Telegram.WebApp on import
// Use platform-mock which doesn't import the SDK
import {
  initPlatformMock,
  injectMockInitData,
  isMockModeEnabled,
  getSelectedMockUser,
} from '@tma-platform/core-react/platform-mock';
import { MOCK_USERS } from '@/config/mock-users';

// Initialize mock IMMEDIATELY before any SDK imports
initPlatformMock(MOCK_USERS);
if (isMockModeEnabled()) {
  let selectedUser = getSelectedMockUser();
  if (!selectedUser?.user_id || !selectedUser.username) {
    console.warn('[Mock] Invalid user in localStorage, using default');
    selectedUser = MOCK_USERS[0] ?? null;
  }
  if (selectedUser) {
    injectMockInitData(selectedUser);
    console.log('[Mock] Injected initData for user:', selectedUser.username);
  }
}

// Now safe to import modules that use Telegram SDK
import {
  Component,
  useEffect,
  type PropsWithChildren,
  type ReactNode,
} from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { initPostHog } from '@tma-platform/core-react/analytics';
import { isApiError } from '@tma-platform/core-react/errors';
import { SDKProvider } from '@tma-platform/core-react/platform';
import { ThemeProvider } from 'next-themes';

import { AppInitProvider, useAppInit } from '@/providers';
import { DebugPanel } from '@/components/debug/debug-panel';
import { ErrorScreen } from '@/components/ErrorScreen';
import { LoadingScreen } from '@/components/LoadingScreen';
import { ResponsiveToaster } from '@/components/responsive-toaster';
import { configureApiClient } from '@/config/kubb-config';
import { useAppTheme } from '@/hooks/useAppTheme';
import { initSentry } from '@/lib/sentry';

// Debug: Log immediately when module loads
console.log('[Providers] Module loading...', { timestamp: Date.now() });

// Configure API client IMMEDIATELY (before any API calls)
configureApiClient();
console.log('[Providers] API client configured');

// Initialize Sentry (after configureApiClient)
initSentry();

// Create QueryClient instance with smart retry logic
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
      // Smart retry based on error classification
      retry: (failureCount, error) => {
        // ApiError from our classification system
        if (isApiError(error)) {
          // Don't retry non-recoverable errors (4xx client errors)
          if (!error.recoverable) return false;

          // Retry recoverable errors (5xx, network) up to 3 times
          return failureCount < 3;
        }

        // Unknown errors: retry once
        return failureCount < 1;
      },
      // Exponential backoff with max 30 seconds
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
    },
    mutations: {
      // Don't retry mutations by default (user can retry manually)
      retry: false,
    },
  },
});

/**
 * Error boundary to catch React errors
 */
class ErrorBoundary extends Component<
  { children: ReactNode; fallback: (error: Error) => ReactNode },
  { error: Error | null }
> {
  constructor(props: {
    children: ReactNode;
    fallback: (error: Error) => ReactNode;
  }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error boundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.error) {
      return this.props.fallback(this.state.error);
    }
    return this.props.children;
  }
}

/**
 * Syncs the Telegram header color with the app's theme.
 * Must be inside ThemeProvider to access theme context.
 */
function TelegramThemeSync() {
  // This hook syncs Telegram header color with app's CSS background color
  // whenever the theme changes (light/dark/system)
  useAppTheme();
  return null;
}

/**
 * Content wrapper that shows loading/error states based on app init
 * Note: SDKProvider is now at root level so ready() is called immediately
 */
function AppContent({ children }: PropsWithChildren) {
  const { error, isLoading } = useAppInit();

  console.log('[AppContent] Render', { isLoading, hasError: !!error, timestamp: Date.now() });

  // Show error screen
  if (error) {
    console.log('[AppContent] Showing error screen:', error.message);
    return <ErrorScreen error={error} />;
  }

  // Show loading screen while initializing
  // Note: For web users not yet authenticated, isReady=false but isLoading=false
  // They'll see the app content (which includes login UI)
  if (isLoading) {
    console.log('[AppContent] Showing loading screen (waiting for AppInit)');
    return <LoadingScreen />;
  }

  // Render app (either authenticated or showing login UI)
  console.log('[AppContent] Rendering children');
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <TelegramThemeSync />
      <ResponsiveToaster toastOptions={{ duration: 4000 }} />
      <DebugPanel />
      {children}
    </ThemeProvider>
  );
}

/**
 * Root providers for the application
 *
 * Handles:
 * - SDK initialization (SDKProvider) - FIRST to call ready() immediately
 * - QueryClient setup
 * - App initialization (AppInitProvider) - auth and API calls
 * - Theme management (ThemeProvider)
 * - Error boundaries
 *
 * IMPORTANT: SDKProvider must be at root level so miniApp.ready() is called
 * immediately when the app loads, not after waiting for API calls.
 * This prevents Telegram from timing out and causing infinite reload loops.
 */
export function Providers({ children }: PropsWithChildren) {
  console.log('[Providers] Component mounting...', { timestamp: Date.now() });

  useEffect(() => {
    console.log('[Providers] useEffect running');

    // Initialize Eruda in debug mode (for mobile debugging)
    if (process.env.NEXT_PUBLIC_DEBUG === 'true') {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/eruda';
      script.onload = () => {
        (window as { eruda?: { init: () => void } }).eruda?.init();
        console.log('[Eruda] Mobile debugger initialized');
      };
      document.body.appendChild(script);
    }

    // Initialize PostHog on client-side only
    const apiKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    const host = process.env.NEXT_PUBLIC_POSTHOG_HOST;

    if (apiKey) {
      initPostHog(apiKey, {
        api_host: host ?? 'https://app.posthog.com',
        autocapture: false,
        capture_pageview: false,
        disable_session_recording: true,
      });
    }
  }, []);

  return (
    <ErrorBoundary fallback={(error) => <ErrorScreen error={error} />}>
      <SDKProvider>
        <QueryClientProvider client={queryClient}>
          <AppInitProvider>
            <AppContent>{children}</AppContent>
          </AppInitProvider>
        </QueryClientProvider>
      </SDKProvider>
    </ErrorBoundary>
  );
}
