# Phase 03: Authentication & Base Router

**Focus:** Extract base router endpoints and refactor auth code to use core SessionService

---

## Codebase Analysis

### Existing Core Infrastructure

**SessionService** (`core/backend/src/core/services/sessions.py:33-173`)
- Provides unified session management interface
- Methods:
  - `create_session(user_id, user_type, metadata)` → returns session_id (UUID string)
  - `validate_session(session_id)` → returns dict with user_id, user_type, created_at, last_accessed
  - `destroy_session(session_id)` → returns bool
- Configuration via `settings.session` with TTL management
- Uses Redis with configurable key prefixes and expiration

**Cookie Helpers** (`core/backend/src/core/infrastructure/session/cookies.py:18-68`)
- `set_session_cookie(response, session_id)` - Sets cookie with unified settings
- `clear_session_cookie(response)` - Clears session cookie
- `get_session_from_request(request)` - Extracts session ID from cookies
- Uses `settings.session` for secure cookie configuration (httponly, secure, samesite, domain)

**SessionSettings** (`core/backend/src/core/infrastructure/config/components.py:63-79`)
- Fields: `expire_days`, `cookie_secure`, `cookie_httponly`, `cookie_samesite`, `cookie_domain`
- Derived fields set by app: `cookie_name` (e.g., "tarot_session"), `key_prefix` (e.g., "tarot:session:")

### Duplicated Code in Apps

**tarot/auth.py** (`apps/template/backend/src/app/webhook/auth.py:212-292`)
- Session functions (create_session, validate_session, destroy_session) at lines 212-291
- Set/clear cookie functions at lines 294-319
- Line 28: Hard-coded `SESSION_COOKIE_NAME = f"{settings.app_name}_session"`
- Line 28: Hard-coded `SESSION_KEY_PREFIX = f"{settings.app_name}:session:"`
- Duplicate Redis initialization at line 31: `session_redis = RedisClient(settings.redis)`
- All functions use identical logic to core SessionService

**Telegram Authentication** (`apps/template/backend/src/app/webhook/auth.py:54-155`)
- `TelegramAuthenticator` class (lines 71-155) - KEEP IN CORE (see Phase 04)
- `TelegramUser` dataclass (lines 35-51) - KEEP IN CORE
- Helper functions (generate_secret_key, get_telegram_authenticator) - KEEP IN CORE

**User Authentication** (`apps/template/backend/src/app/webhook/auth.py:533-582`)
- `get_user()` dependency (lines 533-582) - KEEP IN APPS (app-specific auth flow)
- `_authenticate_telegram()`, `_authenticate_session()`, `_get_mock_guest_user()` - KEEP IN APPS
- These depend on app-specific services and business logic

### Base Router Endpoints

**tarot/routers/base.py** (`apps/template/backend/src/app/webhook/routers/base.py:20-68`)
- 4 endpoints identical across all apps:
  - GET `/friends` - Rate-limited (SOFT_LIMIT), returns list[UserSchema]
  - POST `/add_friend` - Rate-limited (HARD_LIMIT), takes friend_id: UUID
  - GET `/create_invite` - Rate-limited (HARD_LIMIT), returns str
  - POST `/process_start` - Rate-limited (SOFT_LIMIT), takes StartParamsRequest

**maxstat/routers/base.py** (`apps/template-react/backend/src/app/webhook/routers/base.py:59-80`)
- Same 4 endpoints, BUT `/process_start` has cookie override logic (lines 70-78):
  ```python
  if result.current_user.is_onboarded:
      response.set_cookie(key="user_onboarded", value="true", ...)
  ```
- This is APP-SPECIFIC behavior (maxstat only) → implement via dependency override or hook

### Auth.py After Refactor (target: ~150 lines)

**REMOVE:**
- `create_session()`, `validate_session()`, `destroy_session()` → use SessionService
- `set_session_cookie()`, `clear_session_cookie()` → use core.infrastructure.session
- Hard-coded SESSION_COOKIE_NAME, SESSION_KEY_PREFIX, session_redis initialization

**KEEP:**
- `TelegramAuthenticator`, `TelegramUser`, `generate_secret_key()` (move to core in Phase 04, but keep imports)
- `get_user()` dependency with its auth flow logic
- `_authenticate_telegram()`, `_authenticate_session()`, `_get_mock_guest_user()`
- `get_mock_guest_user()` constant function
- `MOCK_GUEST_USER_ID` constant

### App.py Integration Pattern

**tarot/app.py** (`apps/template/backend/src/app/webhook/app.py:58-107`)
- Currently imports: `routers.base.router`, `routers.demo.router`, etc. (line 72, 77)
- After extraction: Import `base.router` from core instead
- Already uses `app.dependency_overrides[core_deps.get_user] = app_get_user` (line 106)
- After extraction: Add override for SessionService if needed (likely not, as it's injected via services)

### Cookie Override Pattern (maxstat-specific)

**maxstat/base.py** has `Response` parameter in `/process_start` endpoint (line 63)
- Sets "user_onboarded" cookie when `result.current_user.is_onboarded`
- After extraction: Use dependency injection to override `process_start` implementation or add app-specific hook
- **Constraint from CLAUDE.md**: "NO factory functions for routers" → use `app.dependency_overrides`

---

## Implementation Steps

### Step 1: Extract Base Router to Core
- **File:** Create `core/backend/src/core/infrastructure/fastapi/routers/base.py`
- **Source:** Copy from `apps/template/backend/src/app/webhook/routers/base.py` (lines 1-68)
- **Modifications:**
  - Keep 4 endpoints unchanged (identical across all apps)
  - Keep all imports (they're from core/app services already)
  - Don't override `/process_start` cookie logic yet (will be handled via app-specific hook)

### Step 2: Create process_start Hook for maxstat
- **File:** `core/backend/src/core/infrastructure/fastapi/routers/base.py` (same file)
- **Add:** Protocol or callback for app-specific `/process_start` response handling
- **Pattern:**
  ```python
  # At module level
  ProcessStartHookProtocol = Callable[[Any, UserSchema], Awaitable[None]]
  _process_start_hook: ProcessStartHookProtocol | None = None

  def set_process_start_hook(hook: ProcessStartHookProtocol) -> None:
      global _process_start_hook
      _process_start_hook = hook
  ```
- **In endpoint:**
  ```python
  result = await services.start.process_start(user, start_params)
  if _process_start_hook:
      await _process_start_hook(response, result)
  return result
  ```

### Step 3: Refactor tarot/auth.py
- **File:** `apps/template/backend/src/app/webhook/auth.py`
- **Remove lines 212-319:** All session functions and cookie functions
- **Replace with imports:**
  ```python
  from core.infrastructure.session import (
      set_session_cookie,
      clear_session_cookie,
      get_session_from_request,
  )
  from core.services.sessions import SessionService
  ```
- **Update line 448-499 (`_authenticate_session`):**
  - Remove direct `validate_session()` calls
  - Get SessionService from `services.sessions` (provided by app's RequestsService)
  - Call `await services.sessions.validate_session(session_id)`
- **Remove lines 28:** Hard-coded SESSION_COOKIE_NAME, SESSION_KEY_PREFIX, session_redis

### Step 4: Update tarot/app.py
- **Import base router from core:**
  ```python
  from core.infrastructure.fastapi.routers import base  # NEW
  ```
- **Update routers list in create_api() call (line 63-78):**
  - Change `routers.base.router` → `base.router`
- **No dependency override needed** (SessionService injected via services already)

### Step 5: Refactor maxstat/auth.py
- **Same as Step 3** (identical tarot/auth.py)
- **Update lines 448-499** to use `services.sessions`

### Step 6: Update maxstat/app.py
- **Same as Step 4**
- **Add hook setup for cookie override:**
  ```python
  # After create_api() call
  from core.infrastructure.fastapi.routers.base import set_process_start_hook

  async def maxstat_process_start_hook(response: Response, result: StartData) -> None:
      if result.current_user.is_onboarded:
          response.set_cookie(
              key="user_onboarded",
              value="true",
              path="/",
              max_age=31536000,
              httponly=False,
              samesite="lax",
          )

  set_process_start_hook(maxstat_process_start_hook)
  ```

### Step 7: Refactor template-react/auth.py
- **Same refactoring as tarot/auth.py** (Step 3)
- **If has /process_start endpoint:** Check if it has cookie logic, add to hooks if needed

### Step 8: Refactor template-vue/auth.py
- **Same refactoring as tarot/auth.py** (Step 3)
- **If has /process_start endpoint:** Check if it has cookie logic, add to hooks if needed

### Step 9: Update Remaining App.py Files
- **template-react/app.py** (same as Step 4)
- **template-vue/app.py** (same as Step 4)

### Step 10: Delete App-Specific Base Routers
- Delete `apps/template/backend/src/app/webhook/routers/base.py`
- Delete `apps/template-react/backend/src/app/webhook/routers/base.py`
- Delete `apps/template-vue/backend/src/app/webhook/routers/base.py`
- Delete `apps/template-react/backend/src/app/webhook/routers/base.py`

### Step 11: Update Core's __init__.py Exports
- **File:** `core/backend/src/core/infrastructure/fastapi/routers/__init__.py`
- **Add:** `from core.infrastructure.fastapi.routers import base`
- **Export in __all__**

---

## Success Criteria

### Extraction Complete
- [ ] `core/backend/src/core/infrastructure/fastapi/routers/base.py` exists (57 lines)
- [ ] Core base.py contains all 4 endpoints: /friends, /add_friend, /create_invite, /process_start
- [ ] All rate limiting, dependencies, exceptions preserved
- [ ] Core routers __init__.py exports `base` module

### Session Refactoring Complete
- [ ] All 4 apps' auth.py import from `core.infrastructure.session` for cookie functions
- [ ] All 4 apps' auth.py use `services.sessions` (SessionService) for validation
- [ ] No direct Redis initialization in any app's auth.py
- [ ] No hard-coded SESSION_COOKIE_NAME or SESSION_KEY_PREFIX in any app's auth.py
- [ ] `get_user()` dependency still works identically (unit tests pass)
- [ ] Session authentication still works in integration tests

### App Integration Complete
- [ ] All 4 apps import base router from core
- [ ] `/friends`, `/add_friend`, `/create_invite`, `/process_start` endpoints accessible on all apps
- [ ] maxstat's "user_onboarded" cookie logic works via hook
- [ ] No duplicate code between tarot/auth.py and other app auth.py files

### Tests Pass
- [ ] `make test APP=tarot` - All tests pass
- [ ] `make test APP=template-react` - All tests pass
- [ ] `make test APP=template-vue` - All tests pass
- [ ] `make test APP=maxstat` - All tests pass
- [ ] Session authentication flows work correctly

### Code Quality
- [ ] `make lint APP=tarot` - No lint errors
- [ ] `make lint APP=template-react` - No lint errors
- [ ] `make lint APP=template-vue` - No lint errors
- [ ] `make lint APP=maxstat` - No lint errors
- [ ] No circular imports (core doesn't import from app)

### Deprecation
- [ ] All 4 app base.py routers removed from file system
- [ ] App-specific session functions removed (no dead code)
- [ ] ~1,000 lines of duplicated session/base router code removed

---

## Dependencies & Constraints

**Depends On:**
- Phase 01 (exceptions in place)
- SessionService already exists in core (implemented)
- Cookie helpers already in core (implemented)

**Blocked By:**
- None

**Related To Phase 04:**
- Will extract TelegramAuthenticator to core later
- Currently kept in apps but will be refactored

**CLAUDE.md Constraints:**
- NO factory functions for routers → use `app.dependency_overrides` for maxstat cookie hook
- NO `if TYPE_CHECKING:` imports
- NO importing app modules from core
- Session validation must use `datetime.now(UTC)` (already in SessionService)
