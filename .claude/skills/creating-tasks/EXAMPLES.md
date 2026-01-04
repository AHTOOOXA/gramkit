# Task Creation Examples

Complete examples of different task types created with this skill.

## Example 1: Feature Implementation Task

**User request:** "Create task for adding user profile customization"

**Created structure:**
```
docs/tasks/user-profile-customization/
├── README.md
├── 00-overview.md
├── 01-planning.md
├── 02-backend-models.md
├── 03-backend-api.md
├── 04-frontend-store.md
├── 05-frontend-ui.md
├── 06-testing.md
└── 07-documentation.md
```

**README.md excerpt:**
```markdown
# User Profile Customization

Add user profile customization features including avatar, display name, bio, and preferences.

---

## Quick Start

**Total Time:** 8-10 hours (can split over 2 days)

**Strategy:**
1. Plan data model and API contracts
2. Implement backend (models, repos, services, endpoints)
3. Generate API schema for frontend
4. Implement frontend (store, UI components)
5. Test end-to-end functionality
6. Update documentation

**Goal:** Users can customize their profiles with avatar, display name, bio, and preferences stored in database and displayed in UI.

---

## Phase Overview

| Phase | Description | Time | Status |
|-------|-------------|------|--------|
| [00 - Overview](./00-overview.md) | Feature requirements and architecture | 30m | ⏸️ Not started |
| [01 - Planning](./01-planning.md) | Data model design, API contracts | 1h | ⏸️ Not started |
| [02 - Backend Models](./02-backend-models.md) | UserProfile model and migration | 1h | ⏸️ Not started |
| [03 - Backend API](./03-backend-api.md) | Repository, service, endpoints | 2h | ⏸️ Not started |
| [04 - Frontend Store](./04-frontend-store.md) | Pinia store for profile management | 1h | ⏸️ Not started |
| [05 - Frontend UI](./05-frontend-ui.md) | Profile edit screen and components | 2.5h | ⏸️ Not started |
| [06 - Testing](./06-testing.md) | Contract tests, integration tests | 1.5h | ⏸️ Not started |
| [07 - Documentation](./07-documentation.md) | Update guides and API docs | 30m | ⏸️ Not started |
```

---

## Example 2: Migration Task

**User request:** "Create task for migrating to new Redis session format"

**Created structure:**
```
docs/tasks/redis-session-migration/
├── README.md
├── 00-overview.md
├── 01-preparation.md
├── 02-new-format-design.md
├── 03-backward-compatible-reader.md
├── 04-dual-write-implementation.md
├── 05-testing-validation.md
├── 06-switch-to-new-format.md
├── 07-cleanup-old-format.md
├── 08-deployment.md
├── MIGRATION_LOG.md
└── session-inventory.txt
```

**README.md excerpt:**
```markdown
# Redis Session Format Migration

Migrate from current Redis session format to new structured format with versioning support.

---

## Quick Start

**Total Time:** 12-14 hours (split over 3 days recommended)

**Strategy:**
1. Design new session format with versioning
2. Implement backward-compatible reader (reads both formats)
3. Implement dual-write (writes both formats)
4. Test thoroughly with production-like data
5. Switch to single-write new format
6. Clean up old format support
7. Deploy with zero downtime

**Goal:** All sessions use new structured format with zero user disruption.

---

## Migration Scope

### ✅ What Changes

**Session format:**
- Old: Flat string keys in Redis
- New: Structured JSON with version field

**Code:**
- SessionManager reads/writes both formats (Phase 3-5)
- SessionManager reads/writes only new format (Phase 6+)

### ✅ What Improves

- Versioning support for future migrations
- Structured data (easier to extend)
- Type safety in session data
- Better debugging (readable in Redis CLI)

### ❌ What Stays the Same

- Redis as session store
- Session TTL and expiration
- Session validation logic
- User-facing session behavior

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Session data loss | Low | Critical | Dual-write phase, extensive testing |
| Breaking active sessions | Medium | High | Backward-compatible reader first |
| Performance degradation | Low | Medium | Benchmark dual-write overhead |
| Rollback complexity | Medium | High | Keep old format reader 30 days |

**Overall Risk:** ⚠️ **MEDIUM** (careful phased rollout required)
```

---

## Example 3: Architecture Review Task

**User request:** "Create task for reviewing payment service architecture"

**Created structure:**
```
docs/tasks/payment-service-review/
├── README.md
├── 00-scope-definition.md
├── 01-current-implementation.md
├── 02-provider-integration-analysis.md
├── 03-error-handling-review.md
├── 04-testing-coverage.md
├── 05-security-assessment.md
├── 06-scalability-analysis.md
└── 07-recommendations.md
```

**README.md excerpt:**
```markdown
# Payment Service Architecture Review

Comprehensive review of payment service architecture, provider integrations, error handling, and scalability.

---

## Quick Start

**Total Time:** 10-12 hours (1-2 weeks)

**Strategy:**
1. Define review scope and success criteria
2. Document current implementation
3. Analyze each payment provider integration
4. Review error handling and edge cases
5. Assess test coverage
6. Conduct security assessment
7. Analyze scalability and performance
8. Compile recommendations

**Goal:** Identify architecture issues, security concerns, and improvement opportunities in payment processing.

---

## Phase Overview

| Phase | Description | Time | Priority |
|-------|-------------|------|----------|
| [00 - Scope](./00-scope-definition.md) | Define what to review | 1h | 🔴 Critical |
| [01 - Current State](./01-current-implementation.md) | Document as-is architecture | 2h | 🔴 Critical |
| [02 - Providers](./02-provider-integration-analysis.md) | Review each integration | 2h | 🔴 Critical |
| [03 - Errors](./03-error-handling-review.md) | Error handling patterns | 1.5h | 🟡 Important |
| [04 - Tests](./04-testing-coverage.md) | Test coverage analysis | 1.5h | 🟡 Important |
| [05 - Security](./05-security-assessment.md) | Security vulnerabilities | 2h | 🔴 Critical |
| [06 - Scale](./06-scalability-analysis.md) | Performance and scale | 1h | 🔵 Nice to have |
| [07 - Recommendations](./07-recommendations.md) | Action items | 1h | 🔴 Critical |

---

## Key Questions to Answer

1. **Is the architecture sound?**
   - Are payment flows secure?
   - Is error handling comprehensive?
   - Are transactions properly isolated?

2. **Are integrations robust?**
   - Do all providers follow best practices?
   - Are webhooks handled correctly?
   - Is retry logic appropriate?

3. **What are the risks?**
   - Security vulnerabilities?
   - Data consistency issues?
   - Race conditions?

4. **Can it scale?**
   - Performance bottlenecks?
   - Database query optimization?
   - Caching opportunities?

5. **What needs improvement?**
   - Critical issues (fix before production)
   - Important improvements (backlog)
   - Nice-to-haves (future)
```

---

## Example 4: Bug Fix Task

**User request:** "Create task for fixing race condition in balance deductions"

**Created structure:**
```
docs/tasks/balance-race-condition-fix/
├── README.md
├── 00-problem-analysis.md
├── 01-root-cause.md
├── 02-solution-design.md
├── 03-implementation.md
├── 04-testing.md
└── 05-verification.md
```

**README.md excerpt:**
```markdown
# Balance Race Condition Fix

Fix race condition in concurrent balance deductions causing negative balances.

---

## Quick Start

**Total Time:** 4-6 hours (1 day)

**Strategy:**
1. Analyze the problem with concrete examples
2. Identify root cause (missing pessimistic lock)
3. Design solution (SELECT FOR UPDATE)
4. Implement pessimistic locking in BalanceRepo
5. Write regression tests
6. Verify fix in all scenarios

**Goal:** Zero occurrences of negative balance due to race conditions.

---

## Phase Overview

| Phase | Description | Time | Status |
|-------|-------------|------|--------|
| [00 - Problem](./00-problem-analysis.md) | Reproduce and document issue | 1h | ⏸️ Not started |
| [01 - Root Cause](./01-root-cause.md) | Identify why race occurs | 30m | ⏸️ Not started |
| [02 - Solution](./02-solution-design.md) | Design locking strategy | 30m | ⏸️ Not started |
| [03 - Implementation](./03-implementation.md) | Add pessimistic locking | 1h | ⏸️ Not started |
| [04 - Testing](./04-testing.md) | Regression + concurrency tests | 1.5h | ⏸️ Not started |
| [05 - Verification](./05-verification.md) | Verify all scenarios fixed | 30m | ⏸️ Not started |

---

## Current Problem

**Scenario:**
```python
# Two requests process simultaneously:
# Request A: Deduct 100 from balance (current: 150)
# Request B: Deduct 100 from balance (current: 150)

# Without locking:
# 1. A reads balance: 150
# 2. B reads balance: 150 (before A commits)
# 3. A writes: 150 - 100 = 50
# 4. B writes: 150 - 100 = 50
# Result: Balance is 50 (should be -50 or one request should fail)
```

**Impact:**
- Users get free credits
- Revenue loss
- Data integrity violation

---

## Proposed Solution

**Use pessimistic locking:**
```python
# Request A: SELECT balance FROM ... WHERE id = X FOR UPDATE
# Request B: Waits for A's transaction to commit
# Result: Correct sequential processing
```

**Benefits:**
- ✅ Prevents race condition
- ✅ Database-level guarantee
- ✅ Minimal code change

---

## Success Criteria

- [ ] Concurrent test with 100 parallel requests succeeds
- [ ] Final balance is mathematically correct
- [ ] No negative balances possible
- [ ] Regression test added to test suite
- [ ] All existing tests still pass
```

---

## Example 5: Refactoring Task

**User request:** "Create task for extracting shared validation logic to core"

**Created structure:**
```
docs/tasks/validation-extraction/
├── README.md
├── 00-overview.md
├── 01-inventory.md
├── 02-core-design.md
├── 03-core-implementation.md
├── 04-tarot-migration.md
├── 05-testing.md
└── 06-documentation.md
```

**README.md excerpt:**
```markdown
# Validation Logic Extraction to Core

Extract shared validation logic from apps/template to core for reuse across all apps.

---

## Quick Start

**Total Time:** 6-8 hours (split over 2 days)

**Strategy:**
1. Inventory all validation logic in tarot app
2. Identify which validators are app-specific vs generic
3. Design core validation module structure
4. Implement generic validators in core
5. Migrate tarot app to use core validators
6. Test thoroughly
7. Document validator usage

**Goal:** All generic validation logic lives in core, apps import as needed.

---

## What Changes

**Before:**
```python
# apps/template/backend/src/app/services/validation.py
def validate_email(email: str) -> bool:
    # Duplicated in every app
```

**After:**
```python
# core/backend/src/core/services/validation.py
def validate_email(email: str) -> bool:
    # Single source of truth

# apps/template - just imports
from core.services.validation import validate_email
```

---

## Validators to Extract

**Generic (move to core):**
- Email validation
- Phone number validation
- URL validation
- Password strength
- Username format

**App-specific (keep in tarot):**
- Reading question validation
- Tarot card selection validation

---

## Success Criteria

- [ ] 5+ validators moved to core
- [ ] Tarot app imports from core
- [ ] All tests passing
- [ ] No code duplication
- [ ] Documentation updated
```

## Task Naming Patterns

**Features:** `{noun}-{capability}`
- user-profile-customization
- payment-provider-integration
- notification-system

**Migrations:** `{target}-migration`
- timestamptz-migration
- redis-session-migration
- sqlalchemy-2.0-migration

**Reviews:** `{subject}-review` or `pr{N}-{type}-review`
- payment-service-review
- pr85-architecture-review
- security-audit-review

**Fixes:** `{component}-{issue}-fix`
- balance-race-condition-fix
- session-timeout-fix
- cache-invalidation-fix

**Refactors:** `{subject}-extraction` or `{subject}-refactor`
- validation-extraction
- auth-service-refactor
- database-layer-refactor
