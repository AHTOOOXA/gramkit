# Changelog

gramkit is synced from a private production monorepo that runs on the same `core/`. Each entry covers one
sync and lists changes to `core/`, the two templates, `scripts/`, CI and the Claude Code setup. Entries are
grouped as **Added / Changed / Fixed / Breaking**; read **Breaking** before you pull a sync into an app
you built from a template.

## Unreleased — admin area (core admin API, admin tasks, broadcasts, marketing links, overview + analytics + daily digest, template-vue and template-react screens), seen_features composables

### Breaking (migrations required)

- New table `admin_audit_logs` (template-vue `b3a91c5d7e24`, template-react `c4d02e6f8a35`). An app copied from
  an earlier template needs its own: `make migration msg="admin audit log" APP=<app>`, review, `make upgrade`.
- New table `promotional_broadcasts` (template-vue `d5e13f7a9b46`, template-react `e6f24a8b0c57`). Same for an
  app copied from an earlier template: `make migration msg="promotional broadcasts" APP=<app>`, review, `make upgrade`.
- New table `marketing_links` (template-vue `f7a35c9e1d82`, template-react `a8b46d0f2e93`). Same for an app copied
  from an earlier template: `make migration msg="marketing links" APP=<app>`, review, `make upgrade`.

### Breaking (code)

- **The request transaction now commits before the response is sent.** FastAPI runs a `yield` dependency's
  exit after the response by default, so a client refetching right after a mutation could read pre-commit data
  and a failed commit still answered 200. Your app's `get_services` must depend on
  `Depends(get_repo, scope="function")` and `return` (not `yield`); endpoints whose `StreamingResponse`
  generator writes to the DB use `get_services_streaming` / `get_user_streaming` (request scope). The
  `test_session_scope.py` contract checks every route uses one scope.

- Mount core's admin router before your own: `from core.infrastructure.fastapi.routers import admin as core_admin`,
  then `routers=[..., core_admin.router, routers.admin.router]`.
- Add the delegators: `RequestsRepo.audit_log` / `.admin_users` and `RequestsService.audit_log` / `.admin` / `.admin_tasks`
  (`return self._core.<name>`). `BaseCompositionTests` now fails without them.
- Core's `GET /admin/users/{user_id}` catches any one-segment `/admin/users/<x>`, so app routes under
  `/admin/users/` need two segments (e.g. `/admin/users/{id}/notes`).
- Import your task module once at startup in `app/webhook/app.py`
  (`from app.services import admin_tasks as _admin_tasks  # noqa: F401`); that import is what registers
  the tasks. Registering two tasks with the same name raises `ValueError` at startup.
- No migration for admin tasks: runs are stored in `admin_audit_logs`.
- **Broadcasts:**
  - Add the delegators `RequestsRepo.promotional_broadcasts` and `RequestsService.broadcasts`;
    `BaseCompositionTests` enforces them.
  - Add `python-multipart` to your backend's `web` extra. The core admin router declares a multipart route
    (broadcast media upload), and FastAPI refuses to import it without the package, so the webhook fails at start.
  - Replace your `user_broadcast_job` with a re-export of core's
    (`from core.infrastructure.arq.jobs.broadcasts import user_broadcast_job`) and keep it in `job_functions`.
    It keeps the old name and `(broadcast_data, requester_telegram_id)` call shape.
  - Register a `"daily"` broadcast keyboard from `setup_infrastructure()` with
    `register_broadcast_keyboard("daily", builder)` (see `app/tgbot/keyboards/notification_keyboards.py`).
    Builders get `(button_text, locale)` and translate with `t(key, locale)`.
  - To deliver scheduled broadcasts, register core's `morning_notification_job` / `evening_notification_job`
    hourly (`cron(..., minute=0)`) and put core's `MorningPromotionalBroadcast` / `EveningPromotionalBroadcast`
    first in `get_*_notifications_with_promotions`. The templates now do this, with the example notifications
    left out of the lists, so a derived app's users get only the broadcasts you schedule.
  - The bot `/promo`, `/promo_list` and `/promo_cancel` commands are removed; use `/admin/broadcasts`.
    `/broadcast` stays and goes through the core job.
  - For `BaseBroadcastTests`, override `get_bot` in your `test_app` with `api_bot_mock()`
    (`core.testing.fixtures.bot`).
- **Marketing links:**
  - Add the delegators `RequestsRepo.marketing_links` and `RequestsService.marketing_links`
    (`return self._core.marketing_links`). `BaseCompositionTests` asserts both; without the service
    delegator the `/admin/marketing-links` endpoints answer 500 (`BaseMarketingLinksTests` catches that too).
  - Register core's `marketing_links_alerts_job` in your worker (`job_functions` and
    `cron(marketing_links_alerts_job, minute=20)`); it messages `RBAC__OWNER_IDS` and is silent without them.
  - List your app's own link codes (notification and broadcast buttons, e.g. `dailynotification`) in
    `app/domain/referrals.py` and pass them as `CoreRequestsService(internal_referal_ids=INTERNAL_REFERRAL_CODES)`,
    as the templates now do. Otherwise your own notification is stored as a user's acquisition source and
    shows up on the Marketing screen.
- **Overview, analytics, daily digest** (no migration):
  - `RequestsService.statistics` / `.analytics` and `RequestsRepo.analytics` must be core's
    (`return self._core.<name>`). `BaseCompositionTests` checks the types, so an app that keeps its own
    `StatisticsService` fails it (core's `/admin/statistics/overview`, digest job and `/stats` call core methods).
  - The template's `app/services/statistics.py` (`get_daily_statistics` / `format_statistics_message`) and its
    bot `/stats` handler are gone; `/stats` is now core's and answers only the owner who asked. An app's own
    `/stats` handler still wins, because app bot routers are included before core's.
  - `daily_admin_statistics_job` is now a re-export of core's (keep it in `job_functions` and the 01:55 UTC cron).
    The digest is a rich table (plain-HTML fallback), sent silently unless gathering failed.
  - Add your own numbers in `app/services/admin_metrics.py` (`register_admin_metrics()`, called from
    `setup_infrastructure()`); the templates ship it empty with an example.
- **Legacy admin stubs removed** (both templates): `GET /admin/stats`, `GET /admin/me` and
  `POST /admin/demo-action` are gone, with their schemas (`AdminStatsResponse`, `MyPermissionsResponse`,
  `DemoActionResponse`) and generated hooks (`useGetStatsAdminStatsGet`, `useGetMyPermissionsAdminMeGet`,
  `useDemoProtectedActionAdminDemoActionPost`). Use `GET /admin/meta/rbac` and `useAuth().isOwner` instead.
  template-react's RBAC demo page at `/admin` (`app/[locale]/(app)/admin/page.tsx` with `ProtectedActionDemo`,
  `StatsCards`, `YourAccessCard`) is replaced by the admin panel; `RbacDemo` on Profile stays.
  `app/webhook/routers/admin.py` stays as an empty router for your own admin endpoints (mounted after core's).

### Added

- **Core admin API** (`/admin/...`): users list (search, role/type filters, sorting, paging), user detail,
  a user's payments and subscriptions, gift / revoke subscription, role change and refund (owner-only), reset
  (owner-only, debug only), `GET /admin/meta/rbac`, and an **audit log** (`GET /admin/audit-log`,
  `GET /admin/audit-log/actions`) that every admin action writes to (`services.audit_log.record(...)`).
- **Admin tasks**: an `@admin_task(name, description, destructive=...)` registry
  (`core/services/admin_tasks.py`) for owner-run data fixes that execute inside the live webhook, plus
  `GET /admin/tasks` (admin) and `POST /admin/tasks/{name}` (owner; dry run by default). A run shares the
  request's transaction and is audit-logged as `admin_task:<name>` with `{"dry_run", "result"}`. The
  templates ship one read-only demo task, `users_overview`. `.claude/rules/prod-scripts.md` now says to
  write an admin task, not a script, for data fixes on a running server.
- `BaseAdminTests` contract suite (it also covers `/admin/tasks` with a probe task) and `admin_client` /
  `owner_client` fixtures (`core.testing`).
- **template-vue admin screens** at `/admin`: users, user detail (payments with Stars refund, subscriptions,
  actions), audit log with action filter and CSV export; mobile card layout. Sections and user-detail panels
  come from `app/admin/*` registries, so an app adds its own tabs without touching the shell. A **Tasks**
  section lists the registered tasks: dry run, then Apply with a confirm for destructive tasks, the result
  JSON, and a "Run history" link to the task's audit-log rows.
- `@core/composables`: `useAdminList` (filters/sort/paging state; not synced to the URL) and `useCsvExport`.
- **Broadcasts admin API** (10 endpoints under `/admin/broadcasts`): list, detail, delivery stats, create, edit,
  cancel, media upload, HTML formatting, preview to yourself, and an owner-only send-now (to a saved broadcast or inline). Scheduled
  broadcasts go out in the morning or evening slot of each user's local time until their deadline, top
  priority first. Every create / edit / cancel / send-now is audit-logged. Keyboard types are a registry
  (`register_broadcast_keyboard`); core ships `main` (an "open the app" button with your text).
- template-vue **Broadcasts** section: list (active by slot, completed), composer (text or photo / video /
  animation / document, Telegram HTML, keyboard, live preview, preview to yourself, owner send-now) and detail.
- `BaseBroadcastTests` contract suite and the `api_bot_mock()` helper; `MockBot` captures video / animation /
  document sends in `media`.
- `@core/utils`: `sanitizeTelegramHtml` (keeps only the tags Telegram renders).
- **Marketing links API** (`GET`/`POST /admin/marketing-links`, `PATCH /admin/marketing-links/{link_id}`): one
  acquisition code per placement, its `?startapp=r-<code>` and `?start=<code>` links, and per code: users (first
  touch, `users.referral_code`), activated, return after 1 / 7 / 30 days, payers, revenue (first 14 days and all
  time; purchases vs renewals), CAC, LTV, ROAS and payback. Codes seen on users before they were registered are
  listed too. Create / edit is audit-logged. Hourly owner alerts (`marketing_links_alerts_job`): first user,
  first payment, and a digest on days 1, 7 and 14 after the publish date.
- `MarketingLinksConfig`, passed as `CoreRequestsService(..., marketing_links_config=...)`: what counts as
  activation and return (query fragments with rows `(user_id, at)`), the digest wording and the currency rates
  (revenue is reported in RUB). Default activation is "opened the app" (`users.last_activity_date`), which is
  about 100% for Mini App links, because opening the link opens the app; it tells more for bot links. Count
  your app's key action instead to make the column useful.
- `BaseMarketingLinksTests` contract suite.
- `BaseSeenFeaturesTests` contract suite for `PATCH /users/me/seen-features` (merge, key validation, guest);
  both templates subclass it. It needs only `authenticated_client` and an unauthenticated `client`.
- `@core/composables`: `createSeenFeatures(registry, useStore)` (one-shot reveals, versioned "what's new", capped
  nudges on `user.seen_features`) and `mergeSeenFeatures`. template-vue ships a key registry
  (`src/config/seenFeatures.ts`), a `useSeenFeatures` store with `useReveal` / `useWhatsNew` / `useNudge` (the
  guest user never sees or writes), and a "what's new" note on `/demo`. No migration.
- template-vue **Marketing** section (`/admin/marketing`): create a code (with an optional placement, price and
  publish date), copy its Mini App and bot links, edit or archive it, and a sortable table of its numbers
  (cards on phones).
- **Admin Overview and money analytics** (core): `GET /admin/statistics/overview` (users with previous-window
  counts and DAU/WAU/MAU, per-currency revenue, product sales, active subscribers, plus the app's registered
  cards) and `/admin/analytics/revenue-timeseries`, `/revenue-kpis` (paying users, ARPPU, average payment, month
  and week growth per currency), `/subscription-trend`, `/subscription-breakdown` (status counts, gifted vs paid,
  30-day churn, net new) and `/mrr` (monthly equivalent per currency from your product catalog's prices).
  Currencies are never summed; Telegram Stars and gifts are non-cash series. The two heavy reads are Redis-cached.
- **Daily owner digest** (core `daily_admin_statistics_job`, 01:55 UTC): one table of the day next to the last
  7 days and their change, DAU/WAU/MAU, active subscriptions, warnings (no revenue, past-due subscriptions);
  `/stats` in the bot sends the same digest so far. Texts are in `core.admin.digest.*` (en, ru).
- `register_overview_card` / `register_digest_row` (`core.services.admin_metrics`): app tiles on the Overview and
  app rows, lines and warnings in the digest; callbacks get the session and the stat windows.
- `BaseAdminStatisticsTests` contract suite (overview + the 5 analytics endpoints).
- template-vue **Overview** (`/admin/overview`, now the first tab and where `/admin` lands): users with deltas and
  DAU/WAU/MAU, your registered cards grouped by section, active subscribers, per-currency revenue and units sold
  per product. **Analytics** (`/admin/analytics`): Revenue (KPIs, period growth, cash and non-cash series by day
  or week) and Subscriptions (MRR, health, weekly trend, by status, churn by reason). `groupOverviewCards` /
  `deltaPct` in `@core/composables`.
- `kubb.config.ts` reads `OPENAPI_PATH`, so `gen/` can be built from an `openapi.json` dump without a running stack.
- **template-react admin panel** at `/[locale]/admin`, at parity with template-vue's: Overview (the `/admin`
  landing tab), Users and user detail (gift / revoke, owner-only role change and reset, payments with an
  owner-only Stars refund, subscriptions), Analytics, Audit log (action filter, CSV), Tasks, Broadcasts (list,
  composer, detail, edit) and Marketing. Same hooks, gating and `admin.*` i18n key paths (en + ru) as the Vue
  screens; mobile card layout below `md`; charts on the template's shadcn `chart`. It lives in its own `(admin)`
  route group (`<AppShell variant="wide">` + `AdminShell` with the role guard). Extension points:
  `config/admin/app-sections.ts` (a tab; the page is a file under `app/[locale]/(admin)/admin/`) and
  `config/admin/app-userPanels.ts` (a user-detail tab, loaded with `React.lazy`). Every confirm keeps its dialog
  open with a spinner until the mutation resolves (`AdminActionDialog`).

### Changed

- Claude Code: the `qa` agent (`.claude/agents/qa.md`) is gone. Check a UI change in the browser with the
  Chrome DevTools MCP from `.mcp.json` (open the page, take screenshots) or `/verify`.

- Admin list search matches `%` and `_` literally.
- `PATCH /users/me/seen-features` answers 403 for the guest user. Every logged-out web visitor is the same
  guest row, so one visitor's dismissal would have hidden the moment for all of them.
- The bot's `/start <code>` no longer stores a code listed in `internal_referal_ids` as the user's acquisition
  source (the Mini App's `?startapp=r-<code>` already didn't).
- **One broadcast send path.** Scheduled slots, send-now, the bot's `/broadcast` and the preview all go through
  `MessageService.send_content` and the notification engine. Send-now supports all 5 media types, skips
  users who blocked the bot, logs a `notification_deliveries` row per user, counts sends on the saved row,
  and is safe to retry: a worker restarted mid-send skips users already delivered, so at most the batch in
  flight (100 users) can get a duplicate.
- Broadcast keyboards are built per recipient in their language and match the preview.
- Expired broadcasts are listed as completed; media uploads are capped at 10 MB for photos and 50 MB otherwise.
- **RBAC note:** an Admin can create or edit a scheduled broadcast that reaches the whole audience at the next
  slot, while send-now is Owner-only. Tighten the gate in your app if your admins shouldn't schedule mass
  messages.
- `promotional_broadcasts.created_by_user_id` (the creator's Telegram id) is `BIGINT`: newer Telegram ids don't
  fit 32 bits.
- Broadcast formatting: Telegram entity offsets are counted in UTF-16 (emoji no longer shift bold/links), text
  and link URLs are HTML-escaped, nested entities render correctly.
- `user_broadcast_job` has its own timeout (`USER_BROADCAST_JOB_TIMEOUT`, register it with
  `func(user_broadcast_job, timeout=...)`), sends outside DB transactions, and tells the requester when it
  stopped partway. Broadcast edit rejects explicit nulls (400) and keeps the formatting flag; cancel is
  idempotent.
- template-vue `gen/` regenerated with the current Kubb (client signature and docstring formatting).
- template-react `kubb.config.ts` reads `OPENAPI_PATH` and defaults to the local backend
  (`http://localhost:8003/openapi.json`) instead of a tunnel URL; its `gen/` is regenerated (it was older than
  the admin API). `/create_invite` is typed as the plain string the backend returns, and Profile → Friends
  shows the invite link again (it read a field that didn't exist).

## 2026-10 — sync from upstream (Jan→Oct 2026)

Covers upstream changes from 2026-01-05 to 2026-10-22.

### Breaking (migrations required)

Core has no migrations of its own: every app's Alembic history covers core's models. Both templates ship the
migrations below; **an app you copied from an earlier template needs its own** (`make migration
msg="core sync 2026-10" APP=<app>` after pulling, then review the autogenerated file and `make upgrade`).
Until it runs, every query on `users` fails with `column users.bot_blocked_at does not exist`.

- **Payments hardening** (template-vue `ed31a817017d`, template-react `a61fd7b47ea4`):
  - `payments.idempotency_key` (`varchar(64)`, nullable) + partial unique index `uq_payment_idempotency_key`
    (`WHERE idempotency_key IS NOT NULL AND status NOT IN ('FAILED','CANCELED')`).
  - `subscriptions.failed_renewal_count` (`int`, default 0), `subscriptions.last_renewal_attempt_at`,
    `subscriptions.payment_method_id` (`varchar(64)`, backfilled from `recurring_details->>'payment_method_id'`).
  - Partial unique index `uq_subscription_active_user` (one `ACTIVE`/`PAST_DUE`/`PENDING` subscription per
    user). The migration first marks older duplicate live subscriptions `EXPIRED` (keeps the latest per user).
- **Notifications, seen_features, referral codes** (template-react `2f53b2cebb7b`, template-vue `858ee0d3c8e4`):
  - new table `notification_deliveries` (+ index on `(user_id, sent_at)`),
  - `users.bot_blocked_at` (`timestamptz`, nullable), `users.seen_features` (`jsonb NOT NULL DEFAULT '{}'`),
  - drops `uq_users_referral_code` (referral codes are no longer unique: several users can share a source).
  - template-vue's migration also restores indexes its uuid7 migration had dropped (`friendships.user_id1/2`,
    `uq_friendship`, `payments.user_id`, `subscriptions.user_id`) and drops the redundant `ix_users_telegram_id`.
- New enum values (stored as strings, no DDL): `PaymentStatus.REFUNDED`, `PaymentEventType.PAYMENT_REFUNDED`,
  `SubscriptionStatus.PAST_DUE`. Code that switches on these enums must handle them; `PAST_DUE` still
  grants access.

### Breaking (code)

- **`admin_broadcast_job` moved to core** (`core.infrastructure.arq.jobs.admin_broadcast_job`). The per-app
  copies in `app/worker/jobs.py` and their i18n keys are gone; register the core job in your worker's
  `job_functions`.
- **Notification engine:** the engine picks the message key and keyboard per user, failed sends return a
  falsy `SendFailure` (`forbidden` / `bad_request` / `other`) instead of `False`, and recipients
  (`get_users_by_local_time`) skip users who blocked the bot or have no `telegram_id`. A core
  `notification_deliveries` repo (`NotificationDeliveryRepo`) was added to `CoreRequestsRepo`; give it a
  delegating `@cached_property` in your app's `RequestsRepo` (copy template-vue's).
- **`Payment.is_recurring`** now means "an automatic renewal charge" only and is never rewritten by the
  webhook (it used to flip to true for any recurring product).
- **`start_purchase` sells only `AVAILABLE_PRODUCTS`** (plus `TEST_PRODUCTS` in debug). A product kept only for
  renewals/refunds of old subscriptions resolves but can't be bought again.
- **Frontend majors (template-vue):** vue-router 5, pinia 4, vue-i18n 11, @vueuse 15, vue-sonner 2.
- **Claude Code setup replaced:** `.claude/commands/`, `.claude/shared/`, `.claude/skills/*` and the
  `developer-agent` / `testing-polish-agent` agents are gone. Path-scoped `.claude/rules/`, guard hooks, a `qa`
  agent and Claude Code's built-ins (`/code-review`, `Plan`, `Explore`, `Workflow`) replace them.
- Per-app `frontend/pnpm-lock.yaml` files were removed; the root `pnpm-lock.yaml` is the only lockfile.

### Added

- **Telegram Stars payments:** Stars subscriptions that renew and cancel correctly (first charge id, guard
  against late renewals), one-time Stars purchases, and Stars refunds (`refunded_payment`
  handler).
- **Optional product hooks** (`core/domain/products.py`): `invoice_text(locale)` (Stars invoice wording),
  `daily_purchase_limit` (purchases per user per 24 h) and `take_back(payment, …)` (what a refund revokes).
  A product without them still satisfies the `PaymentProduct` protocol.
- **YooKassa embedded widget:** embedded confirmation, widget language follows the app locale,
  `GET /payments/{payment_id}/status` with status reconcile (grants the entitlement if the webhook is late).
- **YooKassa hardening:** idempotency keys on every create (deterministic per subscription period for
  renewals), webhook re-fetches the payment instead of trusting the body, a renewal already `SUCCEEDED` this
  period is skipped, a dunning state machine for failed renewals (`PAST_DUE`, grace period, spaced retries),
  refund webhooks, and an owner alert when a provider webhook fails.
- **Notification engine:** `notification_deliveries` log (one row per attempt), batched reads for caps,
  `bot_blocked_at` set on `TelegramForbiddenError` (in a savepoint) and cleared on `/start` or app open,
  `plan_slot` (the read-only "who gets what" step shared by the cron and an admin preview), `get_streak_day`,
  `NotificationTemplate.send_to_user` (override to send a poll or photo), `MessageService.send_poll` and
  `MessageService.send_photo_bytes`.
- **`seen_features`:** `User.seen_features` JSONB + `PATCH /users/me/seen-features` with an atomic `||` merge and
  validated keys, for one-time reveals, coachmarks, "what's new" and capped nudges (`.claude/rules/seen-features.md`).
- **Telegram admin messages** (`core/infrastructure/telegram/admin_messages.py`): one sender with HTML escaping,
  an optional rich body, and a rich → HTML → plain fallback; formatting helpers (`fmt_money`, `fmt_ago`,
  `user_ref`, `tags`…); purchase / renewal / cancel alerts with customer context (joined, payments, LTV);
  `#hashtags` on every alert plus `#u_<handle>`; routine events silent, money and critical loud;
  `alert_owners()`.
- **Start announcements:** webhook and worker post a silent `🚀 <app> <version> · <service> started` to the
  owners once per process start in production (`create_worker_settings(version=…)`).
- **`GET /health`** returns `version` (the version passed to `create_api`) and `started_at`.
- **Backups:** `make backup-db APP=…` / `make restore-db file=… APP=…`; restore wipes and recreates the DB,
  loads older dumps (role and pg17-only directives stripped) and runs `alembic upgrade head`.
- **Analytics:** backend PostHog events for payments (method, failure reason), renewal results
  (`payment_succeeded` / `payment_failed` from the renewal job), referral tracking, return visits and person
  properties; frontend `usePostHog` registers `$app_version` when the app defines `VITE_APP_VERSION`.
- **Platform (Vue core):** `showConfirm`, `enableClosingConfirmation` / `disableClosingConfirmation`,
  `setBackgroundColor`, `setBottomBarColor` (Telegram only, no-ops on web).
- `RootPathMiddleware` for serving static files behind a reverse proxy with a path prefix; 1-year immutable
  cache for static images.
- PWA manifests for both templates (basePath-aware).
- Release workflow: `scripts/release.sh` + `make release-dev APP=… BUMP=…` / `make release-main APP=…`
  (dev first, main merged in a temporary worktree, tagged); `bump_version.py` keeps one source of truth for
  the app version.
- Claude Code: `.claude/rules/*`, `.claude/hooks/` (guard-bash, guard-edit, session-start), `qa` agent,
  `.mcp.json` (Chrome DevTools), `.worktreeinclude`.

### Changed

- Admin alerts were redesigned (contextual HTML instead of plain text); a daily digest can be built on the same
  sender.
- Debug panel: the Telegram-platform mock and "Login as" are independent, and the user chooser is always
  shown in dev (both templates).
- Re-engagement deep links no longer overwrite a user's acquisition source.
- Bot only creates users for real interactions, not for service updates (e.g. `my_chat_member`).
- `AppShell` (React) takes `hideNav` for full-screen routes; both shells pad for the bottom nav only when it
  is visible.
- Sentry no longer attaches request bodies (`max_request_body_size="never"`).
- Dependency bumps: Python security/minor updates, frontend minor/patch updates across the workspace.

### Fixed

- Backups fail loudly: `pg_dump` runs directly (its exit code is the result) instead of `pg_dump | gzip`, which
  sent 0-byte "successful" backups when `pg_dump` was missing; template-react's production image installs
  `postgresql-client`.
- Double-charging of subscriptions that were expired but still `ACTIVE`.
- Stars cancel uses the first charge id; refund notices; balance races in the payment path.
- API errors keep the backend's `message` and `code` for object details and 422 validation errors (Vue and
  React `classifyHttpError`).
- `/start` no longer crashes on an over-long referral code.
- Notifications: unknown languages, invalid timezones, a double-fired slot, retry after send failures.
- UUIDs are converted to strings in PostHog calls and JSON columns; PostHog init is skipped during SSR/SSG.
- `preloadImage` never rejects and times out after 10 s.
- Global exception handler logs unhandled errors; config adapters + script runner argparse fix.
- `process_invite` type annotation (UUID, not int).
- App-setup contract test tolerates the Starlette 1.x router shape; core's admin-message test passes in
  core-only CI.
