import { computed, type ComputedRef } from 'vue';

/**
 * seen_features: generic per-user "has this user passed this UI moment" state.
 *
 * Backing store is the `seen_features` JSONB map on the user, written through the
 * dedicated PATCH /users/me/seen-features endpoint (atomic, shallow JSONB merge).
 * Reads ride the app's /users/me query cache and update optimistically.
 *
 * This file holds the app-independent half: the value/config types and the three
 * kinds. Each app supplies the other half:
 *   - a key registry (`config/seenFeatures.ts`): `{ 'reveal.profile_tab': { kind: 'oneShot' }, ... }
 *     as const satisfies Record<string, SeenFeatureConfig>`;
 *   - a store composable (`useSeenFeatures`) that reads `user.seen_features` from its
 *     /users/me query and PATCHes through its generated hook (see `SeenFeaturesStore`).
 * Then: `export const { useReveal, useWhatsNew, useNudge } = createSeenFeatures(SEEN_FEATURES, useSeenFeatures);`
 *
 * Kinds (pick one per key, consume it through the matching composable):
 *   - `oneShot`   → useReveal   (show once, until dismissed)
 *   - `versioned` → useWhatsNew (show when the content version advances)
 *   - `capped`    → useNudge    (show up to N times with a cooldown, until acted on)
 *
 * Conventions:
 *   - Declaring a key surfaces nothing on its own; a component must render gated on its composable.
 *   - Key grammar: dotted lowercase, `kind.feature[.variant]` (enforced server-side).
 *   - Gating state only: not preferences (real columns) and not analytics (events).
 *   - Keys are forever: retire a key in the registry, never reuse a name with a new meaning.
 *   - The shared GUEST user (every logged-out web visitor) never reads or writes.
 */

/** Registry entry: pick a kind, consume through the matching composable. */
export type SeenFeatureConfig =
  | { kind: 'oneShot' }
  | { kind: 'versioned' }
  | { kind: 'capped'; maxShows: number; cooldownDays: number };
export type SeenFeatureKind = SeenFeatureConfig['kind'];
export type SeenFeatureRegistry = Record<string, SeenFeatureConfig>;

/**
 * Non-`true` value shape; a key only uses the fields its kind needs.
 * The client kinds write `ack: 'accepted' | 'dismissed'`; server-owned keys may store other strings.
 */
// A `type`, not an `interface`: only type aliases are assignable to the generated
// `SeenFeaturesPatch` index signature.
export type SeenFeatureRecord = {
  v?: number;
  n?: number;
  at?: string;
  ack?: string;
};
export type SeenFeatureValue = true | SeenFeatureRecord;
export type SeenFeaturesMap = Record<string, SeenFeatureValue>;

/** Keys of `R` whose configured kind is `K`. */
export type SeenFeatureKeyOf<R extends SeenFeatureRegistry, K extends SeenFeatureKind> = {
  [P in keyof R & string]: R[P]['kind'] extends K ? P : never;
}[keyof R & string];

/**
 * What the app's store composable (its own `useSeenFeatures`) returns. Extra members are fine.
 * `loaded` must be false for the shared GUEST user; then `features` must be `{}` and `mark` must do nothing.
 */
export interface SeenFeaturesStore {
  loaded: ComputedRef<boolean>;
  features: ComputedRef<SeenFeaturesMap>;
  mark: (patch: SeenFeaturesMap) => void;
}

/**
 * Client mirror of the server's shallow JSONB `||` (for the optimistic /users/me cache write):
 * top-level keys from `patch` replace those in `current` whole.
 */
export function mergeSeenFeatures(
  current: Record<string, unknown> | null | undefined,
  patch: SeenFeaturesMap
): Record<string, unknown> {
  return { ...(current ?? {}), ...patch };
}

export interface SeenFeatureComposables<R extends SeenFeatureRegistry> {
  /** One-shot reveal / coachmark: shows until dismissed once, then never again. */
  useReveal(key: SeenFeatureKeyOf<R, 'oneShot'>): {
    show: ComputedRef<boolean>;
    dismiss: () => void;
  };
  /** Versioned "what's new": shows when `currentVersion` exceeds the last seen version. */
  useWhatsNew(
    key: SeenFeatureKeyOf<R, 'versioned'>,
    currentVersion: number
  ): { show: ComputedRef<boolean>; dismiss: () => void };
  /**
   * Capped nudge: shows up to `maxShows` times with a `cooldownDays` gap between
   * shows, and stops once the user accepts or dismisses. Call `recordShown()` when
   * you actually display it; `accept()` / `dismiss()` on the user's choice.
   */
  useNudge(key: SeenFeatureKeyOf<R, 'capped'>): {
    show: ComputedRef<boolean>;
    recordShown: () => void;
    accept: () => void;
    dismiss: () => void;
  };
}

const daysSince = (iso: string): number => (Date.now() - new Date(iso).getTime()) / 86_400_000;

/**
 * Build the kind composables for an app's registry and store.
 * Doesn't call `useStore` here; each composable calls it at component setup,
 * so this is safe at module scope.
 */
export function createSeenFeatures<R extends SeenFeatureRegistry>(
  registry: R,
  useStore: () => SeenFeaturesStore
): SeenFeatureComposables<R> {
  function useReveal(key: SeenFeatureKeyOf<R, 'oneShot'>) {
    const { loaded, features, mark } = useStore();
    return {
      show: computed(() => loaded.value && features.value[key] !== true),
      dismiss: () => mark({ [key]: true }),
    };
  }

  function useWhatsNew(key: SeenFeatureKeyOf<R, 'versioned'>, currentVersion: number) {
    const { loaded, features, mark } = useStore();
    const show = computed(() => {
      if (!loaded.value) return false;
      const val = features.value[key];
      const seen = typeof val === 'object' && val.v != null ? val.v : 0;
      return seen < currentVersion;
    });
    return { show, dismiss: () => mark({ [key]: { v: currentVersion } }) };
  }

  function useNudge(key: SeenFeatureKeyOf<R, 'capped'>) {
    const { loaded, features, mark } = useStore();
    const cfg = registry[key] as Extract<SeenFeatureConfig, { kind: 'capped' }>;

    const record = computed<SeenFeatureRecord>(() => {
      const val = features.value[key];
      return typeof val === 'object' ? val : {};
    });

    const show = computed(() => {
      if (!loaded.value) return false;
      const r = record.value;
      if (r.ack) return false; // already accepted / dismissed
      if ((r.n ?? 0) >= cfg.maxShows) return false; // hit the show cap
      if (r.at && daysSince(r.at) < cfg.cooldownDays) return false; // still cooling down
      return true;
    });

    // Record-valued keys are replaced whole (the server merge is shallow), so send the full value.
    return {
      show,
      recordShown: () =>
        mark({ [key]: { ...record.value, n: (record.value.n ?? 0) + 1, at: new Date().toISOString() } }),
      accept: () => mark({ [key]: { ...record.value, ack: 'accepted' } }),
      dismiss: () => mark({ [key]: { ...record.value, ack: 'dismissed' } }),
    };
  }

  return { useReveal, useWhatsNew, useNudge };
}
