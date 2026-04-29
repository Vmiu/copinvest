---
phase: 01-data-foundation
plan: 02
subsystem: auth
tags: [jwt, pyjwt, pwdlib, bcrypt, fastapi, oauth2, alembic]

requires:
  - phase: 01-01
    provides: SQLAlchemy models (User), FastAPI app skeleton, test fixtures
provides:
  - JWT authentication with login endpoint (POST /api/v1/auth/token)
  - Password hashing with pwdlib bcrypt (not passlib)
  - get_current_user FastAPI dependency extracting identity from Bearer token
  - User seeding from JSON config file
  - Alembic async migrations with initial schema
affects: [01-03, 01-04, 02-api, 04-telegram]

tech-stack:
  added: [python-multipart]
  patterns: [OAuth2PasswordBearer with PyJWT HS256, pwdlib BcryptHasher, get_settings() deferred call in security functions]

key-files:
  created:
    - backend/core/security.py
    - backend/core/dependencies.py
    - backend/routers/auth.py
    - backend/repositories/user_repo.py
    - backend/schemas/auth.py
    - backend/scripts/seed_users.py
    - backend/seed_users.json
    - alembic/env.py
    - alembic/versions/0f1eb48835fc_create_users_table.py
    - tests/test_security.py
    - tests/test_auth.py
  modified:
    - backend/main.py
    - pyproject.toml

key-decisions:
  - "Used pwdlib BcryptHasher explicitly instead of PasswordHash.recommended() for deterministic hasher selection"
  - "Added GET /api/v1/auth/me protected endpoint for testing token-based access"
  - "Alembic configured with async env.py reading DB URL from settings (not hardcoded in alembic.ini)"
  - "Added python-multipart dependency for OAuth2PasswordRequestForm parsing"

patterns-established:
  - "Auth: OAuth2PasswordBearer + PyJWT HS256 with role in JWT payload"
  - "Security: get_settings() called inside functions (not module-level) for testability"
  - "Repository: async select with scalar_one_or_none for nullable lookups"
  - "Router: APIRouter with prefix and tags, Depends for DB and auth injection"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03]

duration: 6min
completed: 2026-04-29
---

# Phase 01 Plan 02: Authentication System Summary

**JWT auth with pwdlib bcrypt hashing, OAuth2 login endpoint, get_current_user dependency, user seeding, and Alembic async migrations**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-29T12:20:00Z
- **Completed:** 2026-04-29T12:26:00Z
- **Tasks:** 2 (TDD: 5 commits total -- 2 RED + 2 GREEN + 1 chore)
- **Files modified:** 17

## Accomplishments
- Complete login flow: POST /api/v1/auth/token accepts email+password, returns JWT with sub and role claims
- Password hashing with pwdlib BcryptHasher (avoids passlib Python 3.13 breakage per Pitfall 1)
- get_current_user dependency extracts user_id and role from Bearer token without DB lookup (D-07)
- User seeding script loads 3 demo users (adviser, senior_adviser, compliance) from JSON
- Alembic async migrations with initial schema covering users, sessions, and audit_log tables
- 15 passing tests (9 security unit + 6 auth integration)

## Task Commits

Each task followed TDD (RED then GREEN):

1. **Task 1 RED: Failing security tests** - `32c8c8b` (test)
2. **Task 1 GREEN: Security utilities and auth dependency** - `c5891dd` (feat)
3. **Task 2 RED: Failing auth integration tests** - `3efb0ee` (test)
4. **Task 2 GREEN: Auth router, user repo, seed script** - `11ef8d6` (feat)
5. **Alembic setup and initial migration** - `eb3a98f` (chore)

## Files Created/Modified
- `backend/core/security.py` - JWT encode/decode with PyJWT, password hashing with pwdlib
- `backend/core/dependencies.py` - get_current_user FastAPI dependency (OAuth2PasswordBearer)
- `backend/routers/auth.py` - POST /api/v1/auth/token login + GET /api/v1/auth/me protected endpoint
- `backend/repositories/user_repo.py` - get_user_by_email async query
- `backend/schemas/auth.py` - TokenResponse Pydantic model
- `backend/scripts/seed_users.py` - CLI script to seed users from JSON
- `backend/seed_users.json` - 3 demo users (one per role)
- `alembic.ini` - Alembic configuration
- `alembic/env.py` - Async migration runner
- `alembic/versions/0f1eb48835fc_create_users_table.py` - Initial migration
- `backend/main.py` - Added auth router include
- `pyproject.toml` - Added python-multipart dependency
- `tests/test_security.py` - 9 tests for hashing and JWT
- `tests/test_auth.py` - 6 tests for login and protected access

## Decisions Made
- Used `PasswordHash((BcryptHasher(),))` instead of `PasswordHash.recommended()` for explicit hasher selection -- avoids surprises if pwdlib changes defaults
- Added `GET /api/v1/auth/me` endpoint as a protected route for testing token-based access (plan only specified `/token` but tests needed a protected endpoint to verify get_current_user)
- Alembic env.py reads database URL from `get_settings()` rather than hardcoding in alembic.ini -- consistent with the config pattern from Plan 01
- Added `python-multipart` to pyproject.toml -- required by FastAPI for `OAuth2PasswordRequestForm` form data parsing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added python-multipart dependency**
- **Found during:** Task 2
- **Issue:** FastAPI OAuth2PasswordRequestForm requires python-multipart for form data parsing; without it, the login endpoint fails at runtime
- **Fix:** Added python-multipart to pyproject.toml dependencies
- **Files modified:** pyproject.toml
- **Verification:** Login endpoint accepts form data, all tests pass
- **Committed in:** 11ef8d6

**2. [Rule 2 - Missing Critical] Added Alembic async migration setup**
- **Found during:** After Task 2
- **Issue:** Plan did not include Alembic setup, but the project needs reproducible schema migrations (not just auto-create_all in lifespan)
- **Fix:** Initialized Alembic with async template, configured env.py, generated initial migration for all 3 tables
- **Files modified:** alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/0f1eb48835fc_create_users_table.py
- **Verification:** `alembic upgrade head` runs cleanly
- **Committed in:** eb3a98f

**3. [Rule 2 - Missing Critical] Added GET /api/v1/auth/me protected endpoint**
- **Found during:** Task 2
- **Issue:** Plan specified tests for protected endpoint access but no protected endpoint existed beyond /health (which is public)
- **Fix:** Added /api/v1/auth/me endpoint that returns current user identity via get_current_user dependency
- **Files modified:** backend/routers/auth.py
- **Verification:** test_protected_endpoint_valid_token and test_protected_endpoint_no_token pass
- **Committed in:** 11ef8d6

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 missing critical)
**Impact on plan:** All fixes necessary for correctness and testability. No scope creep.

## TDD Gate Compliance

- RED gate: `32c8c8b` (test) and `3efb0ee` (test) -- failing tests committed before implementation
- GREEN gate: `c5891dd` (feat) and `11ef8d6` (feat) -- implementation making tests pass
- REFACTOR gate: Not needed -- code was clean after GREEN

## Issues Encountered
None

## User Setup Required
None - uses existing .env from Plan 01.

## Next Phase Readiness
- Auth primitive (get_current_user) ready for all subsequent endpoints
- Audit service (Plan 03) can now reference authenticated user identity
- Qdrant RBAC filtering (Plan 04) can inject role from JWT payload
- Alembic migrations ready for schema evolution in future plans

## Self-Check: PASSED

- All 10 key files verified present on disk
- All 5 task commits verified in git log (32c8c8b, c5891dd, 3efb0ee, 11ef8d6, eb3a98f)

---
*Phase: 01-data-foundation*
*Completed: 2026-04-29*
