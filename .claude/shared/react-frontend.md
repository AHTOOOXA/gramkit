# React Frontend Patterns

## Quick Checklist

- [ ] Server Components by default, 'use client' only when needed
- [ ] Server state → TanStack Query (generated hooks from `@gen/hooks/`)
- [ ] Client state → Zustand or local `useState`
- [ ] Query options nested under `query: { ... }`
- [ ] Mutation variables wrapped in `{ data: ... }`
- [ ] Uses shadcn/ui components
- [ ] Custom hooks follow `use*` naming
- [ ] No god hooks
- [ ] Event handlers for user actions (not useEffect)
- [ ] No derived state with useState + useEffect
- [ ] **Check layout padding before adding `px-*`/`pt-*` to pages**
- [ ] **Use `useAuth()` for auth checks, not `!!user`**
- [ ] **Add nav items to `config/navigation.ts`, not components**

---

## TanStack Query + Kubb

### Critical Gotchas

**1. Query options must be nested:**
```tsx
// ❌ WRONG
const { data } = useGetCurrentUserUsersMeGet({
  staleTime: 5 * 60 * 1000,
});

// ✅ CORRECT
const { data } = useGetCurrentUserUsersMeGet({
  query: {
    staleTime: 5 * 60 * 1000,
  }
});
```

**2. Mutation variables must be wrapped:**
```tsx
// ❌ WRONG
await updateUser({ app_language_code: 'ru' });

// ✅ CORRECT
await updateUser({ data: { app_language_code: 'ru' } });
```

**3. Hook names are verbose:**
```tsx
useGetCurrentUserUsersMeGet()       // GET /users/me
useUpdateCurrentUserUsersMePatch()  // PATCH /users/me
useGetProductsPaymentsProductsGet() // GET /payments/products
```

**4. Finding the right hook:**
```tsx
// 1. Browse: apps/{app}/frontend/src/gen/hooks/
// 2. Pattern: use{Method}{Path} → useGetCurrentUserUsersMeGet
// 3. Query keys: get{Path}QueryKey → getCurrentUserUsersMeGetQueryKey
```

### Basic Query

```tsx
import { useGetCurrentUserUsersMeGet } from '@gen/hooks';

function Profile() {
  const { data: user, isLoading, error, isPending } = useGetCurrentUserUsersMeGet({
    query: {
      staleTime: 5 * 60 * 1000,
    }
  });

  if (isPending) return <Skeleton />;
  if (error) return <Error error={error} />;
  return <ProfileView user={user} />;
}
```

### Loading & Error States

```tsx
function UserProfile() {
  const { data, isLoading, error, refetch } = useGetCurrentUserUsersMeGet();

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Error occurred
          <Button size="sm" onClick={() => refetch()}>Retry</Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (isLoading) {
    return <Skeleton className="h-5 w-1/2" />;
  }

  return <div>{data?.name}</div>;
}
```

### Dependent Queries

```tsx
// Only fetch subscription when user exists
function UserSubscription() {
  const { data: user } = useGetCurrentUserUsersMeGet();

  const { data: subscription } = useGetSubscriptionSubscriptionsGet({
    query: {
      enabled: !!user, // Only fetch when user exists
    }
  });

  return <SubscriptionView subscription={subscription} />;
}
```

### When to Create Focused Hooks

| Scenario | Pattern |
|----------|---------|
| Simple query | Generated hook directly |
| Simple mutation | Generated hook directly |
| Mutation + optimistic update | Create focused hook |
| Mutation + cache clearing + redirect | Create focused hook |
| Mutation + multi-query invalidation | Create focused hook |
| Same config in 3+ places | Consider focused hook |

### Optimistic Update Pattern

```tsx
function useUpdateUser() {
  const queryClient = useQueryClient();

  return useUpdateCurrentUserUsersMePatch({
    mutation: {
      onMutate: async (variables) => {
        // Cancel outgoing queries
        await queryClient.cancelQueries({
          queryKey: getCurrentUserUsersMeGetQueryKey()
        });

        // Snapshot previous value
        const previousUser = queryClient.getQueryData(
          getCurrentUserUsersMeGetQueryKey()
        );

        // Optimistically update cache
        if (previousUser && variables.data) {
          queryClient.setQueryData(
            getCurrentUserUsersMeGetQueryKey(),
            { ...previousUser, ...variables.data }
          );
        }

        return { previousUser };
      },

      onError: (error, variables, context) => {
        // Rollback on error
        if (context?.previousUser) {
          queryClient.setQueryData(
            getCurrentUserUsersMeGetQueryKey(),
            context.previousUser
          );
        }
        toast.error('Failed to update');
      },

      onSuccess: () => {
        // Sync with server
        queryClient.invalidateQueries({
          queryKey: getCurrentUserUsersMeGetQueryKey()
        });
        toast.success('Updated!');
      },
    },
  });
}
```

### Cache Invalidation

**Always use generated `*QueryKey()` functions.** Kubb generates keys as `[{ url: '/path' }, ...params]`, not simple strings.

```tsx
// ✅ CORRECT: Use generated query key functions
import { getCurrentUserUsersMeGetQueryKey } from '@gen/hooks';
import { listOrdersOrdersGetQueryKey } from '@gen/hooks';

// Invalidate specific query (no params)
queryClient.invalidateQueries({
  queryKey: getCurrentUserUsersMeGetQueryKey()
});

// Invalidate query with specific params
queryClient.invalidateQueries({
  queryKey: listOrdersOrdersGetQueryKey({ status: 'active' })
});

// Invalidate all variants of a query (any params)
queryClient.invalidateQueries({
  queryKey: listOrdersOrdersGetQueryKey()  // No params = matches all /orders queries
});

// Clear all cache (e.g., on logout)
queryClient.clear();
```

```tsx
// ❌ WRONG: Simple string arrays don't match kubb-generated keys
queryClient.invalidateQueries({ queryKey: ['orders'] });  // Won't work!
// Kubb keys are [{ url: '/orders' }], not ['orders']

// ⚠️ AVOID: Predicate is fragile, couples to internal structure
queryClient.invalidateQueries({
  predicate: (q) => (q.queryKey[0] as { url?: string })?.url === '/orders'
});
```

### Streaming / SSE Endpoints

For streaming endpoints (AI responses, SSE), use `apiFetch` instead of axios:

```tsx
import { apiFetch } from '@/config/kubb-config';

// ✅ CORRECT: Uses same baseURL and auth headers as axios
const res = await apiFetch('/demo/stream');
const reader = res.body?.getReader();

// ❌ WRONG: Hardcoded URL, missing auth headers
const res = await fetch('/api/template-react/demo/stream');
```

`apiFetch` automatically includes:
- Correct `baseURL` from environment
- `initData` header for Telegram auth
- `Mock-Platform` header in debug mode
- `credentials: 'include'` for cookies

### WebSocket / Socket.io

For WebSocket connections, use `getSocketOptions()`:

```tsx
import { io } from 'socket.io-client';
import { getSocketOptions } from '@/config/kubb-config';

const { url, options } = getSocketOptions();
const socket = io(url, options);
```

`getSocketOptions()` returns complete socket.io config:
- Correct URL and path for production/dev
- `auth` with `initData` for Telegram authentication
- `withCredentials: true` for cookies
- Reconnection settings (5 attempts, 1s delay)

---

## State Management

### The Rule

```
Server State → TanStack Query
Client State → Zustand or useState
```

**Server state:** Data from APIs (users, products, subscriptions)
**Client state:** UI state (theme, modals, form inputs)

```tsx
// ✅ Server state - TanStack Query
const { data: user } = useGetCurrentUserUsersMeGet();
const { data: subscription } = useGetSubscriptionSubscriptionsGet();

// ✅ Client state - Zustand
const isDarkMode = useUIStore(state => state.isDarkMode);

// ✅ Client state - local useState
const [isEditing, setIsEditing] = useState(false);

// ✅ Derived from server state - computed (no useState needed!)
const isPremium = subscription?.status === 'active';
```

### Zustand Store (Client State Only)

```tsx
export const useUIStore = create<UIStore>((set) => ({
  isDarkMode: false,
  isModalOpen: false,
  toggleTheme: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
}));

// ❌ BAD: Server state in Zustand
export const useUserStore = create((set) => ({
  user: null,
  fetchUser: async () => { /* NO! Use TanStack Query */ },
}));
```

---

## Authentication & Authorization

### useAuth Hook

Centralized auth state. **Always use this instead of checking `user` directly.**

```tsx
import { useAuth } from '@/hooks';

function MyComponent() {
  const {
    user,              // User object (may be GUEST or REGISTERED)
    role,              // 'user' | 'admin' | 'owner' | null
    isAuthenticated,   // True if REGISTERED (not GUEST)
    isGuest,           // True if not logged in
    isAdmin,           // role === 'admin'
    isOwner,           // role === 'owner'
    isAdminOrOwner,    // admin OR owner (for admin pages)
    isLoading,         // Auth initializing
    reinitialize,      // Call after login
  } = useAuth();

  if (isGuest) return <LoginPrompt />;
  if (isOwner) return <OwnerDashboard />;
  if (isAdminOrOwner) return <AdminPanel />;
  return <UserDashboard />;
}
```

**Why not `!!user`?** Backend returns a `GUEST` user even without login, so `!!user` is always true. Must check `user_type === 'REGISTERED'`.

### Roles

| Role | Privilege | Can Access |
|------|-----------|------------|
| `user` | Basic | Auth-required pages |
| `admin` | Elevated | Admin pages + user pages |
| `owner` | Highest | Everything + protected actions |

### Navigation Config

Single source of truth: `config/navigation.ts`

```tsx
// Add a new nav item
export const navItems: NavItem[] = [
  { id: 'home', href: '/', icon: Home, labelKey: 'nav.home', access: 'public', showInMobile: true },
  { id: 'demo', href: '/demo', icon: FlaskConical, labelKey: 'nav.demo', access: 'public', showInMobile: true },
  { id: 'profile', href: '/profile', icon: User, labelKey: 'nav.profile', access: 'auth', showInMobile: true },
  { id: 'admin', href: '/admin', icon: Settings, labelKey: 'nav.admin', access: 'admin', showInMobile: false },
];
```

**Access Levels:**

| Level | Who Can See |
|-------|-------------|
| `public` | Everyone |
| `guest` | Only guests (not logged in) |
| `auth` | Authenticated users |
| `admin` | Admin OR Owner |
| `owner` | Only Owner |

**To add a nav item:** Edit `config/navigation.ts` only - no need to touch components.

---

## Server vs Client Components

```
Need interactivity? → 'use client'
├─ onClick, onChange handlers
├─ useState, useEffect
├─ Browser APIs (localStorage)
└─ TanStack Query hooks

Otherwise → Server Component (default)
├─ Static content
├─ Direct database access
├─ Secure operations (API keys)
```

```tsx
// ✅ Server Component (default) - no 'use client'
async function UserProfile({ userId }: { userId: string }) {
  const user = await db.users.findUnique({ where: { id: userId } });
  return <Profile user={user} />;
}

// ✅ Client Component - needs interactivity
'use client';
function ContactForm() {
  const [email, setEmail] = useState('');
  return <input value={email} onChange={e => setEmail(e.target.value)} />;
}
```

---

## Common Anti-Patterns

### Derived State with useState + useEffect

```tsx
// ❌ BAD: Derived state
function Component({ items }: { items: Item[] }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    setCount(items.length); // Unnecessary state!
  }, [items]);

  return <div>Count: {count}</div>;
}

// ✅ GOOD: Compute during render
function Component({ items }: { items: Item[] }) {
  const count = items.length; // No state needed!
  return <div>Count: {count}</div>;
}
```

### useEffect for User Actions

```tsx
// ❌ BAD: useEffect for button click
function Component() {
  const [shouldSave, setShouldSave] = useState(false);

  useEffect(() => {
    if (shouldSave) {
      saveData();
      setShouldSave(false);
    }
  }, [shouldSave]);

  return <button onClick={() => setShouldSave(true)}>Save</button>;
}

// ✅ GOOD: Event handler
function Component() {
  const handleSave = async () => {
    await saveData();
  };
  return <button onClick={handleSave}>Save</button>;
}
```

### Missing Dependencies

```tsx
// ❌ BAD: Missing dependencies (stale closure)
useEffect(() => {
  fetchUser(userId);
}, []); // userId is stale!

// ✅ GOOD: Include all dependencies
useEffect(() => {
  fetchUser(userId);
}, [userId]);
```

### God Hooks

```tsx
// ❌ BAD: God hook
const { user, friends, posts, updateUser, addFriend } = useUser();
// Over-fetching, can't tree-shake

// ✅ GOOD: Focused hooks
const { data: user } = useGetCurrentUserUsersMeGet();
const { data: friends } = useGetFriendsGet();
const { mutate: updateUser } = useUpdateUser();
```

### Infinite Render Loops

```tsx
// ❌ BAD: Infinite loop
useEffect(() => {
  setCount(count + 1); // Triggers re-render → effect runs again
}); // No dependency array!

// ✅ GOOD: Controlled dependencies
useEffect(() => {
  setCount(prev => prev + 1);
}, []); // Runs once
```

---

## shadcn/ui

**Location:** `apps/{app}/frontend/src/components/ui/`

```tsx
// Button with loading
<Button disabled={isPending} onClick={handleSubmit}>
  {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
  {isPending ? 'Saving...' : 'Save'}
</Button>

// Select with event handler
<Select value={language} onValueChange={handleLanguageChange}>
  <SelectTrigger>
    <SelectValue />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="en">English</SelectItem>
    <SelectItem value="ru">Русский</SelectItem>
  </SelectContent>
</Select>

// Dialog
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogTrigger asChild>
    <Button>Open</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Title</DialogTitle>
    </DialogHeader>
    {/* content */}
  </DialogContent>
</Dialog>
```

---

## Next.js App Router

### Route Groups & AppShell

```
app/[locale]/
├── (marketing)/   # Public pages with footer (/, /demo, /marketing)
├── (app)/         # Auth-required pages (/profile, /shop, /admin)
└── (auth)/        # Login pages (/login)
```

**Single unified AppShell:**

```tsx
// components/shells/AppShell.tsx
export function AppShell({
  children,
  footer = false,        // Show footer for guests
  variant = 'default',   // 'default' | 'wide' | 'narrow' | 'full'
}: AppShellProps)
```

| Route Group | Layout | Props |
|-------------|--------|-------|
| `(marketing)` | `<AppShell footer>` | Shows footer for guests |
| `(app)` | `<AppShell>` | Auth-required, middleware redirects |
| `(auth)` | `<AppShell>` | Login page |

```tsx
// (marketing)/layout.tsx
import { AppShell } from '@/components/shells';
export default function Layout({ children }) {
  return <AppShell footer>{children}</AppShell>;
}

// (app)/layout.tsx or (auth)/layout.tsx
import { AppShell } from '@/components/shells';
export default function Layout({ children }) {
  return <AppShell>{children}</AppShell>;
}
```

### Mobile Layout Config

Configure in `config/layout.ts`:

```tsx
export const layoutConfig = {
  mobileLayout: 'bottom-tabs', // or 'hamburger'
} as const;
```

- `bottom-tabs`: iOS-style bottom navigation (consumer apps)
- `hamburger`: Top header with slide-out menu (admin/dashboard apps)

### Platform Detection

- Cookie: `{APP_NAME}-platform` = 'telegram' | 'web'
- `usePlatform()` hook provides: `isTelegram`, `isTelegramMobile`, `isTelegramDesktop`, `tgPlatform`
- Middleware uses `{APP_NAME}_session` cookie for auth

### Loading & Error Files

```
app/dashboard/
├── page.tsx
├── loading.tsx    # Automatic loading UI
├── error.tsx      # Error boundary
└── not-found.tsx  # 404 page
```

---

## File Structure

```
apps/{app}/frontend/src/
├── gen/hooks/           # Generated TanStack Query hooks (DO NOT EDIT)
├── components/ui/       # shadcn/ui components
├── app/
│   ├── store/          # Zustand stores (client state only)
│   ├── composables/    # Custom hooks (useUpdateUser, etc.)
│   ├── presentation/
│   │   └── components/ # Reusable components
│   └── i18n/           # Translations
```

---

## Layout & Spacing

### Check Parent Layout Before Adding Padding

**Common mistake:** Adding `px-4 pt-4` to a page when the layout already provides it.

```tsx
// ❌ BAD: Redundant padding - layout already has px-4 pt-4
// File: app/[locale]/(app)/my-page/page.tsx
return (
  <div className="px-4 pt-4 pb-20">  {/* Double padding! */}
    <MyContent />
  </div>
);

// ✅ GOOD: Only add what's needed (e.g., extra bottom for sticky button)
return (
  <div className="pb-20 md:pb-0 max-w-md mx-auto">
    <MyContent />
  </div>
);
```

**Before adding spacing, check the parent layout:**

```tsx
// apps/{app}/frontend/app/[locale]/(app)/layout.tsx typically has:
<main className="px-4 lg:px-6 pt-4 md:pt-16 pb-20 md:pb-6">
  {children}
</main>
```

### Next.js Layout Hierarchy

Layouts are **nested** - each wraps the one below it:

```
app/
├── layout.tsx              # Root: html, body, fonts
├── [locale]/
│   ├── layout.tsx          # Locale: providers, i18n
│   ├── (app)/
│   │   ├── layout.tsx      # App: nav + main with padding ← ADDS PADDING
│   │   ├── page.tsx        # /
│   │   ├── profile/
│   │   │   └── page.tsx    # /profile (inherits (app) layout)
│   │   └── report_form/
│   │       └── page.tsx    # /report_form (inherits (app) layout)
│   └── (public)/
│       ├── layout.tsx      # Public: no padding (just <>children</>)
│       └── login/
│           └── page.tsx    # /login (no inherited padding)
```

**Route groups `(name)` don't affect URL** - they're for organizing layouts:
- `/profile` → uses `(app)/layout.tsx` → has padding
- `/login` → uses `(public)/layout.tsx` → no padding

**What each layout provides:**

| Layout | Styling | Contains |
|--------|---------|----------|
| `app/layout.tsx` | None (just html/body) | Fonts, metadata |
| `[locale]/layout.tsx` | None | Providers, i18n |
| `(app)/layout.tsx` | `px-4 pt-4 pb-20 max-w-*` | Navigation + padded main |
| `(public)/layout.tsx` | None (`<>{children}</>`) | Nothing - pages control own layout |

**When to add page-level spacing:**
- Extra `pb-*` for sticky mobile buttons
- `max-w-*` to constrain content width narrower than layout
- Specific margin between sections (`space-y-*`)

---

## Reference Implementations

- **Auth hook:** `apps/template-react/frontend/hooks/useAuth.ts`
- **Navigation config:** `apps/template-react/frontend/config/navigation.ts`
- **Layout config:** `apps/template-react/frontend/config/layout.ts`
- **AppShell:** `apps/template-react/frontend/components/shells/AppShell.tsx`
- **AppNav:** `apps/template-react/frontend/components/navigation/AppNav.tsx`
- **Profile page:** `apps/template-react/frontend/app/[locale]/(app)/profile/page.tsx`
- **Login page:** `apps/template-react/frontend/app/[locale]/(auth)/login/page.tsx`
- **Middleware:** `apps/template-react/frontend/middleware.ts`
- **Optimistic updates:** `apps/template-react/frontend/hooks/useUpdateUser.ts`
- **Logout hook:** `apps/template-react/frontend/hooks/useLogout.ts`
- **Generated hooks:** `apps/template-react/frontend/src/gen/hooks/`
- **Zustand stores:** `apps/template-react/frontend/src/store/`
