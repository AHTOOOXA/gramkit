---
paths:
  - "apps/template-react/frontend/**"
  - "core/frontend-react/**"
---

# React / Next apps (`template-react` and apps copied from it, `core/frontend-react`)

Stack: Next.js 16 App Router, React 19, TanStack Query + Kubb 3, shadcn/ui (`new-york-v4`, lucide),
`next-intl`, `sonner`, Tailwind v4 + `tailwindcss-motion`. The API layer (`make schema`, generated hooks,
query keys, `apiFetch`) is covered in `.claude/rules/frontend-api.md`. The always-on rules are in root `CLAUDE.md`.

Everything below describes **template-react**. An app copied from it may have drifted (its own layouts, route
groups, auth hooks), so check that app's files before assuming any of it.

## Layout of `apps/<app>/frontend/` (there's no `src/` except for codegen)
```
app/[locale]/(marketing|app|auth)/   routes; app/providers.tsx = QueryClient (retry rules), PostHog, platform mock
components/ui/          shadcn/ui     components/shells/AppShell.tsx   components/navigation/AppNav.tsx
components/layout/      Footer, FooterMinimal, header
config/                 kubb-config.ts, navigation.ts, layout.ts, constants.ts, mock-users.ts
hooks/                  useAuth, useUpdateUser, useLogout, useScrollReveal…, re-exported from hooks/index.ts
i18n/                   next-intl routing + messages/{en,ru}.json
lib/                    utils (cn), errors, platform.ts (server), middleware-utils
styles/globals.css      Tailwind v4 entry, tokens, layout CSS vars
src/gen/  src/schema/   codegen (don't edit)
proxy.ts                Next 16 proxy (there is no middleware.ts): i18n + route access
```
Aliases: `@/` = the frontend root, so generated code is `@/src/gen/hooks` (`@gen/*` also works).
`@tma-platform/core-react` = `core/frontend-react/src`.

## Core package: `@tma-platform/core-react`
- Import from subpaths: `/errors` (`classifyHttpError`, `isApiError`, `getErrorMessage`), `/analytics`
  (`initPostHog`, `usePostHog`; see `.claude/rules/analytics.md`), `/platform` (`usePlatform`,
  `useTelegram`, `isUserMockEnabled`), `/platform-mock`, `/types`, `/hooks`, `/services`, `/utils`.
  **Not `@core/...`.** That alias belongs to the Vue apps.
- `usePlatform`, `useTelegram`, `useScroll` and `useLayout` are re-exported from `@/hooks`. `usePlatform()` gives
  `isTelegram`, `isTelegramMobile`, `isTelegramDesktop` and `tgPlatform`.
- `core/frontend-react` never imports from an app. React code that 2+ apps need goes there.

## Rendering model
- Every page is a client component (`'use client'`). Data comes from the FastAPI backend through the
  generated hooks. The Next server has no database and no secrets, so don't write server-side fetching or DB
  access into pages.
- Server-only helpers are few: `lib/platform.ts` → `getPlatform()`, `isTelegram()` and `isWeb()` read the
  `${APP_NAME}-platform` cookie (for server layouts, e.g. a web-only route group).
  `app/[locale]/{loading,error,not-found}.tsx` exist at the locale level.
- Local `basePath` is `/template-react` (see `next.config.ts`, where `NEXT_PUBLIC_BASE_PATH` overrides it). For
  locale-aware navigation, use `Link`/`useRouter` from `@/i18n/navigation`.

## State
- Server state lives in TanStack Query. Local UI state lives in `useState`, and shared app state lives in
  React context (`providers/AppInitProvider.tsx`, read through `useAuth`).
- `zustand` is in `package.json`, but **no file imports it**, and there is no `src/store`. Don't create a store
  for something `useState`, context or the query cache already covers.

## Auth and route access
- **Check auth with `useAuth()` from `@/hooks`, never `!!user`.** The backend returns a `GUEST` user even
  when nobody is logged in, so `user` is always set. `useAuth` gives `isAuthenticated`
  (`user_type === 'REGISTERED'`), `isGuest`, `role` (`'user' | 'admin' | 'owner' | null`), `isAdmin`,
  `isOwner`, `isAdminOrOwner` (for admin pages), `isLoading`, `isReady`, and `reinitialize()`, which you call
  after login. Source: `hooks/useAuth.ts`.
- **Access is enforced in `proxy.ts`, not by route groups.** It keeps three lists: `publicRoutes` (`/`,
  `/demo`), `guestOnlyRoutes` (`/login`, `/marketing`; logged-in users get sent home) and
  `authRequiredRoutes` (`/profile`, `/admin`, `/test-gen`; guests get sent to `/login`). **A new protected
  page must be added to `authRequiredRoutes`.** Putting it in `(app)` doesn't protect it.
  The proxy only checks that an `initData` header or a `${APP_NAME}_session` cookie is present. Roles are
  checked in the page (`isAdminOrOwner`) and on the backend.

## Navigation and shell
- **Nav items live only in `config/navigation.ts` → `navItems`**, and `AppNav` renders them through
  `getVisibleNavItems`. Each item has `id`, `href`, `icon` (lucide), `labelKey` (an i18n key, so add both en
  and ru), `access` (`public` | `guest` | `auth` | `admin` for admin or owner | `owner`), plus `showInMobile`
  (bottom tabs, ≤5), `showInDesktop` and `lockedForGuests`. Don't hand-add links in components.
- `config/layout.ts` → `layoutConfig.mobileLayout`: `'bottom-tabs'` (consumer apps) or `'hamburger'`
  (admin/dashboard).
- Route groups, each with its own layout: `(marketing)` → `<AppShell footer={<Footer />}>` (`/`), `(app)` →
  `<AppShell>` (`/demo`, `/profile`, `/admin`, `/test-gen`), `(auth)` → `<AppShell>` (`/login`).
- `AppShell` (`components/shells/AppShell.tsx`) takes `footer?: ReactNode`, `variant` (`default` | `wide` |
  `narrow` | `full`) and `hideNav`. It **already pads `<main>`** with
  `px-[var(--page-padding-x)] py-[var(--page-padding-y)]` and reserves `--bottom-nav-height` on mobile. So
  don't add `px-*`/`pt-*` to a page. Add only what the page needs, such as `max-w-*`, `space-y-*`, or extra `pb-*`
  under a sticky button. Always read the layout chain first.
- Layout CSS vars in `styles/globals.css`: `--header-height` 3.5rem, `--bottom-nav-height` 4.125rem (0 on
  desktop), `--page-padding-x` 1rem (1.5rem on desktop), `--page-padding-y` 1rem, `--page-max-width` 80rem. Use
  them for sticky/fixed placement: `sticky top-[calc(var(--header-height)+1rem)]`,
  `fixed bottom-[calc(var(--bottom-nav-height)+1.5rem)] md:bottom-6`, and for full-bleed sections
  `-mx-[var(--page-padding-x)]`. Never write `top-14`.

## UI and styling
- Use shadcn/ui from `@/components/ui/*` before you build anything custom. template-react has a broad set:
  dialog, sheet, drawer, alert-dialog, popover, tooltip, dropdown-menu, command, select, form (react-hook-form
  + zod), input-otp, password-input, table, tabs, carousel, chart, sidebar, skeleton, spinner, sonner, and more.
  Extend a component through `className` + `cn()` or a wrapper component. Don't edit copies of shadcn source.
  For toasts, use `toast` from `sonner`.
- Colors: use semantic tokens (`bg-card`, `text-muted-foreground`, `border-border`, `bg-primary/10`) and
  check both themes. Touch targets should be ≥ 44px (`h-11 w-11`).
- Tailwind v4 policy is the same as the Vue apps: write classes inline. ❌ No JS maps of class strings. ❌ No
  `@utility`/`@apply` that only bundles existing utilities. Reuse goes into a component. `@utility` is only
  for CSS Tailwind lacks.
- For scroll reveals, use `useScrollReveal()` from `@/hooks` (returns `{ ref, isVisible }`) and wrap it in a
  small local `ScrollReveal` component with a 0/100/200 ms `transitionDelay` stagger (see
  `app/[locale]/(marketing)/page.tsx`). `tailwindcss-intersect` doesn't work with v4.

## Packages and dev server
- `cd apps/<app>/frontend && pnpm add <pkg>`. Use `pnpm exec`, not `npx`. The real lockfile is the root
  `pnpm-lock.yaml` (pnpm workspace).
- `next dev` runs on the host: template-react on port 3001 (give each new app its own port). If it misses a change, run
  `make restart-frontend APP=<app>`. If you bump `@kubb/*`, run `make schema` and commit `src/gen` in the
  same commit.
- Checks: `pnpm typecheck` (`tsc --noEmit`), `pnpm lint`, or `pnpm check` (which also checks prettier formatting).

## Reference implementations (template-react)
`hooks/useAuth.ts`, `hooks/useUpdateUser.ts` (optimistic), `hooks/useLogout.ts`, `config/navigation.ts`,
`config/layout.ts`, `components/shells/AppShell.tsx`, `components/navigation/AppNav.tsx`, `proxy.ts`,
`app/[locale]/(app)/profile/page.tsx`, `app/[locale]/(auth)/login/page.tsx`, and
`app/[locale]/(app)/demo/page.tsx` (query/mutation/streaming demos).
