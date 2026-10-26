---
paths:
  - "**/*.vue"
  - "apps/template-vue/frontend/src/**"
  - "core/frontend/**"
---

# Vue apps (`template-vue` and apps copied from it, `core/frontend`)

Stack: Vue 3 `<script setup lang="ts">`, TanStack Vue Query + Kubb, Pinia, shadcn-vue on `reka-ui`,
Tailwind v4 + `tailwindcss-motion`, `vue-i18n`, `vue-sonner`. The API layer (`make schema`, generated hooks, query
keys, `apiFetch`) is covered in `.claude/rules/frontend-api.md`. The always-on rules are in root `CLAUDE.md`.

If your app has its own design system (a `DESIGN.md`, typography roles in `src/style.css`), it wins over the
baseline styling notes below.

## Layout of `apps/<app>/frontend/src/`
```
gen/                       Kubb output (hooks/, client/, models/): don't edit
components/ui/             shadcn-vue components + animation/ (Animate, Stagger, ScrollReveal)
config/kubb-config.ts      API client setup, apiFetch, getSocketOptions
lib/                       utils.ts (cn), errors.ts, sentry.ts
style.css                  Tailwind v4 entry, @theme tokens, layout CSS vars
app/composables/           use* composables (useUpdateUser, useAuth, useLogout, useAppInit…)
app/store/                 Pinia, client/flow state only
app/presentation/screens/  routed pages;  app/presentation/components/  app components
app/router/  app/i18n/locales/{en,ru}.json  app/config/
```
Aliases: `@/` = `src/`, `@app/` = `src/app/`, `@gen/` = `src/gen/`, and `@core/` = `core/frontend/src/`.

## Core imports
- The apps really use `@core/platform` (`usePlatform`, `useTelegram`, the mock helpers), `@core/errors`,
  `@core/analytics` (`usePostHog`; see `.claude/rules/analytics.md`), `@core/services` (`useStatic()`, which
  builds backend `/static/...` URLs), `@core/platform-mock`, `@core/injection-keys` and
  `@core/types/language`.
- `core/frontend/src/api` (openapi-fetch) and `core/frontend/src/ui` are never imported by an app. Don't build on
  them. Use the app's generated hooks and the app's own composables. `@core/composables` is: `useAdminList`,
  `useCsvExport` (admin lists), `groupOverviewCards` / `deltaPct` (admin Overview cards) and `createSeenFeatures`
  (seen_features kinds); the other composables there are unused.
- `core/` never imports from an app. If 2+ apps need a piece of Vue code, it goes in `core/frontend/src/`.

## Generated hooks in Vue: keep them reactive
- Hook params and `query` options accept refs and getters (`MaybeRefOrGetter`). Pass a **getter** so the
  query follows state. A plain value is read once at setup and never changes:
  ```ts
  useGetItemDetailDemoItemsItemIdGet(() => id.value, { query: { enabled: () => !!id.value } })  // ✅
  useX(id.value ? { id: id.value } : undefined, { query: { enabled: !!id.value } })    // ❌ frozen at setup
  ```
- Results are refs: `data.value` in `<script>`, auto-unwrapped in the template.
- Keep server data in the query result, and derive from it with `computed`. Don't copy it into a Pinia store
  or a `ref`.

## Client state
- `ref()` for local state, and Pinia (`src/app/store/`) only for UI or flow state that several screens share
  (template-vue's only store is `theme.ts`). A multi-step form may keep its draft in a store, but the API data
  it shows still comes from the generated query hook.
- When the user does something (save, change a setting), run it from an event handler, not from a `watch`
  on the model.

## Components and UI
- shadcn-vue lives in **`src/components/ui/`**. template-vue has: alert, avatar, badge, button, card,
  checkbox, dialog, dropdown-menu, input, label, progress, select, separator, sheet, skeleton, tabs,
  textarea (+ `animation/`). Check that a component exists before you import it, and add missing ones with the
  shadcn-vue CLI. There is no tooltip, popover, switch, form or toast component. For toasts, import
  `toast` from `vue-sonner` (the `<Toaster>` is mounted in `App.vue`).
- Pages render inside a shell that already pads the content. `app/presentation/components/AppShell.vue` puts
  `px/py-[var(--page-padding-*)]` on `<main>` and reserves `--bottom-nav-height`. Read the shell before you add `px-*`/`pt-*` to a page.
- Layout sizes are CSS vars in `src/style.css` (`--header-height`, `--page-padding-x`, `--page-max-width`, and
  `--bottom-nav-height` in template-vue). Use `top-[calc(var(--header-height)+1rem)]`, not `top-14`.
- Colors: use semantic tokens (`bg-card`, `text-muted-foreground`, `border-border`, `bg-primary/10`), never
  `bg-white`/`text-gray-900`. Check both themes.
- Keep en+ru keys in sync (`app/i18n/locales/`).

## Tailwind v4 policy: inline classes, no class dictionaries
- Write utilities inline in the template. Long class lists are intentional: they're visible, IntelliSense
  works, and Prettier sorts them.
- ❌ JS maps of class strings (`hover.lift`, `feedback.pop`) and ❌ `@utility`/`@apply` that only bundles
  existing utilities.
- If you need reuse, make a component: a wrapper with `:class="cn('…', $props.class)"` and a `<slot />`.
- `@utility` is only for CSS that Tailwind lacks (scrollbar hiding, `::selection`, text-stroke).
  Hand-written CSS in `style.css` is only for keyframes, missing properties, and third-party overrides.
- Allowed exceptions: design-system classes defined in `style.css` (e.g. typography roles). `src/lib/animations.ts` (`animationVariants`) only feeds `<Animate variant>`, which nothing uses.
  Don't extend it or import it elsewhere.
- `tailwindcss-intersect` doesn't work with v4. For scroll reveals, use
  `src/components/ui/animation/ScrollReveal.vue` (`delay` in ms for a 0/100/200 stagger, `threshold`,
  `rootMargin`, `triggerOnce`), or `app/composables/useScrollReveal.ts` for custom behavior. Don't hide an LCP element behind a
  scroll reveal.

## Motion performance (applies to every animated screen)
Measure it, don't guess. A mid-range phone is about 4× CPU throttle in Chrome DevTools (Performance panel);
confirm on a real phone.
- Move things between layouts with **FLIP** (jump the layout, animate a transform). Never transition
  `top`/`left`/`width`, because that re-lays out the page every frame.
- For multi-step motion, use **dense sampled keyframes with linear easing**, not 4–5 keyframes. Window each
  oscillation to exactly 0 at its last keyframe, and bound it by design rather than raw physics.
- A new animation on the same element replaces the running one (a jerk). Use WAAPI `composite: 'add'` so
  they blend.
- **No per-frame DOM writes.** Session recorders and MutationObservers pay for every attribute change, and a
  custom property on a container restyles its whole subtree. Write per-frame values into a CSSOM rule
  (`sheet.cssRules[i].style.x = …`).
- Don't run idle rAF loops. Pause CSS loops and effects while they're off screen (IntersectionObserver).
- Use GPU look-alikes: a gradient overlay instead of `mask-image` over motion, plain alpha instead of
  `mix-blend-mode`, SVG-drawn shadows instead of `filter: drop-shadow` on moving things, small blurs.
- Avoid first-use hitches: warm `unicode-range` fonts (e.g. Cyrillic) with `document.fonts.load(...)`, and call
  `img.decode()` before the reveal.
- A CSS `linear()` spring needs a fallback. Declare the cubic-bezier `transition` first and the `linear()` one
  second, never inside `var()`.

## Packages and dev server
- `cd apps/<app>/frontend && pnpm add <pkg>` (or `-D`). Use `pnpm exec <bin>`, not `npx`. It's a pnpm
  workspace, so the real lockfile is the **root** `pnpm-lock.yaml`, and the Dockerfiles copy that one. Don't create
  per-app lockfiles.
- Vite runs on the host with HMR. If it misses a new dependency, run `make restart-frontend APP=<app>`.
- If you bump `@kubb/*`, run `make schema APP=<app>` and commit the regenerated `src/gen` in the same commit.
- Checks: `pnpm typecheck` (`vue-tsc --noEmit`) and `pnpm lint`.

## Reference implementations
- Profile screen: `apps/template-vue/frontend/src/app/presentation/screens/Profile.vue`
- Optimistic mutation: `apps/template-vue/frontend/src/app/composables/useUpdateUser.ts`
- Query/mutation demos (polling, infinite scroll, WebSocket, streaming, optimistic):
  `apps/template-vue/frontend/src/app/presentation/components/demo/`
