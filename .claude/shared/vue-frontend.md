# Vue Frontend Patterns

## Quick Checklist

- [ ] `<script setup>` syntax
- [ ] Server state → TanStack Query (generated hooks from `@gen/hooks/`)
- [ ] Client state → Pinia or local `ref()`
- [ ] Query options nested under `query: { ... }`
- [ ] Mutation variables wrapped in `{ data: ... }`
- [ ] Uses shadcn-vue (NOT PrimeVue)
- [ ] Composables follow `use*` naming
- [ ] `computed()` for derived state (not watchers)
- [ ] Event handlers for user actions (not watchers)

---

## TanStack Query + Kubb

### Critical Gotchas

**1. Query options must be nested:**
```typescript
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
```typescript
// ❌ WRONG
await updateUser({ app_language_code: 'ru' });

// ✅ CORRECT
await updateUser({ data: { app_language_code: 'ru' } });
```

**3. Hook names are verbose:**
```typescript
useGetCurrentUserUsersMeGet()       // GET /users/me
useUpdateCurrentUserUsersMePatch()  // PATCH /users/me
useGetProductsPaymentsProductsGet() // GET /payments/products
```

**4. Finding the right hook:**
```typescript
// 1. Browse: apps/{app}/frontend/src/gen/hooks/
// 2. Pattern: use{Method}{Path} → useGetCurrentUserUsersMeGet
// 3. Query keys: get{Path}QueryKey → getGetCurrentUserUsersMeGetQueryKey
```

### Basic Query

```typescript
import { useGetCurrentUserUsersMeGet } from '@gen/hooks/useGetCurrentUserUsersMeGet';

const { data: user, isLoading, error, isPending } = useGetCurrentUserUsersMeGet({
  query: {
    staleTime: 5 * 60 * 1000,
  }
});
```

### Loading & Error States

```vue
<template>
  <div>
    <!-- Error state -->
    <Alert v-if="error" variant="destructive">
      <AlertDescription>
        Error occurred
        <Button size="sm" @click="refetch()">Retry</Button>
      </AlertDescription>
    </Alert>

    <!-- Loading state -->
    <template v-else-if="isLoading">
      <Skeleton class="h-5 w-1/2" />
    </template>

    <!-- Data state -->
    <div v-else-if="data">
      {{ data.name }}
    </div>
  </div>
</template>
```

### Dependent Queries

```typescript
// Only fetch subscription when user exists
const { data: user } = useGetCurrentUserUsersMeGet();

const { data: subscription } = useGetSubscriptionSubscriptionsGet({
  query: {
    enabled: !!user.value, // Only fetch when user exists
  }
});
```

### When to Create Focused Composables

| Scenario | Pattern |
|----------|---------|
| Simple query | Generated hook directly |
| Simple mutation | Generated hook directly |
| Mutation + optimistic update | Create focused composable |
| Mutation + cache clearing + redirect | Create focused composable |
| Mutation + multi-query invalidation | Create focused composable |
| Same config in 3+ places | Consider focused composable |

### Optimistic Update Pattern

```typescript
import { useQueryClient } from '@tanstack/vue-query';
import { useUpdateCurrentUserUsersMePatch } from '@gen/hooks/useUpdateCurrentUserUsersMePatch';
import { getGetCurrentUserUsersMeGetQueryKey } from '@gen/hooks/useGetCurrentUserUsersMeGet';

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useUpdateCurrentUserUsersMePatch({
    mutation: {
      onMutate: async (variables) => {
        // Cancel outgoing queries
        await queryClient.cancelQueries({
          queryKey: getGetCurrentUserUsersMeGetQueryKey()
        });

        // Snapshot previous value
        const previousUser = queryClient.getQueryData(
          getGetCurrentUserUsersMeGetQueryKey()
        );

        // Optimistically update cache
        if (previousUser && variables.data) {
          queryClient.setQueryData(
            getGetCurrentUserUsersMeGetQueryKey(),
            { ...previousUser, ...variables.data }
          );
        }

        return { previousUser };
      },

      onError: (error, variables, context) => {
        // Rollback on error
        if (context?.previousUser) {
          queryClient.setQueryData(
            getGetCurrentUserUsersMeGetQueryKey(),
            context.previousUser
          );
        }
        toast.error('Failed to update');
      },

      onSuccess: () => {
        // Sync with server
        queryClient.invalidateQueries({
          queryKey: getGetCurrentUserUsersMeGetQueryKey()
        });
        toast.success('Updated!');
      },
    },
  });
}
```

### Cache Invalidation

**Always use generated `*QueryKey()` functions.** Kubb generates keys as `[{ url: '/path' }, ...params]`, not simple strings.

```typescript
// ✅ CORRECT: Use generated query key functions
import { getGetCurrentUserUsersMeGetQueryKey } from '@gen/hooks/useGetCurrentUserUsersMeGet';
import { getListOrdersOrdersGetQueryKey } from '@gen/hooks/useListOrdersOrdersGet';

// Invalidate specific query (no params)
queryClient.invalidateQueries({
  queryKey: getGetCurrentUserUsersMeGetQueryKey()
});

// Invalidate query with specific params
queryClient.invalidateQueries({
  queryKey: getListOrdersOrdersGetQueryKey({ status: 'active' })
});

// Invalidate all variants of a query (any params)
queryClient.invalidateQueries({
  queryKey: getListOrdersOrdersGetQueryKey()  // No params = matches all /orders queries
});

// Clear all cache (e.g., on logout)
queryClient.clear();
```

```typescript
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

```typescript
import { apiFetch } from '@/config/kubb-config';

// ✅ CORRECT: Uses same baseURL and auth headers as axios
const res = await apiFetch('/demo/stream');
const reader = res.body?.getReader();

// ❌ WRONG: Hardcoded URL, missing auth headers
const res = await fetch('/api/template/demo/stream');
```

`apiFetch` automatically includes:
- Correct `baseURL` from environment
- `initData` header for Telegram auth
- `Mock-Platform` header in debug mode
- `credentials: 'include'` for cookies

### WebSocket / Socket.io

For WebSocket connections, use `getSocketOptions()`:

```typescript
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
Client State → Pinia or ref()
```

**Server state:** Data from APIs (users, products, subscriptions)
**Client state:** UI state (theme, modals, form inputs)

```typescript
// ✅ Server state - TanStack Query
const { data: user } = useGetCurrentUserUsersMeGet();
const { data: subscription } = useGetSubscriptionSubscriptionsGet();

// ✅ Client state - Pinia
const uiStore = useUIStore();

// ✅ Client state - local ref
const isEditing = ref(false);
const selectedPlan = ref('');

// ✅ Derived from server state - computed
const isPremium = computed(() => subscription.value?.status === 'active');
```

### Pinia Store (Client State Only)

```typescript
export const useUIStore = defineStore('ui', () => {
  const isDarkMode = ref(false);
  const isModalOpen = ref(false);
  const activeTab = ref('home');

  return { isDarkMode, isModalOpen, activeTab };
});

// ❌ BAD: Server state in Pinia
export const useUserStore = defineStore('user', () => {
  const user = ref(null);
  const fetchUser = async () => { /* NO! Use TanStack Query */ };
});
```

---

## Reactivity Patterns

### ref vs reactive

**Default: Use `ref()`** - More flexible, fewer gotchas

```typescript
// ✅ ref for primitives
const count = ref(0);
const isActive = ref(true);

// ✅ ref for objects that might be reassigned
const user = ref<User | null>(null);
user.value = await fetchUser();

// ✅ reactive for grouped form state
const form = reactive({
  username: '',
  password: '',
});

// ❌ Destructuring reactive loses reactivity
const { username } = form; // Not reactive!

// ✅ Use toRefs for destructuring
const { username } = toRefs(form);
```

### computed vs watch

```typescript
// ✅ computed: Deriving values
const fullName = computed(() => `${firstName.value} ${lastName.value}`);
const completedTodos = computed(() => todos.value.filter(t => t.completed));

// ❌ BAD: Using watch like computed
const fullName = ref('');
watch([firstName, lastName], ([first, last]) => {
  fullName.value = `${first} ${last}`; // Should be computed!
});

// ✅ watch: Side effects on specific source
watch(userId, async (id) => {
  user.value = await fetchUser(id);
});

// ✅ watchEffect: Auto-tracking multiple deps
watchEffect(() => {
  localStorage.setItem('theme', theme.value);
});
```

### Event Handlers vs Watchers

```typescript
// ❌ BAD: Watcher for user action
watch(selectedLanguage, async (newLang) => {
  await saveLanguage(newLang);
});

// ✅ GOOD: Event handler
const handleLanguageChange = async (newLang: string) => {
  selectedLanguage.value = newLang;
  await saveLanguage(newLang);
};

// Template
<Select v-model="selectedLanguage" @update:modelValue="handleLanguageChange" />
```

---

## Common Pitfalls

### Mutating Arrays in Computed

```typescript
// ❌ BAD: Mutates original
const sorted = computed(() =>
  products.value.sort((a, b) => a.price - b.price) // MUTATES!
);

// ✅ GOOD: Create new array
const sorted = computed(() =>
  [...products.value].sort((a, b) => a.price - b.price)
);
```

### Async in Computed

```typescript
// ❌ BAD: Async computed
const user = computed(async () => await fetchUser()); // Won't work!

// ✅ GOOD: Use TanStack Query
const { data: user } = useGetCurrentUserUsersMeGet();
```

---

## shadcn-vue

**Location:** `apps/{app}/frontend/src/components/ui/`

```vue
<!-- Button with loading -->
<Button :disabled="isPending" @click="handleSubmit">
  <Loader2 v-if="isPending" class="mr-2 h-4 w-4 animate-spin" />
  {{ isPending ? 'Saving...' : 'Save' }}
</Button>

<!-- Select with event handler -->
<Select v-model="selectedLanguage" @update:model-value="handleLanguageChange">
  <SelectTrigger>
    <SelectValue />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="en">English</SelectItem>
    <SelectItem value="ru">Русский</SelectItem>
  </SelectContent>
</Select>

<!-- Dialog -->
<Dialog v-model:open="isOpen">
  <DialogTrigger asChild>
    <Button>Open</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Title</DialogTitle>
    </DialogHeader>
    <!-- content -->
  </DialogContent>
</Dialog>
```

---

## File Structure

```
apps/{app}/frontend/src/
├── gen/hooks/           # Generated TanStack Query hooks (DO NOT EDIT)
├── components/ui/       # shadcn-vue components
├── app/
│   ├── store/          # Pinia stores (client state only)
│   ├── composables/    # Custom composables (useUpdateUser, etc.)
│   ├── presentation/
│   │   ├── screens/    # Full page views
│   │   └── components/ # Reusable components
│   ├── router/
│   └── i18n/locales/   # en.json, ru.json
```

---

## Reference Implementations

- **Profile page:** `apps/template/frontend/src/app/presentation/screens/user/Profile.vue`
- **Optimistic updates:** `apps/template/frontend/src/app/composables/useUpdateUser.ts`
- **Paywall:** `apps/template/frontend/src/app/presentation/screens/payments/Paywall.vue`
- **Generated hooks:** `apps/template/frontend/src/gen/hooks/`
- **Pinia stores:** `apps/template/frontend/src/app/store/`
