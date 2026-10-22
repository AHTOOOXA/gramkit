---
paths:
  - "core/frontend/src/errors/**"
  - "core/frontend-react/src/errors/**"
  - "apps/*/frontend/src/config/kubb-config.ts"
  - "apps/*/backend/src/app/exceptions.py"
  - "apps/*/backend/src/app/webhook/routers/**"
  - "core/backend/src/core/infrastructure/fastapi/routers/**"
---

# Errors: API → UI

## Backend
- Domain errors subclass `BackendException` (`apps/<app>/backend/src/app/exceptions.py`). Each carries
  `message`, `name`, and `code` (the class name, e.g. `NoChatMessagesError`).
- **Routers translate them to `HTTPException`**. No global handler is registered: `create_exception_handler`
  in `webhook/app.py` exists but its registration is commented out. See `routers/base.py` and `routers/demo.py`.
- `detail` comes in two shapes, and the frontend reads both:
  - `detail="Not found"`: plain text. Use it when the UI only needs a message.
  - `detail={"code": "NoChatMessagesError", "message": str(e)}`: use it when the UI must branch on *which*
    error happened (e.g. two different 402 "out of credits" errors). Keep `code` = the exception class name.
  - Other keys in an object `detail` (e.g. `{"dry_run": …, "result": …}` in admin) are fine for admin-only
    endpoints, but the UI then shows `Request failed (<status>)`, so include a `message` if a user sees it.
- Unhandled exceptions become core's `500 {"detail": str(exc)}`. Streaming endpoints can't change the status
  mid-stream, so they send an error line in the stream instead.
- `message` reaches the user as-is. Write it as user-facing text, or map `code` to an i18n key in the UI.
- Status codes: 4xx = the client's fault, never retried; 429/5xx/network = retried by TanStack Query;
  402 = out of credits/limit (the app shows the paywall or refetches the balance).

## Frontend (`@core/errors` for Vue, `@tma-platform/core-react/errors` for React)
- The axios interceptor in `apps/<app>/frontend/src/config/kubb-config.ts` turns every failure into an
  `ApiError` through `classifyHttpError(status, body)` / `classifyNetworkError(error)`.
- `ApiError`: `message`, `status` (0 = network), `recoverable` (5xx/429/0), and optional `code` (from
  `detail.code`). `message` is taken from a string `detail`, from `detail.message`, from the first
  `detail[].msg` (422 validation) or from `body.message`, falling back to `Request failed (<status>)`.
- Branch on `isApiError(e) && e.code === 'NoChatMessagesError'` (or on `e.status === 402`), not on message text.
- Retries: `main.ts` (Vue) / providers (React) retry queries only while `recoverable`; mutations never retry.
- Every query renders its `error` state and every `mutateAsync` sits in a try/catch with a toast or inline
  message (`getErrorMessage(e)`). Never let a mutation fail silently.
- Unhandled frontend errors go to Sentry and to PostHog as `frontend_error`.
