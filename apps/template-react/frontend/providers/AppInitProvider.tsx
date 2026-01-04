'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type PropsWithChildren,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { useTelegram } from '@tma-platform/core-react/platform';
import { usePostHog } from '@tma-platform/core-react/analytics';
import { useRouter } from '@/i18n/navigation';
import {
  getCurrentUserUsersMeGetQueryKey,
  getSubscriptionSubscriptionsGetQueryKey,
} from '@/src/gen/hooks';
import { processStartProcessStartPost } from '@/src/gen/client/processStartProcessStartPost';
import { getSubscriptionSubscriptionsGet } from '@/src/gen/client/getSubscriptionSubscriptionsGet';
import type { UserSchema, StartMode } from '@/src/gen/models';

// ============================================================================
// Types
// ============================================================================

interface AppInitState {
  /** App is fully initialized and ready */
  isReady: boolean;
  /** Currently loading/initializing */
  isLoading: boolean;
  /** Current authenticated user (null if not authenticated) */
  user: UserSchema | null;
  /** Error during initialization */
  error: Error | null;
}

interface AppInitContextValue extends AppInitState {
  /**
   * Trigger re-initialization after web auth completes.
   * Call this from auth hooks after successful authentication.
   */
  reinitialize: () => void;
}

// ============================================================================
// Context
// ============================================================================

const AppInitContext = createContext<AppInitContextValue | null>(null);

// ============================================================================
// Start Param Parsing (from old useStartParams)
// ============================================================================

enum StartParamKey {
  INVITE = 'i',
  REFERAL = 'r',
  MODE = 'm',
  PAGE = 'p',
}

interface ParsedStartParam {
  type: StartParamKey | null;
  value: string | null;
  rawParam: string | null;
}

function parseStartParam(param: string | undefined): ParsedStartParam {
  if (!param) {
    return { type: null, value: null, rawParam: null };
  }

  // Format: "key_value" (e.g., "i_abc123" for invite code "abc123")
  const parts = param.split('_');
  if (parts.length >= 2) {
    const key = parts[0] as StartParamKey;
    const value = parts.slice(1).join('_');

    if (Object.values(StartParamKey).includes(key)) {
      return { type: key, value, rawParam: param };
    }
  }

  return { type: null, value: null, rawParam: param };
}

function handleModeRouting(mode: string, router: ReturnType<typeof useRouter>) {
  switch (mode) {
    case 'draw':
      router.push('/');
      break;
    case 'settings':
      router.push('/profile');
      break;
    default:
      // Unknown mode, ignore
      break;
  }
}

// ============================================================================
// Module-level state (persists across component remounts)
// ============================================================================

// Track if we've successfully initialized this session
// Using module-level variable because component may remount on locale change
let hasInitializedSession = false;

// ============================================================================
// Provider
// ============================================================================

/**
 * AppInitProvider - Single entry point for app initialization.
 *
 * Handles:
 * - Authentication detection (TMA initData vs web session cookie)
 * - Calling /process_start (admin notification, streak, referral)
 * - PostHog identification with database user_id
 * - Start param parsing and routing (for TMA users)
 * - User data caching
 *
 * Usage:
 * - Wrap your app with this provider
 * - Use useAppInit() hook to access state
 * - Call reinitialize() after web auth completes
 */
export function AppInitProvider({ children }: PropsWithChildren) {
  console.log('[AppInitProvider] Render', { timestamp: Date.now() });

  const queryClient = useQueryClient();
  const posthog = usePostHog();
  const telegram = useTelegram();
  const router = useRouter();

  // Trigger counter - incrementing this causes init to re-run
  const [trigger, setTrigger] = useState(0);

  // Track if init is currently running (to prevent concurrent calls)
  const isInitializing = useRef(false);

  // State
  const [state, setState] = useState<AppInitState>({
    isReady: false,
    isLoading: true,
    user: null,
    error: null,
  });

  // Reinitialize function - exposed to auth hooks
  const reinitialize = useCallback(() => {
    // Reset the module-level flag so init runs again
    hasInitializedSession = false;
    isInitializing.current = false;
    setTrigger((t) => t + 1);
  }, []);

  // Main initialization effect
  // Note: Only depend on `trigger` to prevent unnecessary re-runs
  // Other values are accessed via refs or are stable
  useEffect(() => {
    console.log('[AppInitProvider] useEffect running', { hasInitializedSession, isInitializing: isInitializing.current });

    // Skip if already successfully initialized this session
    // (module-level variable persists across component remounts from locale changes)
    if (hasInitializedSession) {
      console.log('[AppInitProvider] Already initialized, restoring from cache');
      // Restore user from query cache and update state (for remounted component)
      const cachedUser = queryClient.getQueryData<UserSchema>(getCurrentUserUsersMeGetQueryKey());
      setState({
        isReady: true,
        isLoading: false,
        user: cachedUser ?? null,
        error: null,
      });
      return;
    }

    // Skip if already initializing (prevents React Strict Mode double-invoke)
    if (isInitializing.current) {
      console.log('[AppInitProvider] Already initializing, skipping');
      return;
    }

    async function init() {
      console.log('[AppInitProvider] Starting init...');
      isInitializing.current = true;
      setState((s) => ({ ...s, isLoading: true, error: null }));

      try {
        // 1. Detect auth method
        const initDataRaw = telegram.initData;
        const hasTmaAuth = !!initDataRaw;
        console.log('[AppInitProvider] Auth detection', { hasTmaAuth, initDataLength: initDataRaw ? initDataRaw.length : 0 });

        // 2. Parse start params (TMA only)
        let startParamData: ParsedStartParam = { type: null, value: null, rawParam: null };
        let telegramUserId: string | undefined;

        if (hasTmaAuth) {
          const initDataParams = new URLSearchParams(initDataRaw);
          const startParam = initDataParams.get('start_param');
          startParamData = parseStartParam(startParam ?? undefined);

          // Extract telegram user ID for reference
          const userParam = initDataParams.get('user');
          if (userParam) {
            try {
              const userData = JSON.parse(userParam) as { id?: number };
              telegramUserId = userData.id?.toString();
            } catch {
              console.error('[AppInit] Failed to parse user from initData');
            }
          }
        }

        // 3. Build process_start request
        const inviteCode =
          startParamData.type === StartParamKey.INVITE ? startParamData.value : '';
        const referalId =
          startParamData.type === StartParamKey.REFERAL ? startParamData.value : '';
        const modeType =
          startParamData.type === StartParamKey.MODE ? startParamData.value : '';
        const page =
          startParamData.type === StartParamKey.PAGE ? startParamData.value : '';

        // 4. Call /process_start
        // - TMA users: initData sent via header by API client middleware
        // - Web users: session cookie sent automatically
        let result;
        try {
          console.log('[AppInitProvider] Calling /process_start API...');
          const startTime = Date.now();
          result = await processStartProcessStartPost({
            invite_code: inviteCode ?? '',
            referal_id: referalId ?? '',
            mode: modeType ? (modeType as StartMode) : null,
            page: page ?? '',
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          });
          console.log('[AppInitProvider] /process_start succeeded', {
            duration: Date.now() - startTime,
            userId: result.current_user.id
          });
        } catch (err) {
          // 5. Handle errors (Kubb throws on error)
          // Any error (including 401 unauthorized) - user not authenticated
          // This is OK for web users before login - they'll see the login UI
          // After they authenticate and call reinitialize(), this will succeed
          console.error('[AppInitProvider] /process_start FAILED:', err);
          console.log('[AppInitProvider] Setting isLoading=false (unauthenticated)');
          setState({
            isReady: false,
            isLoading: false,
            user: null,
            error: null,
          });
          return;
        }

        // 6. Success! Mark as initialized (module-level for persistence across remounts)
        console.log('[AppInitProvider] Init successful, marking session initialized');
        hasInitializedSession = true;

        const user = result.current_user;

        // 7. PostHog identification with DATABASE id (not Telegram ID)
        if (user.id) {
          posthog.identify(user.id);
          posthog.capture('app_initialized', {
            start_param: startParamData.rawParam,
            param_type: startParamData.type,
            param_value: startParamData.value,
            telegram_id: telegramUserId, // Keep for reference
            auth_method: hasTmaAuth ? 'tma' : 'web',
          });
        }

        // 8. Set user in query cache
        queryClient.setQueryData(getCurrentUserUsersMeGetQueryKey(), user);

        // 9. Handle mode routing (TMA only)
        if (result.mode) {
          handleModeRouting(result.mode, router);
        }

        // 10. Prefetch subscription
        void queryClient.prefetchQuery({
          queryKey: getSubscriptionSubscriptionsGetQueryKey(),
          queryFn: async () => {
            return await getSubscriptionSubscriptionsGet();
          },
        });

        // 11. Handle page parameter (direct navigation)
        if (startParamData.type === StartParamKey.PAGE && startParamData.value) {
          const path = startParamData.value.replace(/_/g, '/');
          router.push(`/${path}`);
        }

        // 12. Update state
        console.log('[AppInitProvider] ✓ Setting isReady=true, isLoading=false');
        setState({
          isReady: true,
          isLoading: false,
          user,
          error: null,
        });
      } catch (err) {
        console.error('[AppInitProvider] Initialization failed:', err);
        setState({
          isReady: false,
          isLoading: false,
          user: null,
          error: err instanceof Error ? err : new Error('Initialization failed'),
        });
      } finally {
        isInitializing.current = false;
      }
    }

    void init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger]);

  const contextValue: AppInitContextValue = {
    ...state,
    reinitialize,
  };

  return (
    <AppInitContext.Provider value={contextValue}>
      {children}
    </AppInitContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook to access app initialization state and trigger re-initialization.
 *
 * Usage in auth hooks:
 * ```typescript
 * const { reinitialize } = useAppInit();
 *
 * // After successful authentication:
 * await verifyCode(...);
 * reinitialize(); // This triggers /process_start, PostHog identify, etc.
 * ```
 */
export function useAppInit(): AppInitContextValue {
  const context = useContext(AppInitContext);

  if (!context) {
    throw new Error('useAppInit must be used within AppInitProvider');
  }

  return context;
}
