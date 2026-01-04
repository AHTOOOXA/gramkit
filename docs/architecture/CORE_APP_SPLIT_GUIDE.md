# Core/App Split Guide - Universal Rules for Extracting to Core

**Purpose:** Guidelines for determining what should move to core vs stay in app when extracting reusable infrastructure from app-specific code.

**Success Examples:**
- ✅ NotificationTemplate + NotificationsService (Task 1.4.1)
- ✅ Rate Limiter (Task 1.1.1)
- ✅ Script Framework (Task 1.2.1)

**Failure Examples:**
- ❌ Promotional Broadcasts (Task 1.3.x - too app-specific, reverted)

---

## Golden Rules

### Rule #1: The Import Test 🔍
**If it imports from `app.*`, it probably shouldn't go to core**

```python
# ❌ BAD - Core importing from app
from app.services.readings import ReadingsService
from app.tgbot.keyboards import main_kb

# ✅ GOOD - Core importing only from core
from core.services.base import BaseService
from core.schemas.users import UserSchema
```

**Exception:** Type checking imports are acceptable if using composition pattern:
```python
if TYPE_CHECKING:
    from app.services.requests import RequestsService  # OK for typing
```

### Rule #2: The "Second App Test" 🎯
**Ask: "Would a second app with completely different domain logic need this?"**

**YES → Core:**
- Notification scheduling framework
- Rate limiting
- User authentication
- Payment processing
- Database session management

**NO → App:**
- Tarot reading logic
- Specific notification templates (DailyCardNotification)
- Tarot-specific business rules
- App-specific keyboard layouts

### Rule #3: The Abstraction Layer 🏗️
**Core should provide abstractions/frameworks, App provides implementations**

```python
# Core: Abstract base class (framework)
class NotificationTemplate(ABC):
    @abstractmethod
    async def get_message_key(self) -> str:
        pass

# App: Concrete implementation
class DailyCardNotification(NotificationTemplate):
    async def get_message_key(self) -> str:
        return "notifications.daily_card.0"
```

### Rule #4: The Configuration Pattern ⚙️
**Core provides behavior, App provides configuration**

```python
# Core: Generic service with configurable lists
class NotificationsService(BaseService):
    MORNING_NOTIFICATIONS = []  # Override in app
    EVENING_NOTIFICATIONS = []  # Override in app

    async def send_notifications_by_time(self, notification_classes, hour):
        # Generic scheduling logic here
        pass

# App: Configuration via inheritance
class NotificationsService(CoreNotificationsService):
    MORNING_NOTIFICATIONS = [
        DailyCardNotification,
        PremiumNotification,
    ]
    EVENING_NOTIFICATIONS = [
        OutOfReadingsFollowUpNotification,
    ]
```

---

## Decision Matrix

Use this matrix to decide where code belongs:

| Characteristic | Core ✅ | App ⚠️ |
|---------------|---------|--------|
| **Imports** | Only from `core.*` | Can import from `app.*` |
| **Abstraction Level** | Abstract/Generic | Concrete/Specific |
| **Business Logic** | Domain-agnostic | Domain-specific |
| **Reusability** | All apps need this | Only tarot needs this |
| **Dependencies** | Core services only | App-specific services |
| **Configuration** | Configurable via overrides | Hard-coded specifics |
| **Examples** | Framework, Protocol, Base class | Implementation, Template, Handler |

---

## Patterns for Core/App Split

### Pattern 1: Abstract Base + Concrete Implementation

**Use when:** You have a clear protocol/interface with multiple implementations

```python
# ✅ Core: Abstract base
class NotificationTemplate(ABC):
    @abstractmethod
    async def get_message_key(self) -> str:
        pass

    async def filter_eligible_users(self, users):
        return users  # Default implementation

# ✅ App: Concrete implementations
class DailyCardNotification(NotificationTemplate):
    async def get_message_key(self) -> str:
        return self.get_random_key(self._message_keys)

    async def filter_eligible_users(self, users):
        # Tarot-specific filtering
        return [u for u in users if u.wants_daily_cards]
```

**✅ Moves to core:** Abstract base class
**⚠️ Stays in app:** All concrete implementations

---

### Pattern 2: Framework Service + Configuration

**Use when:** Core provides generic orchestration, app provides specifics

```python
# ✅ Core: Framework with extension points
class NotificationsService(BaseService):
    MORNING_NOTIFICATIONS = []  # Extension point
    EVENING_NOTIFICATIONS = []  # Extension point

    async def send_notifications_by_time(self, classes, hour):
        """Generic scheduling logic - works for any app"""
        users = await self.services.users.get_users_by_local_time(hour)
        for cls in classes:
            notification = cls().initialize(self.services)
            await self.send_notification(notification, users)

# ✅ App: Configuration via inheritance
class NotificationsService(CoreNotificationsService):
    MORNING_NOTIFICATIONS = [TarotSpecificNotification1, ...]
    EVENING_NOTIFICATIONS = [TarotSpecificNotification2, ...]

    def get_morning_notifications_with_promotions(self):
        """App-specific: Add promotional broadcasts"""
        return [PromotionalBroadcast] + self.MORNING_NOTIFICATIONS
```

**✅ Moves to core:** Generic service framework
**⚠️ Stays in app:**
- Notification class lists
- App-specific override methods
- Promotional broadcast integration

---

### Pattern 3: Composition (Aggregator Pattern)

**Use when:** Core and app have separate concerns that compose together

```python
# ✅ Core: Base aggregator
class CoreRequestsRepo:
    @cached_property
    def users(self):
        return UserRepo(self.session)

    @cached_property
    def payments(self):
        return PaymentRepo(self.session)

# ✅ App: Composes core + adds app-specific
class RequestsRepo:
    def __init__(self, session):
        self._core = CoreRequestsRepo(session)

    @cached_property
    def users(self):
        return self._core.users  # Delegate to core

    @cached_property
    def readings(self):
        return ReadingsRepo(self.session)  # App-specific
```

**✅ Moves to core:** Universal repos (users, payments, subscriptions)
**⚠️ Stays in app:** App-specific repos (readings, tarot spreads)

---

## Step-by-Step Extraction Process

### Phase 1: Analysis ✍️

1. **Read the code to extract**
   - Identify all imports
   - Identify all dependencies
   - Map out class hierarchy

2. **Apply the Import Test**
   ```bash
   grep "from app\." target_file.py
   ```
   - If NO app imports → Strong candidate for core
   - If YES app imports → Analyze each one

3. **Apply the Second App Test**
   - Would a dating app need this? → Core
   - Would a recipe app need this? → Core
   - Only tarot needs this? → App

4. **Identify the split point**
   - Abstract/Framework → Core
   - Concrete/Configuration → App

### Phase 2: Create Core Structure 🏗️

1. **Create core directory**
   ```bash
   mkdir -p core/backend/src/core/path/to/feature
   ```

2. **Create `__init__.py` with exports**
   ```python
   from core.path.to.feature.base import BaseClass
   from core.path.to.feature.service import ServiceClass

   __all__ = ["BaseClass", "ServiceClass"]
   ```

3. **Move abstract base classes first**
   - Start with types/protocols
   - Then move services
   - Test after each move

### Phase 3: Move Code 🚚

1. **Copy files to core**
   ```bash
   cp app/feature/base.py core/feature/base.py
   ```

2. **Update imports in core files**
   - Change `from app.*` → `from core.*`
   - Remove app-specific logic
   - Add TODOs for future improvements

3. **Remove app-specific code from core**
   - Strip out concrete implementations
   - Replace with abstract methods
   - Make configuration points explicit

### Phase 4: Update App 🔧

1. **Update app to extend core**
   ```python
   from core.feature.service import CoreFeatureService

   class FeatureService(CoreFeatureService):
       # App-specific overrides and configuration
       pass
   ```

2. **Update imports across app**
   ```bash
   # Find all imports
   grep -r "from app.feature import" apps/template/backend/src/app/

   # Update to import from core where applicable
   # Keep app-specific imports from app
   ```

3. **Delete moved files from app**
   ```bash
   rm apps/template/backend/src/app/feature/base.py
   ```

### Phase 5: Verify ✅

1. **Run import boundary checks**
   ```bash
   make lint  # Should pass import-linter
   ```

2. **Verify no app imports in core**
   ```bash
   grep -r "from app\." core/backend/src/core/path/to/feature/
   # Should return nothing
   ```

3. **Run all tests**
   ```bash
   make test  # All tests should pass
   ```

4. **Check test coverage**
   - Verify moved code is tested
   - Notification service: 12 tests covering framework ✅

---

## Common Mistakes to Avoid ⚠️

### Mistake 1: Moving Too Much
**Problem:** Moving app-specific implementations to core

```python
# ❌ BAD - Promotional broadcasts in core
class PromotionalBroadcastNotification(NotificationTemplate):
    """This is tarot-specific business logic"""
    def __init__(self, time_slot):
        self._time_slot = time_slot  # Tarot business rule
```

**Solution:** Keep concrete implementations in app
```python
# ✅ GOOD - Framework in core
class NotificationTemplate(ABC):
    """Generic notification protocol"""
    @abstractmethod
    async def get_message_key(self) -> str:
        pass

# ✅ GOOD - Implementation in app
class PromotionalBroadcastNotification(NotificationTemplate):
    # Tarot-specific implementation stays in app
    pass
```

### Mistake 2: Leaving App Dependencies in Core
**Problem:** Core imports from app

```python
# ❌ BAD - Core depends on app
from app.tgbot.keyboards import main_kb

class NotificationsService(BaseService):
    def get_keyboard(self):
        return main_kb()  # App-specific keyboard
```

**Solution:** Make it configurable
```python
# ✅ GOOD - Core accepts keyboard via parameter
class NotificationsService(BaseService):
    async def send_notification(self, notification, users):
        keyboard_func = notification.get_keyboard_func()  # Protocol
        keyboard = keyboard_func() if keyboard_func else None
```

### Mistake 3: No Extension Points
**Problem:** Core service is rigid and unconfigurable

```python
# ❌ BAD - Hard-coded app logic in core
class NotificationsService(BaseService):
    async def send_morning_notification(self):
        # Hard-coded list - can't be changed by app
        notifications = [DailyCardNotification, PremiumNotification]
        return await self.send_notifications_by_time(notifications, 10)
```

**Solution:** Provide configuration points
```python
# ✅ GOOD - Configurable via inheritance
class NotificationsService(BaseService):
    MORNING_NOTIFICATIONS = []  # Override in app
    MORNING_HOUR = 10  # Override in app

    def get_morning_notifications_with_promotions(self):
        """Override in app for custom behavior"""
        return self.MORNING_NOTIFICATIONS.copy()

    async def send_morning_notification(self):
        notifications = self.get_morning_notifications_with_promotions()
        return await self.send_notifications_by_time(notifications, self.MORNING_HOUR)
```

### Mistake 4: Splitting Too Fine
**Problem:** Over-engineering the abstraction

```python
# ❌ BAD - Too many tiny abstractions
class NotificationScheduler(ABC): pass
class NotificationFilter(ABC): pass
class NotificationSender(ABC): pass
class NotificationPrioritizer(ABC): pass
# ... 10 more abstract classes
```

**Solution:** Start pragmatic, refactor when needed
```python
# ✅ GOOD - Start with working solution + TODOs
class NotificationsService(BaseService):
    """
    TODO: When building second app, consider:
    - Extracting scheduler into separate class
    - Making broadcast behavior pluggable
    - Supporting custom time slots
    """
    # Working implementation that can be refactored later
```

---

## Validation Checklist

Before committing a core extraction, verify:

### Code Quality ✅
- [ ] No `from app.*` imports in core files (check with grep)
- [ ] Core files only import from `core.*`
- [ ] All abstract methods have docstrings explaining contract
- [ ] TODOs added for future improvements

### Architecture ✅
- [ ] Abstract base class / protocol in core
- [ ] Concrete implementations remain in app
- [ ] App extends/composes core (not duplicates)
- [ ] Configuration points clearly documented

### Testing ✅
- [ ] All existing tests still pass
- [ ] Core functionality is covered by tests
- [ ] Both unit and integration tests pass
- [ ] No test imports from `app.*` into core tests

### Import Boundaries ✅
- [ ] `make lint` passes (import-linter checks)
- [ ] Core layer doesn't depend on app layer
- [ ] Circular dependencies avoided
- [ ] Dependency graph flows core ← app (not app → core)

### Documentation ✅
- [ ] Docstrings explain what goes to core vs app
- [ ] Extension points documented
- [ ] Examples of app-specific overrides provided
- [ ] TODOs for future multi-app improvements

---

## Case Study: Notification Framework Migration

**Task:** Move notification system to core for reuse across multiple apps

### What Moved to Core ✅

**1. Abstract Base Class (`types.py`)**
```python
# Why: Protocol/contract that all apps need
class NotificationTemplate(ABC):
    @abstractmethod
    async def get_message_key(self) -> str:
        pass

    # Generic helpers any app can use
    def get_random_key(self, keys: list[str]) -> str:
        import random
        return random.choice(keys)
```

**Decision factors:**
- No app imports ✅
- Pure protocol/framework ✅
- All apps need notification system ✅

**2. Framework Service (`service.py`)**
```python
# Why: Generic scheduling/delivery infrastructure
class NotificationsService(BaseService):
    MORNING_NOTIFICATIONS = []  # Override in app
    EVENING_NOTIFICATIONS = []  # Override in app

    async def send_notifications_by_time(self, classes, hour):
        """Generic algorithm works for any app"""
        users = await self.services.users.get_users_by_local_time(hour)
        # Priority-based scheduling logic...
        for notification in sorted_notifications:
            await self.send_notification(notification, users)
```

**Decision factors:**
- Generic scheduling algorithm ✅
- Works with any NotificationTemplate subclass ✅
- Only uses core services (users, messages) ✅
- Configurable via inheritance ✅

### What Stayed in App ⚠️

**1. Concrete Notification Templates (`templates.py`)**
```python
# Why: Tarot-specific business logic
class DailyCardNotification(NotificationTemplate):
    def __init__(self):
        self._message_keys = [
            "notifications.daily_card.0",  # Tarot-specific messages
            "notifications.daily_card.1",
        ]

    def get_keyboard_func(self):
        return daily_card_notification_kb  # Tarot-specific keyboard

class PremiumNotification(NotificationTemplate):
    async def filter_eligible_users(self, users):
        # Tarot business rule: only premium subscribers
        return [u for u in users if await self.services.subscriptions.has_active(u.id)]
```

**Decision factors:**
- Imports app-specific keyboards ❌
- Contains tarot business rules ❌
- Uses tarot-specific i18n message keys ❌
- Only tarot needs these specific notifications ❌

**2. App Configuration (`service.py`)**
```python
# Why: Tarot-specific notification schedule
class NotificationsService(CoreNotificationsService):
    MORNING_HOUR = 10  # Tarot's schedule
    EVENING_HOUR = 19  # Tarot's schedule

    MORNING_NOTIFICATIONS = [
        DailyCardNotification,  # Tarot-specific
        SelfDiscoveryJourneyNotification,  # Tarot-specific
    ]

    def get_morning_notifications_with_promotions(self):
        """Tarot-specific: add promotional broadcasts"""
        return [PromotionalBroadcast] + self.MORNING_NOTIFICATIONS
```

**Decision factors:**
- Lists of tarot-specific notification classes ❌
- Promotional broadcast integration (tarot feature) ❌
- Tarot's specific schedule (another app might use different hours) ❌

### Results 📊

**Before:**
- All notification code in app
- Not reusable for second app
- 326 lines in `app/services/notifications/service.py`

**After:**
- Framework in core: 318 lines
- App configuration: 67 lines
- Reusable across all apps ✅
- All 167 tests passing ✅
- 12 notification-specific tests passing ✅

**Reusability proven:**
- Second app can create own notification templates
- Second app can use different schedule
- Second app reuses entire scheduling infrastructure
- Second app can override/extend behavior as needed

---

## Quick Reference

### "Should this go to core?" Decision Tree

```
Does it import from app.*?
├─ YES → Stay in app (probably)
└─ NO
   └─ Would a completely different app need this exact logic?
      ├─ NO → Stay in app
      └─ YES
         └─ Is it abstract/framework or concrete/implementation?
            ├─ Concrete → Stay in app
            └─ Abstract → Move to core ✅
```

### TODOs for Future Refactoring

When moving code to core, add TODOs for multi-app improvements:

```python
class NotificationsService(BaseService):
    """
    Core notification service.

    TODO: When building second app, consider:
    - Extracting scheduler into separate class
    - Making broadcast behavior pluggable
    - Supporting custom time slots beyond morning/evening
    - Dependency injection for notification discovery
    """
```

**Why TODOs matter:**
- You have ONE app now, don't over-engineer
- Move to core when you have real reuse case
- Add TODOs to guide future refactoring
- Pragmatic > Perfect

---

## Summary

**Core should contain:**
- ✅ Abstract base classes / protocols
- ✅ Generic framework services
- ✅ Infrastructure / utilities
- ✅ Domain-agnostic logic
- ✅ Code with NO app imports

**App should contain:**
- ⚠️ Concrete implementations
- ⚠️ Business rules
- ⚠️ Configuration / data
- ⚠️ App-specific integrations
- ⚠️ Code that imports from app.*

**Remember:**
1. Use the Import Test first (no `from app.*` in core)
2. Use the Second App Test (would dating app need this?)
3. Start pragmatic, refactor when you have second app
4. Add TODOs for future multi-app improvements
5. Verify with tests and import-linter

**When in doubt:** Keep it in app. It's easier to move to core later than to fix a premature abstraction.
