import { ref, computed, type ComputedRef } from 'vue';
import { useQueryClient, type QueryClient } from '@tanstack/vue-query';
import { usePlatform } from '@core/platform';
import { usePostHog } from '@core/analytics';
import router from '@app/router/router';
import { StartParamKey } from '@app/types/StartParamKey';
import {
  getCurrentUserUsersMeGetQueryKey,
  getSubscriptionSubscriptionsGetQueryKey,
} from '@gen/hooks';
import { processStartProcessStartPost, getSubscriptionSubscriptionsGet } from '@/gen/client';
import type { UserSchema } from '@/gen/models';
import type { StartMode } from '@/gen/models';

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

type StartParams = Partial<Record<StartParamKey, string>>;

interface ParsedStartParam {
  params: StartParams;
  rawParam: string | null;
}

// ============================================================================
// Module-level state (persists across component remounts)
// ============================================================================

// Track if we've successfully initialized this session
let hasInitializedSession = false;

// Track if init is currently running (to prevent concurrent calls)
let isInitializing = false;

// Reactive state (module-level for singleton pattern)
const state = ref<AppInitState>({
  isReady: false,
  isLoading: true,
  user: null,
  error: null,
});

// ============================================================================
// Start Param Parsing
// ============================================================================

function parseStartParam(param: string | undefined): ParsedStartParam {
  const params: StartParams = {};

  if (!param) {
    return { params, rawParam: null };
  }

  // Format: "key-value-key-value" (e.g., "i-abc123-r-def456")
  const parts = param.split('-');
  for (let i = 0; i < parts.length; i += 2) {
    if (i + 1 < parts.length) {
      const key = Object.entries(StartParamKey).find(([_, value]) => value === parts[i])?.[0];
      if (key) {
        params[StartParamKey[key as keyof typeof StartParamKey]] = parts[i + 1];
      }
    }
  }

  return { params, rawParam: param };
}

function handleModeRouting(mode: string) {
  switch (mode) {
    case 'draw':
      // TODO: redirect to draw
      break;
    case 'keygo':
      void router.push('/keygo');
      break;
    case 'settings':
      void router.push('/profile');
      break;
    default:
      // Unknown mode, ignore
      break;
  }
}

// ============================================================================
// Initialization Logic
// ============================================================================

async function initializeApp(queryClient: QueryClient): Promise<void> {
  // Skip if already successfully initialized this session
  if (hasInitializedSession) {
    // Restore user from query cache and update state
    const cachedUser = queryClient.getQueryData<UserSchema>(getCurrentUserUsersMeGetQueryKey());
    state.value = {
      isReady: true,
      isLoading: false,
      user: cachedUser ?? null,
      error: null,
    };
    return;
  }

  // Skip if already initializing (prevents concurrent calls)
  if (isInitializing) {
    return;
  }

  isInitializing = true;
  state.value = { ...state.value, isLoading: true, error: null };

  const platform = usePlatform();
  const { posthog } = usePostHog();

  try {
    // 1. Detect auth method
    const initDataRaw = platform.webAppInitData;
    const hasTmaAuth = !!initDataRaw;

    // 2. Parse start params (TMA only)
    let startParamData: ParsedStartParam = { params: {}, rawParam: null };
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
    const inviteCode = startParamData.params[StartParamKey.INVITE] ?? '';
    const referalId = startParamData.params[StartParamKey.REFERAL] ?? '';
    const modeType = startParamData.params[StartParamKey.MODE] ?? '';
    const page = startParamData.params[StartParamKey.PAGE] ?? '';

    // 4. Call /process_start
    // - TMA users: initData sent via header by API client middleware
    // - Web users: session cookie sent automatically
    let result;
    try {
      result = await processStartProcessStartPost({
        invite_code: inviteCode,
        referal_id: referalId,
        mode: modeType ? (modeType as StartMode) : null,
        page: page,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
    } catch {
      // 5. Handle errors
      // Any error (including 401 unauthorized) - user not authenticated
      // This is OK for web users before login - they'll see the login UI
      // After they authenticate and call reinitialize(), this will succeed
      state.value = {
        isReady: false,
        isLoading: false,
        user: null,
        error: null,
      };
      return;
    }

    // 6. Success! Mark as initialized
    hasInitializedSession = true;

    const user = result.current_user;

    // 7. PostHog identification with DATABASE id (not Telegram ID)
    if (user.id) {
      posthog.identify(String(user.id));
      posthog.capture('app_initialized', {
        start_param: startParamData.rawParam,
        invite_code: inviteCode || undefined,
        referal_id: referalId || undefined,
        mode: modeType || undefined,
        telegram_id: telegramUserId, // Keep for reference
        auth_method: hasTmaAuth ? 'tma' : 'web',
      });
    }

    // 8. Set user in query cache
    queryClient.setQueryData(getCurrentUserUsersMeGetQueryKey(), user);

    // 9. Handle mode routing (TMA only)
    if (result.mode) {
      handleModeRouting(result.mode);
    }

    // 10. Prefetch subscription
    void queryClient.prefetchQuery({
      queryKey: getSubscriptionSubscriptionsGetQueryKey(),
      queryFn: async () => {
        return await getSubscriptionSubscriptionsGet();
      },
    });

    // 11. Handle page parameter (direct navigation)
    if (page) {
      const path = page.replace(/_/g, '/');
      void router.push(`/${path}`);
    }

    // 12. Update state
    state.value = {
      isReady: true,
      isLoading: false,
      user,
      error: null,
    };
  } catch (err) {
    console.error('[AppInit] Initialization failed:', err);
    state.value = {
      isReady: false,
      isLoading: false,
      user: null,
      error: err instanceof Error ? err : new Error('Initialization failed'),
    };
    throw err; // Re-throw for main.ts to handle
  } finally {
    isInitializing = false;
  }
}

// ============================================================================
// Composable
// ============================================================================

// Store queryClient reference for reinitialize()
let _queryClient: QueryClient | null = null;

/**
 * Initialize the app (call from main.ts before mounting).
 *
 * @param queryClient - The Vue Query client instance
 */
export async function initApp(queryClient: QueryClient): Promise<void> {
  _queryClient = queryClient;
  await initializeApp(queryClient);
}

/**
 * Composable to access app initialization state and trigger re-initialization.
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
export function useAppInit(): {
  isReady: ComputedRef<boolean>;
  isLoading: ComputedRef<boolean>;
  user: ComputedRef<UserSchema | null>;
  error: ComputedRef<Error | null>;
  reinitialize: () => void;
} {
  // Get queryClient from Vue Query context if not already set
  if (!_queryClient) {
    _queryClient = useQueryClient();
  }

  const reinitialize = () => {
    if (!_queryClient) {
      console.error('[AppInit] QueryClient not available for reinitialize');
      return;
    }

    // Reset the module-level flags so init runs again
    hasInitializedSession = false;
    isInitializing = false;

    // Trigger re-initialization
    void initializeApp(_queryClient);
  };

  return {
    isReady: computed(() => state.value.isReady),
    isLoading: computed(() => state.value.isLoading),
    user: computed(() => state.value.user),
    error: computed(() => state.value.error),
    reinitialize,
  };
}
