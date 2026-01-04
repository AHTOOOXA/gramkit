# Core Test Matrix

## The Core/App Split - How It Works

```
CORE (test once, all apps inherit confidence)
├── infrastructure/auth/telegram.py      → TelegramAuthenticator
├── infrastructure/webhooks/*            → YooKassa, Telegram validators
├── infrastructure/database/repo/base.py → BaseRepo (CRUD + locking)
├── services/sessions.py                 → SessionService (Redis)
├── services/password.py                 → PasswordService (hashing)
└── services/auth.py                     → AuthService (email/link/telegram flows)

APP (test only what you add)
├── app-specific models (Balance, etc.)
├── app-specific services (BalanceService, StatisticsService)
├── app-specific endpoints (demo.py, admin.py)
└── app-level integration (how app wires everything together)
```

**Rule:** Tests in `core/` test core code. Tests in `apps/{app}/` test ONLY app-specific code.

---

## Priority 1: Core Unit Tests (No Infrastructure)

These tests run without Docker, Redis, or Postgres. Pure unit tests.

### 1.1 TelegramAuthenticator

| Test | Type | Description |
|------|------|-------------|
| `test_verify_valid_init_data` | contract | Valid initData returns TelegramUser with correct fields |
| `test_verify_extracts_all_user_fields` | contract | All TelegramUser fields populated (id, first_name, username, is_premium, etc.) |
| `test_verify_rejects_tampered_user_id` | contract | Changing user_id in initData raises InvalidInitDataError |
| `test_verify_rejects_tampered_username` | contract | Changing username in initData raises InvalidInitDataError |
| `test_verify_rejects_wrong_bot_token` | contract | initData signed with different token raises InvalidInitDataError |
| `test_verify_rejects_empty_data` | contract | Empty string raises InvalidInitDataError |
| `test_verify_rejects_missing_hash` | contract | initData without hash raises InvalidInitDataError |
| `test_verify_rejects_missing_user` | contract | initData without user raises InvalidInitDataError |
| `test_verify_rejects_malformed_user_json` | contract | Invalid JSON in user field raises InvalidInitDataError |
| `test_generate_secret_key_deterministic` | contract | Same token always produces same secret key |

**Fixture used:** `generate_telegram_init_data()` from `core/testing/fixtures/auth.py`

### 1.2 YooKassaWebhookValidator

| Test | Type | Description |
|------|------|-------------|
| `test_valid_signature_passes` | contract | Correctly signed payload returns True |
| `test_invalid_signature_raises_401` | contract | Wrong signature raises HTTPException 401 |
| `test_missing_header_raises_401` | contract | No Authorization header raises HTTPException 401 |
| `test_empty_bearer_raises_401` | contract | "Bearer " with no signature raises HTTPException 401 |
| `test_signature_uses_correct_canonical_format` | contract | type&id&status format produces valid signature |
| `test_missing_payload_fields_raises_400` | contract | Missing type/object/id/status raises HTTPException 400 |
| `test_timing_attack_resistant` | business_logic | Uses hmac.compare_digest (constant-time) |

### 1.3 TelegramWebhookValidator

| Test | Type | Description |
|------|------|-------------|
| `test_valid_secret_passes` | contract | Correct secret token returns True |
| `test_invalid_secret_raises_401` | contract | Wrong secret raises HTTPException 401 |
| `test_missing_header_raises_401` | contract | No header raises HTTPException 401 |
| `test_empty_secret_raises_401` | contract | Empty string raises HTTPException 401 |
| `test_timing_attack_resistant` | business_logic | Uses hmac.compare_digest (constant-time) |

### 1.4 PasswordService

**Already tested in apps/template** - MOVE to core or keep as reference.

| Test | Type | Description |
|------|------|-------------|
| `test_hash_password_produces_argon2_hash` | contract | Hash starts with $argon2 |
| `test_hash_different_each_time` | contract | Same password produces different hashes (salt) |
| `test_verify_correct_password` | contract | Correct password verifies |
| `test_verify_wrong_password` | contract | Wrong password fails verification |
| `test_validate_password_min_length` | contract | <8 chars fails |
| `test_validate_password_max_length` | contract | >128 chars fails |
| `test_validate_password_requires_uppercase` | contract | No uppercase fails |
| `test_validate_password_requires_digit` | contract | No digit fails |
| `test_validate_password_requires_special` | contract | No special char fails |
| `test_generate_code_length` | contract | Generated code is 6 digits |
| `test_generate_code_numeric` | contract | Generated code is all digits |

### 1.5 SessionService (Mocked Redis)

| Test | Type | Description |
|------|------|-------------|
| `test_create_session_returns_uuid` | contract | Returns valid UUID string |
| `test_create_session_stores_user_id` | contract | Session data contains user_id |
| `test_create_session_stores_user_type` | contract | Session data contains user_type |
| `test_create_session_stores_metadata` | contract | Custom metadata is stored |
| `test_create_session_sets_ttl` | contract | Redis set called with correct expiry |
| `test_validate_session_returns_data` | contract | Valid session returns data dict |
| `test_validate_session_updates_last_accessed` | contract | last_accessed timestamp updated |
| `test_validate_session_extends_ttl` | contract | TTL extended on validation |
| `test_validate_nonexistent_returns_none` | contract | Missing session returns None |
| `test_validate_empty_id_returns_none` | contract | Empty string returns None |
| `test_validate_corrupted_json_returns_none` | contract | Invalid JSON returns None |
| `test_destroy_session_removes_from_redis` | contract | Redis delete called |
| `test_destroy_session_returns_true` | contract | Returns True on success |
| `test_destroy_nonexistent_returns_false` | contract | Returns False if not found |

---

## Priority 2: Core Integration Tests (Need Testcontainers)

These tests require PostgreSQL via testcontainers. Run with `make test`.

### 2.1 BaseRepo CRUD

| Test | Type | Description |
|------|------|-------------|
| `test_create_returns_model_with_id` | contract | Created entity has auto-generated ID |
| `test_create_persists_all_fields` | contract | All fields saved correctly |
| `test_get_by_id_returns_entity` | contract | Existing entity returned |
| `test_get_by_id_nonexistent_returns_none` | contract | Missing entity returns None |
| `test_get_by_ids_returns_multiple` | contract | Batch get returns all found |
| `test_get_by_ids_partial_match` | contract | Returns only existing entities |
| `test_get_all_returns_all` | contract | All entities returned |
| `test_update_modifies_fields` | contract | Updated fields persisted |
| `test_update_nonexistent_returns_none` | contract | Missing entity returns None |
| `test_delete_removes_entity` | contract | Entity no longer retrievable |
| `test_delete_nonexistent_returns_false` | contract | Returns False if not found |
| `test_upsert_creates_new` | contract | New entity created |
| `test_upsert_updates_existing` | contract | Existing entity updated on conflict |

### 2.2 BaseRepo Pessimistic Locking

| Test | Type | Description |
|------|------|-------------|
| `test_get_by_id_with_lock_acquires_exclusive` | business_logic | Row locked for update |
| `test_concurrent_updates_serialize_with_lock` | business_logic | 10 concurrent deductions from balance=10 → exactly 10 succeed |
| `test_lock_nowait_raises_on_conflict` | business_logic | OperationalError raised when row locked |
| `test_lock_skip_locked_returns_none` | business_logic | Returns None when row locked |
| `test_shared_lock_allows_concurrent_reads` | business_logic | Multiple readers allowed with read=True |
| `test_shared_lock_blocks_writers` | business_logic | Writer waits when shared lock held |
| `test_get_by_ids_with_lock_locks_all` | business_logic | All rows in batch locked |

---

## Priority 3: Move Existing Tests to Core

These tests already exist in `apps/template/` but test CORE services:

### From `apps/template/backend/src/app/tests/unit/`

| File | Move To | Notes |
|------|---------|-------|
| `test_password_service.py` | `core/tests/unit/services/` | 13 tests, no changes needed |
| `services/test_email_auth_service.py` | `core/tests/unit/services/` | 8 tests, update imports |
| `services/test_auth_link.py` | `core/tests/unit/services/` | 4 tests, update imports |

**Total: 25 tests to move** (removes duplication, tests core where core lives)

---

## Test Directory Structure

```
core/backend/src/core/tests/
├── __init__.py
├── conftest.py                          # Import fixtures from core/testing
├── unit/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── test_telegram_authenticator.py   # 10 tests
│   ├── webhooks/
│   │   ├── __init__.py
│   │   ├── test_yookassa_validator.py       # 7 tests
│   │   └── test_telegram_validator.py       # 5 tests
│   └── services/
│       ├── __init__.py
│       ├── test_password_service.py         # 13 tests (moved from app)
│       ├── test_session_service.py          # 14 tests
│       ├── test_email_auth_service.py       # 8 tests (moved from app)
│       └── test_auth_link_service.py        # 4 tests (moved from app)
└── integration/
    ├── __init__.py
    └── database/
        ├── __init__.py
        └── test_base_repo.py                # 20 tests
```

---

## Test Counts Summary

| Category | Tests | Infrastructure |
|----------|-------|----------------|
| Unit: TelegramAuthenticator | 10 | None |
| Unit: YooKassaValidator | 7 | None |
| Unit: TelegramValidator | 5 | None |
| Unit: PasswordService | 13 | None (moved) |
| Unit: SessionService | 14 | Mocked Redis |
| Unit: AuthService (email) | 8 | Mocked (moved) |
| Unit: AuthService (link) | 4 | Mocked (moved) |
| Integration: BaseRepo | 20 | Testcontainers PG |
| **Total** | **81** | |

---

## What Apps Keep

After moving core tests, apps only test:

### apps/template/

| Test File | Tests | What It Tests |
|-----------|-------|---------------|
| `contracts/api/test_demo.py` | 18 | TanStack Query showcase endpoints (app-specific) |
| `contracts/api/test_email_auth.py` | 24 | Email auth endpoint contracts (app integration) |
| `contracts/api/test_telegram_link_auth.py` | 3 | Link auth endpoint contracts (app integration) |

### apps/template-react/

| Test File | Tests | What It Tests |
|-----------|-------|---------------|
| `contracts/api/test_telegram_link_auth.py` | 3 | Link auth endpoint contracts (app integration) |

---

## Implementation Order

1. **Create core test structure** (30 min)
   - Create directories
   - Create conftest.py importing core/testing fixtures

2. **Unit tests - no infra** (2h)
   - TelegramAuthenticator (10 tests)
   - YooKassaValidator (7 tests)
   - TelegramValidator (5 tests)
   - SessionService with mocked Redis (14 tests)

3. **Move existing tests** (30 min)
   - Move PasswordService tests
   - Move AuthService tests
   - Update imports

4. **Integration tests** (2h)
   - BaseRepo CRUD (13 tests)
   - BaseRepo locking (7 tests)

5. **Update CI** (30 min)
   - Add core/backend to test matrix
   - Enable CI workflow

---

## Markers

All tests use markers from `.claude/shared/testing-patterns.md`:

```python
@pytest.mark.contract        # Public interface behavior (80%)
@pytest.mark.business_logic  # Algorithms, race conditions (15%)
@pytest.mark.regression      # Bug fixes with issue reference (5%)
```
