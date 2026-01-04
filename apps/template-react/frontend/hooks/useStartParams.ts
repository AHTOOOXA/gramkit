'use client';

import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { usePostHog } from '@tma-platform/core-react/analytics';
import { useTelegram } from '@tma-platform/core-react/platform';

import {
  InitDataError,
  InitializationError,
  ProcessStartError,
} from '@/lib/errors';
import { useRouter } from '@/i18n/navigation';
import {
  getCurrentUserUsersMeGetQueryKey,
  getSubscriptionSubscriptionsGetQueryKey,
} from '@/src/gen/hooks';
import { processStartProcessStartPost } from '@/src/gen/client/processStartProcessStartPost';
import { getSubscriptionSubscriptionsGet } from '@/src/gen/client/getSubscriptionSubscriptionsGet';
import type { StartMode } from '@/src/gen/models';
import { StartParamKey, type StartParamData } from '@/types/start-params';

/**
 * Parse start parameter into type and value
 */
function parseStartParam(param: string | undefined): StartParamData {
  if (!param) return { type: null, value: null, rawParam: null };

  // Parse format: key-value (e.g., "i-ABC123", "r-123456", "m-draw", "p-profile")
  const parts = param.split('-');
  if (parts.length >= 2) {
    const key = parts[0];
    const value = parts.slice(1).join('-'); // Join back in case value contains dashes

    // Find matching StartParamKey
    for (const [_, enumValue] of Object.entries(StartParamKey)) {
      if (enumValue === key) {
        return {
          type: enumValue,
          value,
          rawParam: param,
        };
      }
    }
  }

  // No recognized prefix, return raw param as value
  return { type: null, value: param, rawParam: param };
}

/**
 * Handle mode-based routing
 */
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

export function useStartParams() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const posthog = usePostHog();
  const telegram = useTelegram();
  const hasProcessed = useRef(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Only run once
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    async function processStart() {
      setIsLoading(true);
      try {
        // 1. Get initData from Telegram SDK (raw string)
        const initDataRaw = telegram.initData;

        // 2. Validate initData in production (required for authentication)
        if (!initDataRaw && process.env.NODE_ENV === 'production') {
          throw new InitDataError('initData is required in production mode');
        }

        // 3. Parse initData to extract user and start_param
        const initDataParams = new URLSearchParams(initDataRaw);
        const startParam = initDataParams.get('start_param');

        // 4. Extract user from initData (canonical source)
        let userId: string | undefined;
        const userParam = initDataParams.get('user');
        if (userParam) {
          try {
            // URLSearchParams.get() already handles URL decoding
            const userData = JSON.parse(userParam) as { id?: number };
            userId = userData.id?.toString();
          } catch (error) {
            console.error(
              '[useStartParams] Failed to parse user from initData:',
              error
            );
          }
        }

        // 5. Parse param type and value
        const paramData = parseStartParam(startParam ?? undefined);

        // 6. ALWAYS call /process_start (even without start params) - CRITICAL operation
        // Note: initData is sent via header by API client middleware, not in body
        const inviteCode =
          paramData.type === StartParamKey.INVITE ? paramData.value : '';
        const referalId =
          paramData.type === StartParamKey.REFERAL ? paramData.value : '';
        const modeType =
          paramData.type === StartParamKey.MODE ? paramData.value : '';
        const page =
          paramData.type === StartParamKey.PAGE ? paramData.value : '';

        let result;
        try {
          result = await processStartProcessStartPost({
            invite_code: inviteCode ?? '',
            referal_id: referalId ?? '',
            mode: modeType ? (modeType as StartMode) : null,
            page: page ?? '',
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          });
        } catch (error) {
          // Kubb throws on error
          throw new ProcessStartError('Process start failed', error);
        }

        // 7. Set user from backend response
        queryClient.setQueryData(
          getCurrentUserUsersMeGetQueryKey(),
          result.current_user
        );

        // 8. Initialize PostHog with DATABASE id (not Telegram ID)
        // This ensures consistent tracking across all auth methods
        const dbUserId = result.current_user.id;
        if (dbUserId) {
          posthog.identify(dbUserId);
          posthog.capture('app_initialized', {
            start_param: paramData.rawParam,
            param_type: paramData.type,
            param_value: paramData.value,
            telegram_id: userId,  // Keep for reference
          });
        }

        // 9. Handle mode routing from backend response
        if (result.mode) {
          handleModeRouting(result.mode, router);
        }

        // 10. Prefetch subscription
        await queryClient.prefetchQuery({
          queryKey: getSubscriptionSubscriptionsGetQueryKey(),
          queryFn: async () => {
            return await getSubscriptionSubscriptionsGet();
          },
        });

        // 11. Handle page parameter (direct navigation)
        if (paramData.type === StartParamKey.PAGE && paramData.value) {
          const path = paramData.value.replace(/_/g, '/');
          router.push(`/${path}`);
          return; // Exit early after navigation
        }

        // 12. Mark initialization complete
        setIsInitialized(true);
        setError(null);
      } catch (err) {
        // Log for debugging
        console.error('[useStartParams] Initialization failed:', err);

        // Re-throw to propagate error
        if (err instanceof ProcessStartError || err instanceof InitDataError) {
          setError(err);
          setIsInitialized(false);
          throw err;
        }

        // Wrap unknown errors
        const wrappedError = new InitializationError(
          'Failed to initialize app',
          err
        );
        setError(wrappedError);
        setIsInitialized(false);
        throw wrappedError;
      } finally {
        setIsLoading(false);
      }
    }

    void processStart();
  }, [router, queryClient, posthog, telegram]);

  return { isInitialized, error, isLoading };
}
