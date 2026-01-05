# Phase 04: Admin Bot Handlers

**Focus:** Extract admin handlers (~2,894 lines) with KeyboardFactory protocol injection

---

## Codebase Analysis

### Current Implementation

**Tarot Admin Module** (`apps/template/backend/src/app/tgbot/handlers/admin.py` - lines 1-945)
- **Router exports:** `router = Router()` (line 19)
- **Imports location:**
  - App-specific: `from app.infrastructure import file_manager` (line 10)
  - App-specific: `from app.tgbot.keyboards.keyboards import command_keyboard, keygo_keyboard` (lines 12)
  - Core services: `from core.infrastructure.config import settings` (line 13)
  - Auth/schemas: `from core.schemas.users import UpdateUserRequest, UserSchema` (line 17)
  - Services: `from app.services.requests import RequestsService` (line 11)

**FSM States Defined** (lines 62-76)
- `class BroadcastStates(StatesGroup)` (lines 63-66)
  - `waiting_for_message`
  - `waiting_for_keyboard`
  - `confirmation`
- `class PromoStates(StatesGroup)` (lines 70-76)
  - `waiting_for_message`
  - `waiting_for_time_slot`
  - `waiting_for_repeat_count`
  - `waiting_for_keyboard`
  - `waiting_for_button_text`
  - `confirmation`

**Handlers Implemented:**
- `/admin` command (lines 79-104) - Shows available admin commands
- `/broadcast` command (lines 107-116) - Starts broadcast flow
- Broadcast FSM flow (lines 119-340) - Message processing, keyboard selection, confirmation
- `/keygo_prediction` command (lines 343-360) - Sends keygo image + keyboard
- `/stats` command (lines 363-392) - Manual statistics generation
- `/promo` command (lines 398-412) - Promotional broadcast scheduler
- Promo FSM flow (lines 415-767) - Multi-step scheduling workflow
- `/promo_list` command (lines 769-813) - List active broadcasts
- `/promo_cancel` command (lines 816-848) - Cancel broadcast by ID
- `/giftsub` command (lines 851-944) - Gift subscription to user

**App-Specific Dependencies:**
- `file_manager.get_full_path("images/keygo/tarotmeowXkeygo.png")` (line 355) - Keygo image path
- `command_keyboard()` function (line 250, 270) - Returns InlineKeyboardMarkup
- `keygo_keyboard()` function (line 352) - Returns InlineKeyboardMarkup
- Both defined in: `apps/template/backend/src/app/tgbot/keyboards/keyboards.py` (lines 9-38)

**Core Admin Handler Pattern** (`core/backend/src/core/infrastructure/telegram/handlers/admin.py` - lines 1-40)
- Uses `CoreRequestsService` dependency injection (line 18)
- Permission checks: `user.telegram_id not in settings.rbac.owner_ids` (line 21)
- Error handling with logger (lines 39-40)

### Media Message Helper

**Reusable Logic** (lines 23-59)
- `_process_media_message()` helper - Converts Telegram entities to HTML formatting
- Handles: photo, video, animation, document with captions
- Used in promo flow (lines 459-465)

**Entity Types Supported:**
- bold, italic, code, pre, underline, strikethrough
- text_link, spoiler, mention, hashtag, url

### Database Models Used

From `apps/template/backend/src/app/infrastructure/database/models/promotional_broadcasts.py`:
- `promotional_broadcasts` repository
- Methods: `.create()`, `.get_all_active()`, `.deactivate_broadcast()`
- Fields: `time_slot` (NotificationTimeSlot enum: MORNING/EVENING), `message_type`, `deadline`, `keyboard_type`

### Service Dependencies

From `apps/template/backend/src/app/services/requests.py`:
- `RequestsService.worker.enqueue_job()` - Queue broadcast/stats jobs
- `RequestsService.statistics` - Get daily stats
- `RequestsService.messages.admin_broadcast()` - Send to admin group
- `RequestsService.repo.promotional_broadcasts` - CRUD operations
- `RequestsService.subscriptions` - Subscription management
- `RequestsService.users.get_by_telegram_id()`

### Duplicate Detection

**Across 4 apps:** tarot, template-react, template-vue, maxstat
- Each has `apps/*/backend/src/app/tgbot/handlers/admin.py`
- Broadcast/promo FSM states identical
- Media processing helper duplicated
- Giftsub command duplicated
- Only keyboard factory differs per app

---

## Implementation Steps

### Step 1: Create FSM States Module
**File:** `core/backend/src/core/infrastructure/telegram/handlers/admin/states.py`
- Extract `BroadcastStates` class (lines 63-66 from tarot admin.py)
- Extract `PromoStates` class (lines 70-76 from tarot admin.py)
- No dependencies - pure FSM definitions

### Step 2: Create Protocol Definition
**File:** `core/backend/src/core/infrastructure/telegram/handlers/admin/protocol.py`
- Define `KeyboardFactory` protocol with 4 methods:
  - `command_keyboard(self) -> InlineKeyboardMarkup` - Main menu button
  - `daily_keyboard(self) -> InlineKeyboardMarkup` - Daily card button
  - `keygo_keyboard(self) -> InlineKeyboardMarkup | None` - Optional keygo button
  - `keygo_image_path(self) -> str | None` - Optional keygo image path
- Protocol pattern (from CLAUDE.md): NO factory functions, use dependency injection

### Step 3: Create Base Handlers Module
**File:** `core/backend/src/core/infrastructure/telegram/handlers/admin/base.py`
- Extract `/admin` command handler (lines 79-104)
- Extract `/stats` command handler (lines 363-392)
- Extract `/giftsub` command handler (lines 851-944)
- Inject `KeyboardFactory` as protocol parameter? NO - use direct imports
- Dependency: `services: CoreRequestsService`
- Note: These 3 commands don't use keyboards, can stay pure

### Step 4: Create Broadcast Module
**File:** `core/backend/src/core/infrastructure/telegram/handlers/admin/broadcast.py`
- Extract `_process_media_message()` helper (lines 23-59)
- Extract broadcast FSM handlers (lines 107-340)
  - `/broadcast` command
  - `BroadcastStates.waiting_for_message` handler
  - `BroadcastStates.waiting_for_keyboard` callback
  - Confirmation handlers
- **Challenge:** Lines 250, 270 call `command_keyboard()` - requires factory
- **Solution:** Pass `KeyboardFactory` as dependency via FSM context or handler parameter
- Dependency: `services: CoreRequestsService`, `keyboard_factory: KeyboardFactory`

### Step 5: Create Promo Module
**File:** `core/backend/src/core/infrastructure/telegram/handlers/admin/promo.py`
- Extract `/promo` command (lines 398-412)
- Extract promo FSM handlers (lines 415-767)
- Extract `/promo_list` command (lines 769-813)
- Extract `/promo_cancel` command (lines 816-848)
- Helper: `_show_promo_preview_and_confirmation()` (lines 583-667)
- **Challenge:** Lines 254, 274, 603 call `command_keyboard()`, `daily_keyboard()` - requires factory
- **Solution:** Same as broadcast - pass factory as dependency
- Dependency: `services: CoreRequestsService`, `keyboard_factory: KeyboardFactory`

### Step 6: Create Module Exports
**File:** `core/backend/src/core/infrastructure/telegram/handlers/admin/__init__.py`
- Export: `from .states import BroadcastStates, PromoStates`
- Export: `from .protocol import KeyboardFactory`
- Export: `from .base import router as base_router`
- Export: `from .broadcast import router as broadcast_router`
- Export: `from .promo import router as promo_router`

### Step 7: Create App Wrappers (All 4 Apps)
**Files:** `apps/*/backend/src/app/tgbot/handlers/admin.py` (NEW ~30 lines each)
```python
from typing import Protocol

from aiogram.types import InlineKeyboardMarkup

from app.tgbot.keyboards.keyboards import (
    command_keyboard,
    daily_keyboard,
    keygo_keyboard,
)
from app.infrastructure import file_manager
from core.infrastructure.telegram.handlers.admin import (
    BroadcastStates,
    PromoStates,
)


class TarotKeyboardFactory(Protocol):
    """Tarot-specific keyboard implementation."""

    def command_keyboard(self) -> InlineKeyboardMarkup:
        return command_keyboard()

    def daily_keyboard(self) -> InlineKeyboardMarkup:
        return daily_keyboard()

    def keygo_keyboard(self) -> InlineKeyboardMarkup | None:
        return keygo_keyboard()

    def keygo_image_path(self) -> str | None:
        return file_manager.get_full_path("images/keygo/tarotmeowXkeygo.png")
```

### Step 8: Register Handlers in App Router
**Files:** `apps/*/backend/src/app/tgbot/app.py`
- Import: `from core.infrastructure.telegram.handlers.admin import (base_router, broadcast_router, promo_router)`
- Include routers: `bot.include_router(base_router)`, etc.
- Pass factory via dependency override: `bot.dependency_overrides[KeyboardFactory] = TarotKeyboardFactory()`

---

## Success Criteria

### Code Quality
- [ ] All 4 app `admin.py` files reduced to ~30 lines (from 945 lines)
- [ ] Zero imports from `app.tgbot` in core handlers
- [ ] Zero imports of app-specific services in core
- [ ] KeyboardFactory protocol properly injected via dependency system

### Functionality
- [ ] `/admin` command works in all 4 apps
- [ ] `/broadcast` FSM works with app-specific keyboards
- [ ] `/promo` scheduling works with keyboard selection
- [ ] `/giftsub` subscription gifting works
- [ ] `/stats` manual statistics generation works
- [ ] `/keygo_prediction` sends correct image + keyboard per app

### Testing
- [ ] All handlers callable without app-specific imports
- [ ] Media entity processing (HTML formatting) works correctly
- [ ] FSM state transitions work in all apps
- [ ] Permission checks block non-admin users
- [ ] Database operations (broadcasts, subscriptions) succeed

### Integration
- [ ] 4 apps can use core handlers with different KeyboardFactory implementations
- [ ] No circular imports (core doesn't import app modules)
- [ ] Hot reload works (no container restarts needed)

### Validation Checklist
- [ ] `make test APP=tarot` passes
- [ ] `make test APP=template-react` passes
- [ ] `make test APP=template-vue` passes
- [ ] `make test APP=maxstat` passes
- [ ] `make lint APP=tarot` passes
- [ ] No mypy errors in core/handlers/admin/
- [ ] No circular import warnings
