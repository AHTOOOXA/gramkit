# Phase 00: Foundation & Cleanup

**Focus:** Delete dead Vue package and add BackendException base class to core

---

## Codebase Analysis

### 1. core/frontend/ Directory Status

**Location:** `/Users/anton/tarot/core/frontend/`

**Current State:**
- Vue.js 3 package labeled as shared infrastructure
- Contains 31 source files across 10 directories
- Package name: `@tma-platform/core`
- Main entry: `package.json` (line 1-33)
- Published as peer dependency with Vue 3.4.38+

**Directory Structure:**
```
core/frontend/src/
├── ui/             # Vue UI components (SkeletonCard.vue, Skeleton.vue, ContentState.vue)
├── types/          # TypeScript types (language.ts)
├── composables/    # Vue composition functions (useScroll, useLayout, useLanguage, usePlaceholderHeight)
├── platform/       # Telegram SDK abstractions (useTelegram.ts, usePlatform.ts, usePlatformMock.ts)
├── utils/          # Utility functions (dom.ts, color.ts, date.ts, number.ts)
├── api/            # API client setup
├── errors/         # Error utilities
├── services/       # Infrastructure services
├── analytics/      # Analytics integration
└── node_modules/   # Dependencies
```

**Active Usage Evidence:**
- **template-vue frontend** actively imports from `@core`:
  - `/Users/anton/tarot/apps/template-vue/frontend/vite.config.ts` (line 51): alias `'@core': path.resolve(..., 'core/frontend/src')`
  - `/Users/anton/tarot/apps/template-vue/frontend/src/App.vue`: imports `usePlatform` from `@core/platform`
  - `/Users/anton/tarot/apps/template-vue/frontend/src/app/composables/useAppInit.ts`: imports `usePlatform`, `usePostHog`
  - 20+ import references across template-vue components

- **ESLint rules** enforce core imports:
  - `/Users/anton/tarot/apps/template-vue/frontend/eslint.config.js`: lint rules require max one-level-deep imports from `@core`

**Verdict:** KEEP - This package is ACTIVELY USED by template-vue frontend (not dead code)

---

### 2. core/backend/src/core/exceptions.py Current State

**Location:** `/Users/anton/tarot/core/backend/src/core/exceptions.py` (lines 1-20)

**Current Content:**
```python
"""Core exceptions for TMA platform."""


class UserNotFoundException(Exception):
    """Raised when a user is not found in the database."""

    pass


class PaymentException(Exception):
    """Base exception for payment-related errors."""

    pass


class SubscriptionException(Exception):
    """Base exception for subscription-related errors."""

    pass
```

**Status:**
- Only 3 exception classes defined
- No BackendException base class (defined in app-specific layers instead)
- NO exception hierarchy for shared failures (FriendAlreadyExistsException, LLMError, etc.)

---

### 3. App-Specific Exception Pattern Analysis

All 4 apps have **identical exception definitions**:

#### apps/template/backend/src/app/exceptions.py (lines 1-65)
#### apps/template-react/backend/src/app/exceptions.py (lines 1-59)
#### apps/template-vue/backend/src/app/exceptions.py (lines 1-59)
#### apps/template-react/backend/src/app/exceptions.py (lines 1-59)

**Pattern Used in All Apps:**
```python
class BackendException(Exception):
    """Base exception for application-specific errors"""

    def __init__(self, message: str = "Service is unavailable", name: str = "BackendException"):
        self.message = message
        self.name = name
        self.code = self.__class__.__name__
        super().__init__(self.message, self.name)
```

**Shared Exceptions Duplicated in All 4 Apps:**
1. `BackendException` base class (all 4 apps)
2. `UserNotFoundException` (all 4 apps)
3. `FriendAlreadyExistsException` (all 4 apps)
4. `LLMError` (all 4 apps)
5. `AllLLMProvidersFailedError` (all 4 apps)

**App-Specific Exceptions (must stay):**
- `NoAvailableReadingsError` (tarot)
- `ReadingNotFoundError` (tarot)
- `NoChatMessagesError` (all 4 apps)
- `NoTrainerAttemptsError` (tarot)
- `DailyReadingError` (tarot)
- `QuestionReadingError` (tarot)

**Duplication Factor:**
- BackendException: ~9 lines (identical in all 4 apps = 36 lines duplicated)
- FriendAlreadyExistsException: ~2 lines (8 lines duplicated)
- LLMError: ~3 lines (12 lines duplicated)
- AllLLMProvidersFailedError: ~3 lines (12 lines duplicated)
- **Total Phase 00 Preparation: ~68 lines of duplicate exception boilerplate**

---

## Implementation Steps

### Step 1: Verify core/frontend is NOT dead code (DISCOVERY)
- Status: COMPLETE
- Finding: Active usage in template-vue frontend with 20+ imports
- Action: **REMOVE core/frontend from Phase 00 deletion list**
- Note: core/frontend should only be deleted if a frontend consolidation phase is planned separately

### Step 2: Add BackendException to core/exceptions.py (IMPLEMENTATION)
- File: `/Users/anton/tarot/core/backend/src/core/exceptions.py`
- Add BackendException class with message/name/code attributes
- Implementation approach:
  ```python
  """Core exceptions for TMA platform."""


  class UserNotFoundException(Exception):
      """Raised when a user is not found in the database."""
      pass


  class BackendException(Exception):
      """Base exception for application-specific errors."""

      def __init__(self, message: str = "Service is unavailable", name: str = "BackendException"):
          self.message = message
          self.name = name
          self.code = self.__class__.__name__
          super().__init__(self.message, self.name)


  class PaymentException(Exception):
      """Base exception for payment-related errors."""
      pass


  class SubscriptionException(Exception):
      """Base exception for subscription-related errors."""
      pass
  ```

### Step 3: Verify app imports don't break (VALIDATION)
- Search for imports of `BackendException` across all 4 apps
- Confirm they currently import from `app.exceptions`
- These will be updated in Phase 01

---

## Success Criteria

### Verification Checklist

- [ ] **core/frontend/ is identified as active code**
  - Evidence: template-vue imports from @core/platform, @core/analytics, @core/errors
  - File: `/Users/anton/tarot/apps/template-vue/frontend/vite.config.ts` line 51
  - Action: Remove core/frontend deletion from ARCHITECTURE.md Phase 00 section

- [ ] **core/exceptions.py has BackendException class**
  - File: `/Users/anton/tarot/core/backend/src/core/exceptions.py`
  - Must include: message, name, code attributes
  - Must include: __init__ constructor signature matching app pattern
  - Verification: `grep -c "class BackendException" /Users/anton/tarot/core/backend/src/core/exceptions.py` = 1

- [ ] **No breaking changes to app imports**
  - Apps still import from `app.exceptions` (not from core yet)
  - Phase 01 will update imports after BackendException is in core

- [ ] **All 4 apps have identical BackendException pattern**
  - tarot: `/Users/anton/tarot/apps/template/backend/src/app/exceptions.py` line 1-8
  - template-react: `/Users/anton/tarot/apps/template-react/backend/src/app/exceptions.py` line 1-8
  - template-vue: `/Users/anton/tarot/apps/template-vue/backend/src/app/exceptions.py` line 1-8
  - maxstat: `/Users/anton/tarot/apps/template-react/backend/src/app/exceptions.py` line 1-8
  - Verification: All have identical __init__ signature

- [ ] **Shared exception list documented for Phase 01**
  - FriendAlreadyExistsException (shared)
  - LLMError (shared)
  - AllLLMProvidersFailedError (shared)
  - UserNotFoundException (will be moved to core)
  - ReadingNotFoundError (app-specific - keep in apps)

---

## ARCHITECTURE.md Update Required

**Current Phase 00 DELETE section is incorrect:**
```
| Path | Reason |
|------|--------|
| `core/frontend/` (entire directory) | Dead Vue package - 0% usage |
```

**Should be updated to:**
```
| Path | Reason | Evidence |
|------|--------|----------|
| NONE - core/frontend is ACTIVE | Not dead code | template-vue imports from @core/platform, @core/analytics (20+ refs) |
```

---

## Phase 00 Summary

| Task | Status | Impact |
|------|--------|--------|
| Verify core/frontend usage | COMPLETE | KEEP - actively used by template-vue |
| Add BackendException to core | PENDING | Enables Phase 01 exception consolidation |
| Update ARCHITECTURE.md | PENDING | Remove incorrect core/frontend deletion |
| Test imports unaffected | PENDING | Validation step before Phase 01 |

**Estimated Effort:** 10 minutes (update 1 file, verify 4 files)
**Lines Changed:** ~20 lines added to core/exceptions.py
**Breaking Changes:** None (backward compatible addition)
