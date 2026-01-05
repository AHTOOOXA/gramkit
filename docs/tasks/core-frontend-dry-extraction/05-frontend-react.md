# Phase 06: Frontend React Extraction

**Focus:** Extract AppInitProvider and auth hooks to core-react package

---

## Codebase Analysis

### Current Implementation (template-react)

#### AppInitProvider
**File:** `/Users/anton/tarot/apps/template-react/frontend/providers/AppInitProvider.tsx` (Lines 1-366)

**Purpose:** Single entry point for app initialization handling:
- Authentication detection (TMA via initData vs web via session cookie)
- Calling `/process_start` API endpoint to:
  - Record user visit (admin notifications)
  - Track referral/invite code usage
  - Handle mode routing (draw, settings, etc.)
  - Update timezone
- PostHog analytics identification (using database user_id, not Telegram ID)
- Start parameter parsing (invites, referrals, mode routing, page navigation)
- Query client integration for caching user data
- Re-initialization trigger for post-login state updates

**Key Dependencies:**
- `useQueryClient` from `@tanstack/react-query`
- `useTelegram` from `@tma-platform/core-react/platform` (for initData detection)
- `usePostHog` from `@tma-platform/core-react/analytics`
- `useRouter` from `@/i18n/navigation` (Next.js i18n router)
- Generated API client: `processStartProcessStartPost`, `getSubscriptionSubscriptionsGet`
- Query keys: `getCurrentUserUsersMeGetQueryKey`, `getSubscriptionSubscriptionsGetQueryKey`
- Types: `UserSchema`, `StartMode`

**State Structure (Lines 29-46):**
```typescript
AppInitState {
  isReady: boolean         // App fully initialized and ready
  isLoading: boolean       // Currently loading/initializing
  user: UserSchema | null  // Current user (null if not authenticated)
  error: Error | null      // Error during initialization
}

AppInitContextValue extends AppInitState {
  reinitialize: () => void // Trigger re-init after web auth
}
```

**Module-Level State (Lines 105-110):**
- `hasInitializedSession`: boolean - Persists across component remounts from locale changes
- `isInitializing`: useRef - Prevents concurrent init calls

**Initialization Flow (Lines 164-327):**
1. Check if already initialized (module-level persistence)
2. Detect auth method: TMA vs web session
3. Parse start parameters (invite codes, referrals, mode, page)
4. Build `/process_start` request with timezone
5. Call API (handles 401 gracefully for unauthenticated web users)
6. On success: Set user in query cache, identify in PostHog, handle mode routing
7. On error: Mark as not ready but not loading (allows login UI to show)
8. Prefetch subscription data

**Hook Export (Lines 357-365):**
```typescript
useAppInit(): AppInitContextValue
// - Access: { user, isReady, isLoading, error, reinitialize }
// - Throws if used outside AppInitProvider
```

#### useAuth Hook
**File:** `/Users/anton/tarot/apps/template-react/frontend/hooks/useAuth.ts` (Lines 1-66)

**Purpose:** Centralized auth state access with role-based permission checks

**Dependencies:**
- `useAppInit` from `@/providers/AppInitProvider`

**Return Values (Lines 28-65):**
```typescript
{
  user: UserSchema | null
  role: 'user' | 'admin' | 'owner' | null
  isAuthenticated: boolean           // user_type === 'REGISTERED'
  isGuest: boolean                   // user_type === 'GUEST' or null
  isAdmin: boolean                   // role === 'admin'
  isOwner: boolean                   // role === 'owner'
  isAdminOrOwner: boolean            // admin OR owner
  isLoading: boolean                 // Auth initializing
  isReady: boolean                   // Auth complete
  error: Error | null                // Init errors
  reinitialize: () => void           // Re-init after login
}
```

**Logic (Lines 32-39):**
- Backend returns GUEST user even without login (check `user_type` field)
- `isAuthenticated` = `user_type === 'REGISTERED'`
- `isGuest` = `!user || user_type === 'GUEST'`
- Role-based checks only valid when authenticated

#### useLogout Hook
**File:** `/Users/anton/tarot/apps/template-react/frontend/hooks/useLogout.ts` (Lines 1-50)

**Purpose:** Logout with automatic cache clearing and state reset

**Dependencies:**
- `useRouter` from `next/navigation`
- `useQueryClient` from `@tanstack/react-query`
- `useLogoutAuthLogoutPost` from `@/src/gen/hooks` (Kubb generated)
- `useAppInit` from `@/providers/AppInitProvider`

**Implementation (Lines 18-49):**
- Wraps generated `useLogoutAuthLogoutPost` mutation
- On success:
  - Clear all query client cache (`queryClient.clear()`)
  - Trigger reinitialize() (will fail auth, set user to null)
  - Redirect to home page
- On error:
  - Still clears cache and reinitializes (logout should always succeed)
  - Redirects anyway (user is effectively logged out locally)

### Current Usage Pattern (template-react)

**Provider Registration:** `/Users/anton/tarot/apps/template-react/frontend/app/providers.tsx` (Lines 1-229)

**Provider Stack (Lines 217-227):**
```tsx
<ErrorBoundary>
  <SDKProvider>                    // Telegram SDK & miniApp.ready()
    <QueryClientProvider>          // TanStack Query
      <AppInitProvider>            // App init & auth state
        <AppContent>               // Shows loading/error states
          <ThemeProvider>
            {children}
          </ThemeProvider>
        </AppContent>
      </AppInitProvider>
    </QueryClientProvider>
  </SDKProvider>
</ErrorBoundary>
```

**Hook Exports:** `/Users/anton/tarot/apps/template-react/frontend/hooks/index.ts` (Lines 1-24)

Current auth hooks exported at app level:
- `useAuth` (Line 2)
- `useLogout` (Line 6)

### Existing Core Exports

**Core Package Location:** `/Users/anton/tarot/core/frontend-react/src/`

**Current Module Structure:**
- `analytics/` - PostHog integration
- `errors/` - Error classification
- `hooks/` - Generic hooks (useScroll, useLayout, usePlaceholderHeight)
- `platform/` - Telegram SDK + mock platform
- `services/` - Static service utilities
- `types/` - Type definitions
- `utils/` - Utility functions
- `index.ts` - Root exports (re-exports all modules)

**Main Export Pattern:** `/Users/anton/tarot/core/frontend-react/src/index.ts` (Lines 1-9)
```typescript
export * from './analytics';
export * from './errors';
export * from './hooks';
export * from './platform';
export * from './services';
export * from './types';
export * from './utils';
```

---

## Implementation Steps

### Step 1: Create Hook Factory for useAuth

**File:** `/Users/anton/tarot/core/frontend-react/src/hooks/auth/createUseAuth.ts` (NEW)

**Pattern - Hook Factory with Dependency Injection:**
```typescript
import type { UserSchema } from '@/src/gen/models'; // From app's generated types

export type UserRole = 'user' | 'admin' | 'owner';

export interface AuthHookDependencies {
  useAppInit: () => {
    user: UserSchema | null;
    isLoading: boolean;
    isReady: boolean;
    error: Error | null;
    reinitialize: () => void;
  };
}

export function createUseAuth(useAppInit: AuthHookDependencies['useAppInit']) {
  return function useAuth() {
    const { user, isLoading, isReady, error, reinitialize } = useAppInit();

    const isGuest = !user || user.user_type === 'GUEST';
    const isAuthenticated = user?.user_type === 'REGISTERED';
    const role = (isAuthenticated ? user.role : null) as UserRole | null;
    const isAdmin = role === 'admin';
    const isOwner = role === 'owner';
    const isAdminOrOwner = isAdmin || isOwner;

    return {
      user,
      role,
      isAuthenticated,
      isGuest,
      isAdmin,
      isOwner,
      isAdminOrOwner,
      isLoading,
      isReady,
      error,
      reinitialize,
    };
  };
}
```

**Rationale:**
- Factory pattern allows core package to remain agnostic of app-specific `useAppInit`
- Apps inject their own `useAppInit` hook
- Core exports the factory, app creates the bound hook

### Step 2: Create Hook Factory for useLogout

**File:** `/Users/anton/tarot/core/frontend-react/src/hooks/auth/createUseLogout.ts` (NEW)

**Pattern - Hook Factory with Multiple Dependencies:**
```typescript
export interface LogoutHookDependencies {
  useQueryClient: () => QueryClient;
  useRouter: () => Router;
  useAppInit: () => { reinitialize: () => void };
  useLogoutMutation: () => UseMutationResult<void, Error>;
}

export function createUseLogout({
  useQueryClient,
  useRouter,
  useAppInit,
  useLogoutMutation,
}: LogoutHookDependencies) {
  return function useLogout() {
    const queryClient = useQueryClient();
    const router = useRouter();
    const { reinitialize } = useAppInit();

    return useLogoutMutation({
      mutation: {
        onSuccess: () => {
          queryClient.clear();
          reinitialize();
          if (typeof window !== 'undefined') {
            router.push('/');
          }
        },
        onError: (error) => {
          console.error('Logout failed:', error);
          queryClient.clear();
          reinitialize();
          if (typeof window !== 'undefined') {
            router.push('/');
          }
        },
      },
    });
  };
}
```

**Rationale:**
- Logout requires several app-level dependencies (router, generated hooks, etc.)
- Factory accepts all dependencies, core provides the composed logic

### Step 3: Create Provider Factory

**File:** `/Users/anton/tarot/core/frontend-react/src/providers/createAppInitProvider.ts` (NEW)

**Pattern - Provider Factory:**
```typescript
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { PropsWithChildren } from 'react';

export interface AppInitProviderDependencies {
  useQueryClient: () => QueryClient;
  useTelegram: () => { initData: string | undefined };
  usePostHog: () => PostHog;
  useRouter: () => Router;
  processStartPost: (payload: ProcessStartPayload) => Promise<ProcessStartResponse>;
  getSubscription: () => Promise<SubscriptionSchema>;
  getCurrentUserQueryKey: () => string[];
  getSubscriptionQueryKey: () => string[];
}

export function createAppInitProvider(deps: AppInitProviderDependencies) {
  const AppInitContext = createContext<AppInitContextValue | null>(null);

  function AppInitProvider({ children }: PropsWithChildren) {
    // ... Full implementation (same as template-react)
    // Use deps.useQueryClient(), deps.useTelegram(), etc.
  }

  function useAppInit(): AppInitContextValue {
    const context = useContext(AppInitContext);
    if (!context) {
      throw new Error('useAppInit must be used within AppInitProvider');
    }
    return context;
  }

  return { AppInitProvider, useAppInit };
}
```

**Rationale:**
- Provider initialization differs by app (query client, router, API client)
- Factory accepts all app-specific dependencies
- Returns both Provider and hook bound to that instance

### Step 4: Create Core Module Exports

**File:** `/Users/anton/tarot/core/frontend-react/src/providers/index.ts` (NEW)

```typescript
export { createAppInitProvider } from './createAppInitProvider';
export type { AppInitProviderDependencies, AppInitContextValue, AppInitState } from './createAppInitProvider';
```

**File:** `/Users/anton/tarot/core/frontend-react/src/hooks/auth/index.ts` (NEW)

```typescript
export { createUseAuth } from './createUseAuth';
export { createUseLogout } from './createUseLogout';
export type { UserRole, AuthHookDependencies, LogoutHookDependencies } from './createUseAuth';
```

**Update Root Export:** `/Users/anton/tarot/core/frontend-react/src/index.ts`

```typescript
// Add to existing exports:
export * from './providers';
export * from './hooks/auth';
```

### Step 5: Update template-react to Use Core Factory

**File:** `/Users/anton/tarot/apps/template-react/frontend/providers/AppInitProvider.tsx` (MODIFY)

**Pattern - Use Core Factory:**
```typescript
'use client';

import { createAppInitProvider } from '@tma-platform/core-react/providers';
import { useQueryClient } from '@tanstack/react-query';
import { useTelegram } from '@tma-platform/core-react/platform';
import { usePostHog } from '@tma-platform/core-react/analytics';
import { useRouter } from '@/i18n/navigation';
import {
  processStartProcessStartPost,
  getSubscriptionSubscriptionsGet,
} from '@/src/gen/client/{...}';
import {
  getCurrentUserUsersMeGetQueryKey,
  getSubscriptionSubscriptionsGetQueryKey,
} from '@/src/gen/hooks';

// Create bound provider and hook for this app
const { AppInitProvider, useAppInit } = createAppInitProvider({
  useQueryClient,
  useTelegram,
  usePostHog,
  useRouter,
  processStartPost: processStartProcessStartPost,
  getSubscription: getSubscriptionSubscriptionsGet,
  getCurrentUserQueryKey: getCurrentUserUsersMeGetQueryKey,
  getSubscriptionQueryKey: getSubscriptionSubscriptionsGetQueryKey,
});

export { AppInitProvider, useAppInit };
```

**Rationale:**
- Removes ~300 lines of logic to core
- App only specifies its dependencies and exports
- Provider behavior is maintained, logic is shared

### Step 6: Update useAuth Hook

**File:** `/Users/anton/tarot/apps/template-react/frontend/hooks/useAuth.ts` (MODIFY)

```typescript
import { createUseAuth } from '@tma-platform/core-react/hooks/auth';
import { useAppInit } from '@/providers/AppInitProvider';

export { type UserRole } from '@tma-platform/core-react/hooks/auth';

// Create bound hook for this app
export const useAuth = createUseAuth(useAppInit);
```

**Rationale:**
- Removes ~30 lines
- Behavior identical to original
- Role types exported from core

### Step 7: Update useLogout Hook

**File:** `/Users/anton/tarot/apps/template-react/frontend/hooks/useLogout.ts` (MODIFY)

```typescript
'use client';

import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { createUseLogout } from '@tma-platform/core-react/hooks/auth';
import { useLogoutAuthLogoutPost } from '@/src/gen/hooks';
import { useAppInit } from '@/providers/AppInitProvider';

export const useLogout = createUseLogout({
  useQueryClient,
  useRouter,
  useAppInit,
  useLogoutMutation: useLogoutAuthLogoutPost,
});
```

**Rationale:**
- Removes ~25 lines of mutation logic
- Centralizes cache clearing and redirect logic
- App specifies only its router and generated hooks

### Step 8: Update providers/index.ts

**File:** `/Users/anton/tarot/apps/template-react/frontend/providers/index.ts` (MODIFY)

```typescript
export { AppInitProvider, useAppInit } from './AppInitProvider';
```

No changes needed - still exports the app's bound provider and hook.

---

## Success Criteria

- [x] Core provider factory extracted to `/Users/anton/tarot/core/frontend-react/src/providers/`
- [x] Auth hook factory extracted to `/Users/anton/tarot/core/frontend-react/src/hooks/auth/`
- [x] Logout hook factory extracted to core
- [x] template-react uses core factories via dependency injection
- [x] Core exports available via `@tma-platform/core-react/providers` and `@tma-platform/core-react/hooks/auth`
- [x] No changes to template-react app functionality or provider stack
- [x] No new imports in template-react of app-generated types/hooks
- [x] ~180 lines of duplicated init logic removed from template-react
- [x] Factory pattern allows future apps (template-vue, maxstat) to reuse same pattern
- [x] Types properly exported from core (`UserRole`, `AppInitContextValue`, `AppInitState`)
- [x] All 'use client' directives in place where needed
- [x] Module-level state (`hasInitializedSession`, `isInitializing`) remains in provider instance
- [x] PostHog identification logic preserved (uses database user_id)
- [x] Start parameter parsing preserved for TMA users
- [x] Subscription prefetch logic preserved
- [x] Error handling for unauthenticated web users preserved (isLoading=false, isReady=false)

---

## Line Count Impact

| Component | Removed | File |
|-----------|---------|------|
| AppInitProvider logic | ~300 lines | template-react → core factory |
| useAuth hook | ~30 lines | template-react → core factory |
| useLogout hook | ~25 lines | template-react → core factory |
| **Phase Total** | **~355 lines** | template-react savings |

**Core additions:** ~280 lines (factories + types + tests)
**Net savings for multi-app:** ~150 lines per additional React app

---

## Dependencies & Imports

### Core Exports
```typescript
@tma-platform/core-react/providers:
  - createAppInitProvider
  - AppInitProviderDependencies
  - AppInitContextValue
  - AppInitState

@tma-platform/core-react/hooks/auth:
  - createUseAuth
  - createUseLogout
  - UserRole
  - AuthHookDependencies
  - LogoutHookDependencies
```

### App-Specific (template-react)
```typescript
- @tanstack/react-query (useQueryClient)
- @tma-platform/core-react/platform (useTelegram)
- @tma-platform/core-react/analytics (usePostHog)
- @/i18n/navigation (useRouter)
- @/src/gen/client/* (generated API functions)
- @/src/gen/hooks (generated query keys)
```

---

## Notes

- Factory pattern decouples core logic from app-specific dependencies
- No global state - each app instance has its own AppInitProvider context
- Module-level `hasInitializedSession` prevents re-init on locale-change remounts
- PostHog identification uses database user_id (not Telegram ID) for accurate analytics
- Unauthenticated web users: `isLoading=false, isReady=false` allows login UI to render
