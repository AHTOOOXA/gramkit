# Phase 05: Worker Jobs & Statistics Service

**Focus:** Extract common jobs and StatisticsService with protocol-based typing

---

## Codebase Analysis

### Common Jobs (Identical Across All 4 Apps)

**File References:**
- `/Users/anton/tarot/apps/template/backend/src/app/worker/jobs.py` (lines 8-35)
- `/Users/anton/tarot/apps/template-vue/backend/src/app/worker/jobs.py` (lines 8-35)
- `/Users/anton/tarot/apps/template-react/backend/src/app/worker/jobs.py` (lines 8-35)
- `/Users/anton/tarot/apps/template-react/backend/src/app/worker/jobs.py` (lines 8-35)

**Jobs to Extract to Core:**

1. **admin_broadcast_job** (lines 8-35)
   - Sends broadcast messages directly to admin IDs via bot
   - Uses `settings.rbac.owner_ids` from config
   - No transaction needed (external API calls)
   - Returns `{"sent": count}`

2. **user_broadcast_job** (lines 39-161)
   - Broadcasts to all users with transaction split pattern
   - Transaction 1: Get all users and extract `(u.id, u.telegram_id)` tuples
   - NO transaction: Send messages via bot (external API, 30-250 seconds)
   - Transaction 2: Send completion notification to requester
   - Handles text and photo messages with optional formatting
   - **Note:** maxstat uses `u.user_id` instead of `u.id` (line 66 variation)

3. **send_delayed_notification** (lines 300-331)
   - Sends delayed Telegram notifications for demo purposes
   - Gets user by telegram_id, extracts language code
   - Uses i18n for localized messages
   - **Note:** maxstat parameter named `user_id` instead of `telegram_user_id` (line 234)

4. **daily_admin_statistics_job** (lines 263-296)
   - Gathers statistics via StatisticsService
   - Transaction 1: Get stats + format message
   - NO transaction: Send to admins via bot
   - Returns `{"sent": count}`

5. **charge_expiring_subscriptions_job** & **expire_outdated_subscriptions_job** (lines 164-187)
   - Already in core at: `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/subscriptions.py`
   - App jobs are wrappers that inject `products` dependency

### App-Specific Jobs to Keep

**File References:**
- `/Users/anton/tarot/apps/template/backend/src/app/worker/jobs.py` (lines 191-253)

**Jobs:**
1. **morning_notification_job** (lines 191-210) - tarot-specific notification logic
2. **evening_notification_job** (lines 214-233) - tarot-specific notification logic
3. **topup_daily_chat_messages_job** (lines 237-253) - tarot-specific balance logic
4. **test_error_job** (lines 257-259) - test/debug only

### StatisticsService Implementation

**Current Location (Identical in All 4 Apps):**
- `/Users/anton/tarot/apps/template/backend/src/app/services/statistics.py` (164 lines)
- `/Users/anton/tarot/apps/template-react/backend/src/app/services/statistics.py`
- `/Users/anton/tarot/apps/template-vue/backend/src/app/services/statistics.py`
- `/Users/anton/tarot/apps/template-react/backend/src/app/services/statistics.py`

**Key Methods:**
1. **get_daily_statistics()** (lines 21-101)
   - Calculates UTC day boundaries (2:00 AM UTC rollover)
   - Gathers: users (total, new, active by period), revenue, subscriptions
   - Uses repo methods: `users.get_*`, `payments.get_*`, `subscriptions.get_active_subscribers_count()`
   - Returns dict with nested structure (users, revenue, product_sales, subscriptions)

2. **format_statistics_message()** (lines 103-163)
   - Formats stats dict into Telegram message
   - Displays users (total, MAU, WAU, DAU, new metrics)
   - Displays subscriptions (active count)
   - Displays revenue (all-time and today, by currency)
   - Displays product sales (all-time and today, by product_id)

**Repository Dependencies:**
- `self.repo.users.get_users_count()` (line 43)
- `self.repo.users.get_new_users_count(start_date)` (line 44)
- `self.repo.users.get_updated_users_count(start_date, end_date)` (line 47)
- `self.repo.payments.get_total_revenue_by_currency()` (line 52)
- `self.repo.payments.get_revenue_by_all_currencies_and_date(start, end)` (line 53)
- `self.repo.payments.get_product_sales_stats()` (line 54)
- `self.repo.payments.get_product_sales_stats_by_date(start, end)` (line 55)
- `self.repo.subscriptions.get_active_subscribers_count()` (line 58)

**Extends:** `BaseService` (line 14) from `/Users/anton/tarot/app/services/base.py`

### Statistics Service Registration

**File:** `/Users/anton/tarot/apps/template/backend/src/app/services/requests.py`
- Line 159-161: StatisticsService cached property
- Line 15: Import statement

**Pattern:** Injected into RequestsService via composition, lazy-loaded via @cached_property

### Existing Core Job Patterns

**File:** `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/__init__.py`

**Already in Core:**
- `charge_expiring_subscriptions_job` (from subscriptions.py)
- `expire_outdated_subscriptions_job` (from subscriptions.py)
- `morning_notification_job` (from notifications.py) - app extends this
- `evening_notification_job` (from notifications.py) - app extends this
- `topup_daily_chat_messages_job` (from balance.py) - app extends this

**Core Infrastructure:**
- `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/balance.py`
- `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/notifications.py`
- `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/subscriptions.py`
- `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/backup.py`

**Decorator Pattern:** `@inject_context` wraps async job functions to inject `WorkerContext`

---

## Implementation Steps

### Step 1: Create Core Job Files

**File:** `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/broadcast.py`
- Copy `admin_broadcast_job` (from tarot jobs.py lines 8-35)
- Copy `user_broadcast_job` (from tarot jobs.py lines 39-161)
  - Use generic `u.id` and `u.telegram_id` for user tuple extraction
  - Keep transaction split pattern (DB -> API -> DB)

**File:** `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/statistics.py`
- Copy `daily_admin_statistics_job` (from tarot jobs.py lines 263-296)

**File:** `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/demo.py`
- Copy `send_delayed_notification` (from tarot jobs.py lines 300-331)
  - Rename parameter to `telegram_user_id` for consistency

### Step 2: Create Core StatisticsService

**File:** `/Users/anton/tarot/core/backend/src/core/services/statistics.py`
- Copy entire StatisticsService class from tarot (164 lines)
- Imports: `UTC`, `datetime`, `timedelta`, `BaseService`, `get_logger`
- Keep repository dependencies as-is (services.repo.users, services.repo.payments, etc.)

### Step 3: Update Core Job Exports

**File:** `/Users/anton/tarot/core/backend/src/core/infrastructure/arq/jobs/__init__.py`
- Add imports for: `admin_broadcast_job`, `user_broadcast_job` (from broadcast.py)
- Add imports for: `daily_admin_statistics_job` (from statistics.py)
- Add imports for: `send_delayed_notification` (from demo.py)
- Add to `__all__` list

### Step 4: Update Each App's jobs.py

**For all 4 apps:**

**File:** `apps/{app}/backend/src/app/worker/jobs.py`
1. Remove common jobs: `admin_broadcast_job`, `user_broadcast_job`, `daily_admin_statistics_job`, `send_delayed_notification`
2. Keep app-specific jobs: `morning_notification_job`, `evening_notification_job`, `topup_daily_chat_messages_job`, `test_error_job`
3. Add imports from core:
   ```python
   from core.infrastructure.arq.jobs import (
       admin_broadcast_job,
       user_broadcast_job,
       daily_admin_statistics_job,
       send_delayed_notification,
   )
   ```
4. Keep existing wrapper pattern for subscription jobs (already in core)

**Modified lines for tarot:**
- Keep lines 1-5 (imports + logger)
- Delete lines 8-35 (admin_broadcast_job)
- Delete lines 39-161 (user_broadcast_job)
- Keep lines 164-187 (subscription wrappers)
- Keep lines 190-253 (app-specific jobs)
- Delete lines 263-296 (daily_admin_statistics_job)
- Delete lines 300-331 (send_delayed_notification)
- Add core imports after line 5

### Step 5: Update Each App's RequestsService

**For all 4 apps:**

**File:** `apps/{app}/backend/src/app/services/requests.py`
- Line 15: Change import from `from app.services.statistics import StatisticsService` to `from core.services.statistics import StatisticsService`
- Keep line 159-161 cached property unchanged (StatisticsService still injected same way)
- All other services remain unchanged

### Step 6: Delete App-Specific Statistics Services

**For all 4 apps:**
- Delete `/apps/{app}/backend/src/app/services/statistics.py`
- Files to delete:
  - `/Users/anton/tarot/apps/template/backend/src/app/services/statistics.py`
  - `/Users/anton/tarot/apps/template-react/backend/src/app/services/statistics.py`
  - `/Users/anton/tarot/apps/template-vue/backend/src/app/services/statistics.py`
  - `/Users/anton/tarot/apps/template-react/backend/src/app/services/statistics.py`

---

## Success Criteria

- [ ] Core broadcast jobs created with correct transaction patterns:
  - admin_broadcast_job: 1 API call loop, no DB transaction
  - user_broadcast_job: 3 transaction phases (DB -> API -> DB)

- [ ] Core statistics job created:
  - daily_admin_statistics_job uses services.statistics service
  - Sends to settings.rbac.owner_ids

- [ ] Core demo job created:
  - send_delayed_notification uses i18n for localization
  - Gets user by telegram_id

- [ ] StatisticsService in core:
  - Inherits from BaseService
  - get_daily_statistics() returns correct nested dict structure
  - format_statistics_message() produces readable Telegram message
  - All repository calls match expected methods

- [ ] All 4 apps updated:
  - jobs.py imports from core: admin_broadcast_job, user_broadcast_job, daily_admin_statistics_job, send_delayed_notification
  - jobs.py keeps app-specific jobs unchanged
  - RequestsService imports StatisticsService from core instead of app
  - App statistics.py files deleted

- [ ] No breaking changes:
  - Job function signatures match exactly
  - Service methods return same data structures
  - Repository calls remain compatible
  - Lazy-loading pattern via @cached_property unchanged

- [ ] Line count savings:
  - Core: 4 new job files (~400 lines total) + 1 statistics file (164 lines)
  - Apps: Each removes ~200 lines from jobs.py + delete 164 lines statistics.py
  - Total: ~847 lines saved (per ARCHITECTURE.md)
