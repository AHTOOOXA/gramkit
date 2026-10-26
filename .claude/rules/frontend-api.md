---
paths:
  - "apps/*/frontend/src/**"
  - "apps/*/frontend/app/**"
  - "apps/*/frontend/hooks/**"
  - "apps/*/frontend/config/**"
  - "apps/*/frontend/components/**"
  - "apps/*/frontend/kubb.config.ts"
  - "core/frontend/**"
  - "core/frontend-react/**"
---

# Frontend API layer (Kubb + TanStack Query), all apps

Root `CLAUDE.md` already says: never edit `gen/`/`schema/`, server state lives in TanStack Query, call the API
only through generated hooks. This file covers how that works here.

## Codegen: `make schema APP=<app>`
- It runs `pnpm generate` (`kubb generate`) in `apps/<app>/frontend`, which writes `src/gen/{client,hooks,models}`.
  The backend has to be running because Kubb reads the live OpenAPI spec. The spec URL is in `kubb.config.ts`:
  - `template-vue`: `http://localhost:8002/openapi.json`. `template-react`: `http://localhost:8003/openapi.json`
    (the local backends).
- **Without a stack:** both templates' `kubb.config.ts` read `OPENAPI_PATH`. Dump `app.openapi()` to a file
  (`ENV_FILE=.env.test`, `RedisClient.__init__` patched like the tests' conftest, and assert `app.__file__` is
  the right template's package, since both backends are a package named `app`), then run
  `OPENAPI_PATH=<file> pnpm generate`. The committed `gen/` is raw Kubb output, so generate without prettier
  on `PATH`.
- **`output.clean: true` wipes `src/gen` before it fetches.** Sometimes Kubb stops with "fetch failed" and
  leaves hundreds of files deleted. After every run, check `git status src/gen`. If you see mass deletions,
  fix the backend or tunnel and run it again. Never commit a half-empty `gen/`.
- Commit the regenerated `src/gen` together with the backend change that caused it. If you bump a `@kubb/*`
  package, regenerate in that same commit too. Otherwise the next session inherits a huge unexplained diff.
- Kubb versions differ by stack: Vue apps use Kubb 4 (`@kubb/plugin-vue-query`) and React apps use Kubb 3
  (`@kubb/plugin-react-query`). The generated code differs slightly, but the rules below hold for both.
- Import types from `@gen/models`. `src/schema/api.d.ts` is an old artifact, and no app imports it.

## Generated hooks
- Names come from the FastAPI `operation_id`. The default is verbose: `GET /users/me` →
  `useGetCurrentUserUsersMeGet`, `PATCH /users/me` → `useUpdateCurrentUserUsersMePatch`. Routes that set an
  explicit `operation_id` on the FastAPI route get short names (`operation_id="list_items"` → `useListItems`). To find a hook, grep
  `src/gen/hooks/` for the URL.
- Query key helper = the operation name + `QueryKey`, with no `get`/`use` prefix added:
  `getCurrentUserUsersMeGetQueryKey()`, `getPaginatedItemsDemoItemsGetQueryKey(params)`.
- Import paths: Vue uses `@gen/hooks` (the barrel) or `@gen/hooks/useX`. React uses `@/src/gen/hooks` (the
  usual form) or `@gen/hooks`.
- **Query options go under `query:`**, and the per-request axios config goes under `client:`:
  ```ts
  useGetCurrentUserUsersMeGet({ query: { staleTime: 5 * 60_000 } })   // not { staleTime }
  useGetPaginatedItemsDemoItemsGet(params, { query: { enabled: ... } })  // params come first
  ```
- **Mutation variables are wrapped.** Path params sit next to `data`:
  ```ts
  updateUser({ data: { app_language_code: 'ru' } })
  updateItem({ item_id, data })
  ```
- Use the generated hook directly for a simple query or mutation. Write a focused `useX` composable or hook
  only when a mutation also needs an optimistic update, invalidation of several queries, a cache clear plus
  redirect, or the same config in 3+ places. There are no "god hooks" that fetch everything.

## Query keys and invalidation
- Kubb keys are objects, not strings: `[{ url: '/demo/items' }, params?]`. **`['orders']` matches
  nothing.** Always build keys with the generated `*QueryKey()` helpers.
- Keys match by prefix. Call the helper with no params to invalidate every variant of that endpoint. With
  params, it hits only that one variant.
- Don't write `predicate: q => q.queryKey[0].url === ...`. It's fragile. The one accepted exception is the admin
  user detail page (both templates): app-registered user panels own queries whose keys the page can't know, so
  after a mutation it invalidates every key whose `url` starts with `/admin/users/:user_id/`.
- On logout, call `queryClient.clear()`. Every app's `useLogout` already does this.

## Optimistic update (reference: `useUpdateUser`)
Vue: `apps/template-vue/frontend/src/app/composables/useUpdateUser.ts`. React:
`apps/template-react/frontend/hooks/useUpdateUser.ts`.
```ts
useUpdateCurrentUserUsersMePatch({ mutation: {
  onMutate: async ({ data }) => {
    await queryClient.cancelQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() });
    const previousUser = queryClient.getQueryData<UserSchema>(getCurrentUserUsersMeGetQueryKey());
    if (previousUser) queryClient.setQueryData(getCurrentUserUsersMeGetQueryKey(), { ...previousUser, ...data });
    return { previousUser };
  },
  onError: (_e, _v, ctx) => { if (ctx?.previousUser) queryClient.setQueryData(getCurrentUserUsersMeGetQueryKey(), ctx.previousUser); },
  onSuccess: () => queryClient.invalidateQueries({ queryKey: getCurrentUserUsersMeGetQueryKey() }),
}});
```

## Outside the generated client: `apiFetch` and `getSocketOptions`
Both live in the app's `kubb-config.ts`: Vue `src/config/kubb-config.ts` (import `@/config/kubb-config`),
React `config/kubb-config.ts` (import the same way). `configureApiClient()` in that file sets the base URL,
the `initData` header, the debug-only `Mock-Platform` header (login-as), and the error-classifying response
interceptor.
- **`apiFetch(path, init)`** is for streaming/SSE, and also for **multipart uploads**: the generated client
  forces `Content-Type: application/json`, which breaks the multipart boundary.
  It sends the same base URL, `initData`, `Mock-Platform` and `credentials: 'include'`.
  Never use a bare `fetch('/api/<app>/...')`.
  - `apiFetch` returns a raw `Response`. It skips the axios interceptor, so check `res.ok` yourself and throw
    through `classifyHttpError` if you want the usual error handling.
- **`getSocketOptions()`** returns `{ url, options }` for `io(url, options)`, with the correct socket path,
  `auth.initData`, `withCredentials` and 5 reconnect attempts. Don't build a socket.io URL by hand.
- Error classes and user-facing messages come from `@core/errors` (Vue) or `@tma-platform/core-react/errors`
  (React): `classifyHttpError`, `isApiError`, `getErrorMessage`. The full flow is in
  `.claude/rules/errors.md`.
