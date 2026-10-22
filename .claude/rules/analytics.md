---
paths:
  - "**/analytics/**"
  - "**/*analytics*.{ts,py}"
  - "**/*posthog*"
  - "docs/ANALYTICS_CATALOG.md"
---

# Analytics — PostHog events

Product analytics is PostHog (optional: with no key configured, captures are no-ops). This is the
**convention** doc — the one rule that keeps analytics from rotting, plus where events live and how to check
that one fires. Keep the event list itself (the registry of record) in **`docs/ANALYTICS_CATALOG.md`**;
create it with your first event.

## The rule (this is the whole point)

**Every time you add, rename, or remove a `posthog.capture(...)` call, update
`docs/ANALYTICS_CATALOG.md` in the same change.** New event → add a row under the
right section with its properties, file, and trigger. Renamed → rename the row.
Removed → move it to "Deprecated Events". No silent events.

An undocumented event is a bug: nobody can build a funnel or dashboard on a name
they can't find, and you can't tell "feature unused" from "feature never shipped".

This applies equally to **backend** captures (`PostHogWrapper.capture(...)`).

## Naming & properties

- **Event name:** `lower_snake_case`, `noun_verb` past-ish (`paywall_shown`,
  `payment_succeeded`, `subscription_cancel_confirmed`). Group by the
  prefix that already exists (`paywall_*`, `payment_*`).
- **Properties:** flat, `snake_case`, primitives or shallow arrays. Suffix units
  (`time_spent_ms`). Keep the same property keys across related
  events so funnels line up.
- **No PII in event names/props.** Identity is the person (`distinct_id`), not a
  property — see Identity below.
- Catalog row format:
  `| `event_name` | `prop_a`, `prop_b` (notes) | `File.vue` | When it fires |`

## Where events live

| Side | How you capture | Catalog section |
|------|-----------------|-----------------|
| **Vue frontend** | `const { posthog } = usePostHog()` from `@core/analytics`, then `posthog.capture('name', { ... })` | "Frontend Events" |
| **React frontend** | `usePostHog()` from `@tma-platform/core-react/analytics` → `posthog.capture(...)` | "Frontend Events" |
| **Backend** | inject the `PostHogWrapper` singleton (`core/.../infrastructure/posthog.py`), `posthog.capture(distinct_id, 'name', { ... })` | "Backend Events" |

Core already captures some backend events (e.g. payment success/failure from the payments service and the
renewal job); list them in your catalog too.

Pair with `seen_features` when an event gates a one-time UI moment: gate the
*show* on `seen_features`, capture the *impression* to PostHog (see
`.claude/rules/seen-features.md`).

## Identity (so events attribute to a real person)

Frontend calls `posthog.identify(String(user.id))` (UUID) on app init
(`useAppInit.ts` / `AppInitProvider.tsx`). Backend captures pass `distinct_id=str(user.id)`; broadcast/
system events use `distinct_id="system"`. Don't invent a new id scheme. When the frontend build defines
`VITE_APP_VERSION`, core registers it as the `$app_version` super property, the same key the backend sends,
so funnels split by release on both sides.

## Checking that an event fires

Put a **personal** API key (`phx_…`, read scopes) and your project id in a gitignored `scripts/.env`
(`POSTHOG_PERSONAL_API_KEY`, `POSTHOG_PROJECT_ID`, `POSTHOG_HOST`, e.g. `https://eu.posthog.com`). Quick
HogQL check after shipping; zero rows over a busy window means it isn't firing (not deployed / not
rendering), not "users declined":

```bash
set -a && . scripts/.env && set +a
curl -s -X POST -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  -H "Content-Type: application/json" \
  "$POSTHOG_HOST/api/projects/$POSTHOG_PROJECT_ID/query/" \
  -d '{"query":{"kind":"HogQLQuery","query":"select count() from events where event = '\''your_event'\'' and timestamp > now() - interval 7 day"}}'
```

Gotchas:
- Don't add a date window unless you mean one.
- Frontend errors arrive as `frontend_error`, not `$exception`.
- A property can't be deleted from already-stored events through the API, only in the PostHog UI.

## Checklist when touching analytics

1. Capture with the right `distinct_id`, grouped name, flat props.
2. Add/update the row in `docs/ANALYTICS_CATALOG.md`.
3. After deploy, HogQL-check the event fires (above).
