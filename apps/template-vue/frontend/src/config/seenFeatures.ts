/**
 * `seen_features` registry: the single source of truth for one-time UI reveals,
 * coachmarks, "what's new" notes and capped nudges.
 *
 * Keys are opaque to the backend; their meaning lives here. Pick a kind, then
 * consume the key through the matching composable from `@app/composables/useSeenFeatures`
 * (built by `createSeenFeatures` in `@core/composables`):
 *   - `oneShot`   → useReveal   (show once, until dismissed)
 *   - `versioned` → useWhatsNew (show when the content version advances)
 *   - `capped`    → useNudge    (show up to N times with a cooldown, until acted on)
 *
 * Declaring a key here surfaces NOTHING on its own: a feature is only "enabled"
 * once a component renders gated on its composable.
 *
 * Conventions:
 *   - Key grammar: dotted lowercase, `kind.feature[.variant]` (enforced server-side).
 *   - Gating state only: not preferences (real columns) and not analytics (PostHog).
 *   - Keys are forever: mark a retired key here, never reuse a name with a new meaning.
 *   - The shared GUEST user (every logged-out web visitor) never reads or writes:
 *     the store reports not-loaded and the endpoint answers 403.
 */

import type { SeenFeatureConfig } from '@core/composables';

export const SEEN_FEATURES = {
  // The "what's new" note on /demo (components/demo/WhatsNewNote.vue).
  'whatsnew.demo': { kind: 'versioned' },
  // Examples of the other two kinds:
  // 'reveal.profile_tab': { kind: 'oneShot' },
  // 'nudge.push_optin': { kind: 'capped', maxShows: 3, cooldownDays: 7 },
} as const satisfies Record<string, SeenFeatureConfig>;

export type FeatureKey = keyof typeof SEEN_FEATURES;
