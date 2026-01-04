# Why Composition Pattern?

**Date:** 2025-10-28
**Status:** Implemented
**Decision:** Migrate from inheritance to composition pattern for Core/App relationship

## Context

The tarot backend originally used inheritance pattern to extend Core functionality:

```python
# Old pattern (inheritance)
class RequestsRepo(CoreRequestsRepo):
    pass

class RequestsService(CoreRequestsService):
    pass
```

This created tight coupling between Core and App layers.

## Decision

Migrate to composition pattern with explicit delegation:

```python
# New pattern (composition)
class RequestsRepo:
    def __init__(self, session):
        self._core = CoreRequestsRepo(session)

    @cached_property
    def users(self):
        return self._core.users
```

## Alternatives Considered

### 1. Keep Inheritance Pattern
**Pros:**
- Simple, no boilerplate
- Automatic inheritance of core functionality

**Cons:**
- Tight coupling (changes in Core affect App)
- Hard to test in isolation
- Implicit dependencies
- Version conflicts difficult to manage
- Cannot control what gets inherited

**Decision:** ❌ Rejected - Coupling issues outweigh simplicity

### 2. Full Duplication (No Core Package)
**Pros:**
- Complete independence
- No shared dependencies

**Cons:**
- Code duplication
- Maintenance nightmare
- Bug fixes need multiple updates
- Inconsistent behavior across apps

**Decision:** ❌ Rejected - Violates DRY principle

### 3. Composition with Simple Delegation
**Pros:**
- Loose coupling
- Easy to test
- Explicit API surface
- Independent versioning

**Cons:**
- Slightly more boilerplate
- Need to maintain delegation properties

**Decision:** ✅ **SELECTED** - Best balance of benefits vs. trade-offs

### 4. Composition with Re-instantiation (Services)
**Pros:**
- Core services can call app services
- Full context propagation
- No circular dependencies
- Maintains cross-service communication

**Cons:**
- Core services instantiated twice (once in _core, once in app)
- Slightly higher memory usage

**Decision:** ✅ **SELECTED for Services** - Essential for cross-service communication

## Benefits Realized

### 1. Loose Coupling ✅
- Core changes isolated to delegation layer
- App can upgrade Core independently
- Clear boundary between Core and App

### 2. Testability ✅
- Can mock `self._core` in tests
- Easy to test App logic in isolation
- Integration tests verify composition works

### 3. Independent Versioning ✅
- Core can be versioned separately
- App can pin Core version
- Safer upgrades

### 4. Explicit API Surface ✅
- Each property documented
- Clear what comes from Core vs App
- Better IntelliSense/autocomplete

### 5. Better Documentation ✅
- Delegation properties serve as documentation
- Clear ownership of each repository/service
- Easier onboarding for new developers

## Implementation Details

### Repository Pattern (Simple Delegation)

```python
class RequestsRepo:
    def __init__(self, session):
        self.session = session
        self._core = CoreRequestsRepo(session)

    @cached_property
    def users(self) -> UserRepo:
        """User repository (from core)"""
        return self._core.users
```

**Rationale:** Repositories don't have cross-dependencies, so simple delegation works.

### Service Pattern (Re-instantiation)

```python
class RequestsService:
    def __init__(self, repo, producer, bot, redis, arq):
        self._core = CoreRequestsService(repo._core, ...)

    @cached_property
    def users(self) -> UserService:
        """User service (from core)"""
        return UserService(self.repo._core, self.producer, self, self.bot)
        # Note: 'self' here is RequestsService, not self._core
```

**Rationale:** Core services need to call app services (e.g., `services.messages.queue_admin_broadcast`). Re-instantiation ensures they receive full `RequestsService` context.

## Trade-offs Accepted

### Boilerplate Delegation Properties
- **Trade-off:** 8 delegation properties in RequestsRepo, 5 in RequestsService
- **Accepted:** Small amount of boilerplate is worth the benefits
- **Mitigation:** Properties are simple one-liners with clear docs

### Dual Instantiation of Core Services
- **Trade-off:** Core services instantiated in both `_core` and as properties
- **Accepted:** Necessary for cross-service communication
- **Mitigation:** Services are lightweight (lazy-loaded)

## Lessons Learned

1. **Services Need Full Context:** Initial attempt at simple delegation failed because core services couldn't call app services. Re-instantiation pattern solved this.

2. **Cached Properties Essential:** Using `@cached_property` prevents performance issues from lazy loading.

3. **Tests Validate Architecture:** Integration tests caught the delegation vs. re-instantiation issue early.

4. **Documentation Matters:** Explicit delegation properties serve as excellent documentation.

## Future Considerations

1. **Multiple Apps:** Composition pattern will make it easier to add more Telegram Mini Apps that reuse Core.

2. **Core Evolution:** Core can evolve independently without breaking App (as long as public API is stable).

3. **Plugin System:** Could potentially add plugin system for extending Core without modifying it.

## Validation Results

- ✅ All 167 tests passing (163 existing + 4 new composition tests)
- ✅ Import boundaries validated (3 contracts kept, 0 broken)
- ✅ Services start successfully (webhook, bot, worker)
- ✅ No runtime errors
- ✅ Backward compatible (all existing code works)

## Conclusion

Composition pattern migration was **successful**. The architecture is now more maintainable, testable, and scalable. The trade-offs (boilerplate, dual instantiation) are acceptable given the significant benefits.

**Recommendation:** Use composition pattern for all future Core/App integrations.
