---
paths:
  - "**/seenFeatures.ts"
  - "**/useSeenFeatures.ts"
  - "core/backend/src/core/services/users.py"
  - "core/backend/src/core/infrastructure/fastapi/routers/users.py"
---

# seen_features — feature reveals, coachmarks, nudges & "what's new"

Generic per-user **"has this user passed this UI moment"** state. One backend
primitive (a JSONB map on the core `User`) powers every one-time reveal,
first-run coachmark, versioned "what's new" prompt, and cooldown nudge — so
each new one is frontend-only, no schema/endpoint work.

```
Component  ──useReveal/useWhatsNew/useNudge──▶  user.seen_features (read, reactive)
   │                                                      ▲
   └── dismiss()/accept()/recordShown() ──▶ PATCH /users/me/seen-features
                                              (atomic JSONB `||` merge)
```

## What it is — and isn't

- **Is:** idempotent gating state. Answers one question at render time: *show this or not?*
- **vs PostHog:** PostHog logs *that* it was shown (events) and A/B *who's* eligible (flags); `seen_features` decides *whether* to show, deterministically and offline-tolerant. Pair them: gate on `seen_features`, capture the impression to PostHog.
- **vs preferences:** notification settings / locale / theme are durable prefs → real columns. If a user would look for it in Settings, it doesn't go here.
- **Gating state only.** Not a generic KV store. Keep blobs out.

## Data model (core)

`User.seen_features` — `JSONB NOT NULL DEFAULT '{}'`
(`core/.../database/models/users.py`). Exposed read-only on `UserSchema`.

Value shape — a scalar for the common case, a shallow record for the rest. A
given key only ever uses the fields its kind needs:

```ts
type FeatureValue =
  | true                                                   // one-shot: seen/done
  | { v?: number;                                          // versioned: last-seen version
      n?: number; at?: string;                             // capped: shown count + last-shown ISO
      ack?: 'accepted' | 'dismissed' }                     // outcome
```

## The three kinds

| Kind | Composable | Value | Behavior |
|------|-----------|-------|----------|
| `oneShot` | `useReveal(key)` | `true` | Show until dismissed once, then never. |
| `versioned` | `useWhatsNew(key, currentVersion)` | `{ v }` | Show when `currentVersion` > last-seen `v`. |
| `capped` | `useNudge(key)` | `{ n, at, ack }` | Show up to `maxShows` times, `cooldownDays` apart, until `accept()`/`dismiss()`. |

`acknowledged` (acted vs dismissed) folds into `capped`'s `accept`/`dismiss`.
Milestone celebrations are `oneShot` with a dynamic key (e.g. `celebrate.streak.7`).

## The one correctness rule: merge in SQL, never read-modify-write

The repo writes `seen_features = seen_features || :patch` in a **single UPDATE**
(`merge_seen_features`, `core/.../repo/users.py`). Top-level keys merge
atomically, so concurrent writes to **different keys never lose updates**;
same-key writes are last-writer-wins.

- `||` is a **shallow** (top-level) merge. Record-valued keys are replaced
  wholesale — callers send the **full value**, not a partial. The composables
  already do this.
- The frontend optimistic update mirrors this exact top-level merge into the
  `/users/me` cache (`useSeenFeatures.ts`).

Do **not** route `seen_features` through the generic `update_user` (it does a
full-column overwrite → lost updates). Use the dedicated endpoint.

## How to add a reveal/nudge (frontend-only)

The templates ship the backend half only. The first time an app needs a reveal, run `make schema` (to get
the `useMarkSeenFeaturesUsersMeSeenFeaturesPatch` hook) and add two small files: a typed registry
`src/config/seenFeatures.ts` and a `useSeenFeatures.ts` composable/hook exposing `useReveal` / `useWhatsNew` /
`useNudge`, which read `user.seen_features` from the `/users/me` query and PATCH through the generated hook with
an optimistic top-level merge into that cache. Then:

1. Add a key + kind to the registry `src/config/seenFeatures.ts`:
   ```ts
   export const SEEN_FEATURES = {
     'reveal.profile_tab': { kind: 'oneShot' },
     'whatsnew.dashboard': { kind: 'versioned' },
     'nudge.push_optin': { kind: 'capped', maxShows: 3, cooldownDays: 7 },
   } as const satisfies Record<string, FeatureConfig>;
   ```
   Key grammar: dotted lowercase `kind.feature[.variant]` (enforced server-side).
2. Gate your component on the matching composable:
   ```ts
   const { show, dismiss } = useReveal('reveal.profile_tab');
   function onClose(accepted: boolean) {
     posthog.capture(accepted ? 'profile_tab_reveal_accepted' : 'profile_tab_reveal_dismissed'); // impression
     dismiss();                                                            // gating state
   }
   ```
   `<Dialog :open="show" @close="onClose(false)">…</Dialog>`

After that, each new reveal is frontend-only. The column, endpoint, and validation are generic.

## Backend surface (already built — reference)

- `PATCH /users/me/seen-features` — body is a shallow `feature_key -> value`
  map (`SeenFeaturesPatch`), returns the updated `UserSchema`.
- Hardened (user-writable): keys must match `^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$`,
  ≤ 20 keys/request, values at most one level deep.
- Server-side targeting (e.g. push "what's new" to users who haven't seen it):
  `WHERE NOT (seen_features ? :key)`. Add a `GIN (seen_features jsonb_path_ops)`
  index **only** when such a query actually exists.

## Conventions & gotchas

- **Keys are forever** — data lingers after a reveal is retired; mark dead keys
  in the registry, never reuse a name with new meaning.
- **QA reset** — there's no UI to clear a user's `seen_features` yet; wire a reset
  into the admin/debug user-chooser before testing reveals at scale (otherwise
  each test needs a fresh user).
- **Politeness** — consider a "max one reveal per session" client governor so
  several features don't all fire on day one.
- **Anonymous web users** without a user row → fall back to `localStorage` (a
  storage adapter behind the same composables).

## Cross-app note

The column + endpoint live in **core**, so every app inherits the model field —
and each app's **database** needs the column (`make migration` + `make upgrade`)
before it runs. Both templates ship that migration; an app copied from an older
template needs its own.

## Key files

- Backend: `core/.../models/users.py`, `core/.../schemas/users.py`
  (`SeenFeaturesPatch`), `core/.../repo/users.py` (`merge_seen_features`),
  `core/.../services/users.py`, `core/.../fastapi/routers/users.py`.
- Frontend (per app, once added): `src/config/seenFeatures.ts` (registry),
  `useSeenFeatures.ts` (composable/hook).
