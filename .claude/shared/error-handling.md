# Error Handling Guide

Minimal error handling for FastAPI backend + React/Vue frontend.

## Architecture

```
Backend (FastAPI)              Frontend (TanStack Query)
─────────────────              ─────────────────────────
HTTPException                  axios interceptor
    ↓                              ↓
{"detail": "msg"}    →        classifyHttpError(status, body)
                                   ↓
                              ApiError { message, status, recoverable }
                                   ↓
                              retry if recoverable, else show to user
```

## Backend: FastAPI Errors

### Pattern

Always use `HTTPException` with string detail:

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="User not found")
raise HTTPException(status_code=400, detail="Invalid email format")
raise HTTPException(status_code=409, detail="Email already registered")
```

### Response Format

```json
{"detail": "User not found"}
```

### Status Code Reference

| Code | When to Use | Recoverable? |
|------|-------------|--------------|
| 400 | Bad request | No |
| 401 | Not authenticated | No |
| 403 | Not authorized | No |
| 404 | Not found | No |
| 409 | Conflict | No |
| 422 | Validation error | No |
| 429 | Rate limited | Yes (auto-retry) |
| 500 | Server error | Yes (auto-retry) |
| 502/503/504 | Gateway error | Yes (auto-retry) |

## Frontend: Simplified Error System

### ApiError Interface

```typescript
interface ApiError extends Error {
  status: number;      // HTTP status code (0 for network errors)
  recoverable: boolean; // Should TanStack Query retry?
}
```

### Core Functions

```typescript
// Classify HTTP error → ApiError
classifyHttpError(status: number, body?: Record<string, unknown>): ApiError

// Classify network error → ApiError
classifyNetworkError(error: Error): ApiError

// Get message from any error
getErrorMessage(error: unknown): string

// Type guard
isApiError(error: unknown): error is ApiError
```

### Recoverability Logic

Simple rule: **server errors can be retried, client errors cannot.**

```typescript
const recoverable = status >= 500 || status === 429 || status === 0;
```

| Status | Recoverable | Reason |
|--------|-------------|--------|
| 4xx | No | Client error - retrying won't help |
| 429 | Yes | Rate limited - wait and retry |
| 5xx | Yes | Server error - may recover |
| 0 | Yes | Network error - may recover |

## TanStack Query Integration

### Retry Configuration

```typescript
// React: app/providers.tsx
// Vue: src/main.ts

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (isApiError(error) && !error.recoverable) {
          return false; // Don't retry 4xx errors
        }
        return failureCount < 3; // Retry others up to 3 times
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
    },
    mutations: {
      retry: false, // User retries manually
    },
  },
});
```

### Axios Interceptor

Error classification happens in axios interceptor (kubb-config.ts):

```typescript
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      throw classifyNetworkError(error);
    }
    throw classifyHttpError(error.response.status, error.response.data);
  }
);
```

## Component Patterns

### Pattern 1: Query with Inline Error

```typescript
// React
function FriendsSection() {
  const { data, error, refetch } = useGetFriends();

  if (error) {
    return (
      <Alert variant="destructive">
        {getErrorMessage(error)}
        <Button onClick={() => refetch()}>Retry</Button>
      </Alert>
    );
  }
  return <FriendsList data={data} />;
}
```

```vue
<!-- Vue -->
<template>
  <Alert v-if="error" variant="destructive">
    {{ getErrorMessage(error) }}
    <Button @click="refetch()">Retry</Button>
  </Alert>
  <FriendsList v-else :data="data" />
</template>

<script setup>
const { data, error, refetch } = useGetFriends();
</script>
```

### Pattern 2: Mutation with Toast

```typescript
// React
function PaymentButton() {
  const { mutateAsync } = useStartPayment();

  const handlePay = async () => {
    try {
      await mutateAsync(data);
      router.push('/success');
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };
}
```

```vue
<!-- Vue -->
<script setup>
const { mutateAsync } = useStartPayment();

const handlePay = async () => {
  try {
    await mutateAsync({ data });
    router.push('/success');
  } catch (error) {
    toast.error(getErrorMessage(error));
  }
};
</script>
```

### Pattern 3: Form with Inline Error

```typescript
// React
function ContactForm() {
  const [error, setError] = useState<string | null>(null);
  const { mutateAsync } = useSubmitContact();

  const onSubmit = async (data) => {
    setError(null);
    try {
      await mutateAsync({ data });
      toast.success('Sent!');
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  return (
    <form onSubmit={onSubmit}>
      {error && <Alert variant="destructive">{error}</Alert>}
      {/* fields */}
    </form>
  );
}
```

### Pattern 4: Auth-Aware Handling

```typescript
function ProtectedPage() {
  const { error } = useGetUser();
  const status = isApiError(error) ? error.status : 0;

  if (status === 401) {
    return <Redirect to="/login" />;
  }
  if (error) {
    return <ErrorPage message={getErrorMessage(error)} />;
  }
}
```

## Quick Reference

### Imports

```typescript
// React
import { getErrorMessage, isApiError } from '@tma-platform/core-react/errors';

// Vue
import { getErrorMessage, isApiError } from '@core/errors';
```

### Cheatsheet

```typescript
// Get message from any error
getErrorMessage(error)  // "User not found"

// Check if ApiError
if (isApiError(error)) {
  error.status      // 404
  error.recoverable // false
}

// Show toast on error
catch (error) {
  toast.error(getErrorMessage(error));
}

// Inline error with retry
if (error) {
  return <Alert>{getErrorMessage(error)} <Button onClick={refetch}>Retry</Button></Alert>;
}
```

## File Reference

| File | Purpose |
|------|---------|
| `core/frontend-react/src/errors/` | React error utilities |
| `core/frontend/src/errors/` | Vue error utilities |
| `apps/*/frontend/**/kubb-config.ts` | Axios interceptor |
| `apps/*/frontend/**/providers.tsx` or `main.ts` | Query retry config |

## Design Principles

1. **Minimal** - Only what's used: message, status, recoverable
2. **Backend decides message** - Frontend just displays `detail`
3. **Status code = classification** - No complex enums needed
4. **Component decides UI** - Toast vs inline vs redirect is context-dependent
5. **Let TanStack Query handle retries** - Don't reinvent retry logic

## Do's and Don'ts

### Backend

```python
# DO: Simple HTTPException
raise HTTPException(status_code=404, detail="User not found")

# DON'T: Complex error objects
raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", ...})
```

### Frontend

```typescript
// DO: Handle error in component
if (error) return <Alert>{getErrorMessage(error)}</Alert>;

// DON'T: Ignore error state
const { data } = useQuery();  // error silently ignored!

// DO: Wrap mutations in try/catch
try { await mutateAsync(data); } catch (e) { toast.error(getErrorMessage(e)); }

// DON'T: Let mutations fail silently
await mutateAsync(data);  // Error disappears!
```
