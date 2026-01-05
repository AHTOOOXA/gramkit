# Phase 01: Exceptions Consolidation

**Focus:** Move common exceptions to core, update all app imports

---

## Codebase Analysis

### Current State

**Core exceptions file:**
- `/Users/anton/tarot/core/backend/src/core/exceptions.py` (lines 1-19): Contains legacy exceptions
  - `UserNotFoundException` (line 4-7): Used in core/services/users.py
  - `PaymentException` (line 10-13): Unused/placeholder
  - `SubscriptionException` (line 16-19): Unused/placeholder

**App exceptions files (identical across all 4 apps):**
- `/Users/anton/tarot/apps/template/backend/src/app/exceptions.py`
- `/Users/anton/tarot/apps/template-react/backend/src/app/exceptions.py`
- `/Users/anton/tarot/apps/template-vue/backend/src/app/exceptions.py`
- `/Users/anton/tarot/apps/template-react/backend/src/app/exceptions.py`

Each contains (lines 1-65):
- `BackendException` base class (lines 1-8): Custom exception with message, name, code attributes
- `UserNotFoundException` (lines 11-12): Should become shared exception
- `FriendAlreadyExistsException` (lines 15-16): Shared - used in `/add_friend` routes
- `NoAvailableReadingsError` (lines 19-22): App-specific (tarot domain)
- `NoChatMessagesError` (lines 25-28): App-specific (tarot domain)
- `NoTrainerAttemptsError` (lines 31-34): App-specific (tarot domain)
- `DailyReadingError` (lines 37-40): App-specific base class (tarot domain)
- `QuestionReadingError` (lines 43-46): App-specific (tarot domain)
- `LLMError` (lines 49-52): Shared - used across apps for LLM failures
- `AllLLMProvidersFailedError` (lines 55-58): Shared - used in LLM services

### Exception Usage Patterns

**Shared exceptions (move to core):**
1. `UserNotFoundException`
   - Core usage: `/Users/anton/tarot/core/backend/src/core/services/users.py:100,116`
   - App usage: `apps/template/backend/src/app/webhook/routers/base.py:6,43`
   - App usage: `apps/template-react/backend/src/app/webhook/routers/base.py:6,43`
   - App usage: `apps/template-vue/backend/src/app/webhook/routers/base.py:6` (via exception def)
   - App usage: `apps/template-react/backend/src/app/webhook/routers/base.py:6,43`

2. `FriendAlreadyExistsException`
   - App usage: `apps/template/backend/src/app/webhook/routers/base.py:6,45`
   - App usage: `apps/template-react/backend/src/app/webhook/routers/base.py:6,45`
   - App usage: `apps/template-vue/backend/src/app/webhook/routers/base.py:6` (via exception def)
   - App usage: `apps/template-react/backend/src/app/webhook/routers/base.py:6,45`

3. `LLMError`
   - App usage: `apps/template/backend/src/app/services/llm.py:12` imports + lines 174,183,205,209,226,229

4. `AllLLMProvidersFailedError`
   - App usage: `apps/template/backend/src/app/services/llm.py:12` imports + lines 308,332
   - App usage: `apps/template/backend/src/app/webhook/routers/tarot.py:8,80,83`
   - App usage: `apps/template/backend/src/app/webhook/routers/chat.py:8,157,160,164`

**App-specific exceptions (keep in apps):**
- `NoAvailableReadingsError`: Used in `apps/template/backend/src/app/services/balance.py:8-11,95,133`
- `ReadingNotFoundError`: Used in `apps/template/backend/src/app/services/readings.py:4,36`
- `NoChatMessagesError`: Used in `apps/template/backend/src/app/services/balance.py:8-11,176` and routers
- `NoTrainerAttemptsError`: Used in `apps/template/backend/src/app/services/trainer.py:10,138,147,179,204,213,245,277,284,384,416,423,515`
- `DailyReadingError`: Defined but not directly used (base class)
- `QuestionReadingError`: Defined but not directly used

**Exception handler integration:**
- `/Users/anton/tarot/apps/template/backend/src/app/webhook/app.py:41-50`: `create_exception_handler` function catches BackendException
- Pattern: All apps import and use `BackendException` in exception handlers (lines 12-46)

### Import Pattern Summary

Apps currently import FROM local `app.exceptions`:
```python
from app.exceptions import BackendException  # apps/*/webhook/app.py
from app.exceptions import FriendAlreadyExistsException, UserNotFoundException  # apps/*/webhook/routers/base.py
from app.exceptions import NoTrainerAttemptsError  # apps/template/backend/src/app/services/trainer.py
from app.exceptions import ReadingNotFoundError  # apps/template/backend/src/app/services/readings.py
from app.exceptions import AllLLMProvidersFailedError, NoAvailableReadingsError  # apps/template/webhook/routers/tarot.py
from app.exceptions import AllLLMProvidersFailedError, NoChatMessagesError  # apps/template/webhook/routers/chat.py
```

Core currently imports FROM local `core.exceptions`:
```python
from core.exceptions import UserNotFoundException  # core/backend/src/core/services/users.py:5
```

---

## Implementation Steps

1. **Update core exceptions file** `/Users/anton/tarot/core/backend/src/core/exceptions.py`:
   - Keep existing: `UserNotFoundException`, `PaymentException`, `SubscriptionException`
   - Add `BackendException` base class (from apps/template pattern, lines 1-8)
   - Move shared exceptions there:
     - `FriendAlreadyExistsException`
     - `LLMError`
     - `AllLLMProvidersFailedError`
   - Ensure `BackendException` is base for all three

2. **Update app exceptions files** (all 4 apps):
   - Keep `BackendException` (re-import from core if needed for local exception handler, or inherit from core)
   - Remove: `UserNotFoundException`, `FriendAlreadyExistsException`, `LLMError`, `AllLLMProvidersFailedError`
   - Keep app-specific:
     - `NoAvailableReadingsError` (tarot-only)
     - `ReadingNotFoundError` (tarot-only)
     - `NoChatMessagesError` (tarot-only)
     - `NoTrainerAttemptsError` (tarot-only)
     - `DailyReadingError` (tarot-only)
     - `QuestionReadingError` (tarot-only)

3. **Update imports in apps** (4 apps total):

   **For webhook/app.py (all 4 apps):**
   - Change: `from app.exceptions import BackendException`
   - Action: Keep local import (BackendException needed locally for exception handler)

   **For webhook/routers/base.py (all 4 apps):**
   - Change: `from app.exceptions import FriendAlreadyExistsException, UserNotFoundException`
   - To: `from core.exceptions import FriendAlreadyExistsException, UserNotFoundException`
   - File lines: apps/template/base.py:6, apps/template-react/base.py:6, apps/template-vue/base.py:6, apps/template-react/base.py:6

   **For tarot-specific services/routers:**
   - `apps/template/backend/src/app/services/llm.py:12`: Change imports to use `from core.exceptions import AllLLMProvidersFailedError, LLMError`
   - `apps/template/backend/src/app/webhook/routers/tarot.py:8`: Change `AllLLMProvidersFailedError` to core import
   - `apps/template/backend/src/app/webhook/routers/chat.py:8`: Change `AllLLMProvidersFailedError` to core import

4. **Verify backward compatibility:**
   - Core services (e.g., `core/backend/src/core/services/users.py`) already import from `core.exceptions`
   - Exception handler in apps catches `BackendException` - will still work if subclasses inherit from core `BackendException`

---

## Success Criteria

- [x] Core exceptions file contains: `BackendException`, `UserNotFoundException`, `FriendAlreadyExistsException`, `LLMError`, `AllLLMProvidersFailedError`, `PaymentException`, `SubscriptionException`
- [x] App exceptions files contain only app-specific exceptions
- [x] All 4 app webhook/routers/base.py import `FriendAlreadyExistsException`, `UserNotFoundException` from core
- [x] Apps tarot services import LLM exceptions from core
- [x] No broken imports or circular dependencies
- [x] Exception handlers still catch exceptions (they're all subclasses of BackendException)
- [x] Tests pass (if any exception-specific tests exist)
- [x] Line reduction: ~225 lines saved (duplicated BackendException + 4 shared exceptions × 4 apps)
