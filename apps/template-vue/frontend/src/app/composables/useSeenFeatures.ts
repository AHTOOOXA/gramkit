import { computed, type ComputedRef } from 'vue';
import { useQueryClient } from '@tanstack/vue-query';
import {
  createSeenFeatures,
  mergeSeenFeatures,
  type SeenFeaturesMap,
  type SeenFeatureValue,
} from '@core/composables';
import {
  getCurrentUserUsersMeGetQueryKey,
  useGetCurrentUserUsersMeGet,
  useMarkSeenFeaturesUsersMeSeenFeaturesPatch,
} from '@gen/hooks';
import type { UserSchema } from '@/gen/models';
import { SEEN_FEATURES } from '@/config/seenFeatures';
import { useAuth } from './useAuth';

/**
 * seen_features store: per-user "has this user passed this UI moment" state.
 *
 * Backing store is the `seen_features` JSONB map on the user, written through
 * PATCH /users/me/seen-features (an atomic, shallow JSONB merge on the server).
 * Reads come from the /users/me query (not `useAuth().user`, which is a snapshot
 * taken at init and doesn't follow cache writes), so a dismiss hides instantly.
 *
 * The kinds logic is `createSeenFeatures` in core. Prefer the kind composables
 * exported below (useReveal / useWhatsNew / useNudge); reach for `useSeenFeatures`
 * only for bespoke gating.
 *
 * The shared GUEST user (every logged-out web visitor) counts as not loaded:
 * nothing shows and nothing is written (the endpoint answers 403 anyway).
 */

const USER_KEY = getCurrentUserUsersMeGetQueryKey();

export function useSeenFeatures(): {
  loaded: ComputedRef<boolean>;
  features: ComputedRef<SeenFeaturesMap>;
  get: (key: string) => SeenFeatureValue | undefined;
  mark: (patch: SeenFeaturesMap) => void;
} {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const { data: user } = useGetCurrentUserUsersMeGet({
    query: { staleTime: 5 * 60_000, enabled: () => isAuthenticated.value },
  });

  const mutation = useMarkSeenFeaturesUsersMeSeenFeaturesPatch({
    mutation: {
      // Optimistic: mirror the server's shallow merge in the /users/me cache.
      onMutate: async (variables) => {
        await queryClient.cancelQueries({ queryKey: USER_KEY });
        const previous = queryClient.getQueryData<UserSchema>(USER_KEY);
        const patch = variables.data as SeenFeaturesMap | undefined;
        if (previous && patch) {
          queryClient.setQueryData<UserSchema>(USER_KEY, {
            ...previous,
            seen_features: mergeSeenFeatures(previous.seen_features, patch),
          });
        }
        return { previous };
      },
      onError: (_error, _variables, context) => {
        const ctx = context as { previous?: UserSchema } | undefined;
        if (ctx?.previous) queryClient.setQueryData(USER_KEY, ctx.previous);
        // Silent: a failed gating write just shows the moment again next time.
      },
      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: USER_KEY });
      },
    },
  });

  const loaded = computed(() => !!user.value && user.value.user_type !== 'GUEST');
  // GUEST is one row shared by every logged-out visitor: expose nothing, so a custom
  // check reading `get(key)` can't gate on someone else's state.
  const features = computed<SeenFeaturesMap>(
    () => (loaded.value ? (user.value?.seen_features ?? {}) : {}) as SeenFeaturesMap
  );

  return {
    loaded,
    features,
    get: (key: string) => features.value[key],
    mark: (patch: SeenFeaturesMap) => {
      if (!loaded.value) return; // GUEST / no user: never write gating state
      mutation.mutate({ data: patch });
    },
  };
}

export const { useReveal, useWhatsNew, useNudge } = createSeenFeatures(SEEN_FEATURES, useSeenFeatures);
