# Phase 2 — Authentication, RBAC & Multi-Tenancy

> **Goal:** Build the custom authentication system (Argon2 + JWT + refresh tokens), role-based access control, multi-tenant organization model, and the user/org/restaurant management APIs. After this phase, users can register, log in, create organizations, invite members, and be assigned roles.

> **Depends on:** Phase 1 (Foundation)

---

## Step 2.1 — Database Models

### 2.1.1 — Organization Model

**File:** `apps/api/app/models/organization.py`

```text
Table: organizations
─────────────────────
id            UUID, PK, default uuid4
name          VARCHAR(255), NOT NULL
slug          VARCHAR(255), UNIQUE, NOT NULL
created_at    TIMESTAMP WITH TZ, default now()
updated_at    TIMESTAMP WITH TZ, default now(), on update now()
```

- Slug is auto-generated from name (lowercase, hyphens, no special chars)
- Unique constraint on `slug`

### 2.1.2 — User Model

**File:** `apps/api/app/models/user.py`

```text
Table: users
────────────
id                UUID, PK, default uuid4
organization_id   UUID, FK → organizations.id, NOT NULL
email             VARCHAR(255), UNIQUE, NOT NULL
password_hash     VARCHAR(255), NOT NULL
name              VARCHAR(255), NOT NULL
is_active         BOOLEAN, default true
created_at        TIMESTAMP WITH TZ
updated_at        TIMESTAMP WITH TZ
```

- Index on `email` (unique)
- Index on `organization_id`
- `password_hash` is NEVER returned in API responses

### 2.1.3 — Role Model

**File:** `apps/api/app/models/role.py`

```text
Table: roles
────────────
id          UUID, PK
name        VARCHAR(50), UNIQUE, NOT NULL
description VARCHAR(255)
```

**Seed values (created via migration or seed script):**
```text
OWNER
ADMIN
MANAGER
AGENT
VIEWER
```

### 2.1.4 — UserRole Model (Join Table)

**File:** `apps/api/app/models/user_role.py`

```text
Table: user_roles
──────────────────
id        UUID, PK
user_id   UUID, FK → users.id, NOT NULL
role_id   UUID, FK → roles.id, NOT NULL
```

- Unique constraint on `(user_id, role_id)` — a user can't have the same role twice
- Index on `user_id`

### 2.1.5 — Restaurant Model

**File:** `apps/api/app/models/restaurant.py`

```text
Table: restaurants
───────────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL
name              VARCHAR(255), NOT NULL
address           TEXT
phone             VARCHAR(50)
email             VARCHAR(255)
website           VARCHAR(255)
timezone          VARCHAR(50), default 'UTC'
created_at        TIMESTAMP WITH TZ
updated_at        TIMESTAMP WITH TZ
```

- Index on `organization_id`

### 2.1.6 — Models Registry

**File:** `apps/api/app/models/__init__.py`

Import all models here so Alembic discovers them:
```python
from app.models.organization import Organization
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.restaurant import Restaurant
```

### 2.1.7 — Generate Alembic Migration

```bash
cd apps/api
alembic revision --autogenerate -m "add auth and org tables"
alembic upgrade head
```

**Verification:** Tables exist in PostgreSQL. `\dt` shows `organizations`, `users`, `roles`, `user_roles`, `restaurants`.

---

## Step 2.2 — Pydantic Schemas

**File:** `apps/api/app/schemas/auth.py`

```python
# RegisterRequest: email, password, name, organization_name
# LoginRequest: email, password
# TokenResponse: access_token, refresh_token, token_type
# RefreshRequest: refresh_token
# UserResponse: id, email, name, organization_id, roles, is_active, created_at
# (password_hash is NEVER in any response schema)
```

**File:** `apps/api/app/schemas/organization.py`

```python
# OrganizationCreate: name
# OrganizationResponse: id, name, slug, created_at
# OrganizationUpdate: name (optional)
```

**File:** `apps/api/app/schemas/restaurant.py`

```python
# RestaurantCreate: name, address, phone, email, website, timezone
# RestaurantResponse: id, name, address, phone, email, website, timezone, created_at
# RestaurantUpdate: all fields optional
```

**File:** `apps/api/app/schemas/user.py`

```python
# UserCreate: email, password, name, role (default AGENT)
# UserUpdate: name, is_active (optional)
# UserRoleAssign: role_name
```

---

## Step 2.3 — Password Hashing

**File:** `apps/api/app/core/security.py`

**Functions:**
```python
from argon2 import PasswordHasher

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hash: str) -> bool:
    try:
        return ph.verify(hash, password)
    except Exception:
        return False
```

---

## Step 2.4 — JWT Token Management

**File:** `apps/api/app/core/jwt.py`

**Functions:**

```python
def create_access_token(data: dict) -> str:
    """
    Creates a JWT access token.
    - Payload: sub (user_id), org_id (organization_id), roles (list), exp
    - Expiry: settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    - Secret: settings.JWT_SECRET
    - Algorithm: HS256
    """

def create_refresh_token(data: dict) -> str:
    """
    Creates a JWT refresh token.
    - Payload: sub (user_id), exp
    - Expiry: settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    - Secret: settings.JWT_REFRESH_SECRET
    - Algorithm: HS256
    """

def decode_access_token(token: str) -> dict:
    """Decodes and validates an access token. Raises on expired/invalid."""

def decode_refresh_token(token: str) -> dict:
    """Decodes and validates a refresh token. Raises on expired/invalid."""
```

---

## Step 2.5 — FastAPI Dependencies

**File:** `apps/api/app/core/deps.py`

### `get_current_user`

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    1. Extract token from Authorization: Bearer <token>
    2. Decode JWT
    3. Fetch user from DB by user_id
    4. Verify user is active
    5. Return User object
    Raise 401 if any step fails.
    """
```

### `get_current_organization`

```python
async def get_current_organization(
    current_user: User = Depends(get_current_user),
) -> UUID:
    """Returns the organization_id from the current user. 
    Used to scope ALL queries."""
```

### Role-checking dependency factory

```python
def require_roles(*roles: str):
    """
    Returns a dependency that checks if the current user has 
    at least one of the specified roles.
    
    Usage:
        @router.post("/admin-only", dependencies=[Depends(require_roles("OWNER", "ADMIN"))])
    
    Raises 403 if user lacks the required role.
    """
```

---

## Step 2.6 — Repositories

### `apps/api/app/repositories/organization_repo.py`

```python
class OrganizationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, name: str, slug: str) -> Organization: ...
    async def get_by_id(self, org_id: UUID) -> Organization | None: ...
    async def get_by_slug(self, slug: str) -> Organization | None: ...
    async def update(self, org_id: UUID, **kwargs) -> Organization: ...
```

### `apps/api/app/repositories/user_repo.py`

```python
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, email: str, password_hash: str, name: str, org_id: UUID) -> User: ...
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def list_by_org(self, org_id: UUID) -> list[User]: ...
    async def update(self, user_id: UUID, **kwargs) -> User: ...
    async def assign_role(self, user_id: UUID, role_id: UUID) -> None: ...
    async def get_user_roles(self, user_id: UUID) -> list[Role]: ...
```

### `apps/api/app/repositories/restaurant_repo.py`

```python
class RestaurantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, org_id: UUID, **kwargs) -> Restaurant: ...
    async def get_by_id(self, restaurant_id: UUID, org_id: UUID) -> Restaurant | None: ...
    async def list_by_org(self, org_id: UUID) -> list[Restaurant]: ...
    async def update(self, restaurant_id: UUID, org_id: UUID, **kwargs) -> Restaurant: ...
    async def delete(self, restaurant_id: UUID, org_id: UUID) -> None: ...
```

**CRITICAL:** Every query in every repository that returns business data MUST filter by `organization_id`. This is the multi-tenancy enforcement.

---

## Step 2.7 — Services

### `apps/api/app/services/auth_service.py`

```python
class AuthService:
    def __init__(self, user_repo: UserRepository, org_repo: OrganizationRepository):
        ...
    
    async def register(self, email, password, name, organization_name) -> TokenResponse:
        """
        1. Check email not already taken
        2. Create organization (generate slug from name)
        3. Hash password with Argon2
        4. Create user linked to org
        5. Assign OWNER role
        6. Generate access + refresh tokens
        7. Return TokenResponse
        """
    
    async def login(self, email, password) -> TokenResponse:
        """
        1. Find user by email
        2. Verify password
        3. Check is_active
        4. Fetch roles
        5. Generate tokens
        6. Return TokenResponse
        """
    
    async def refresh(self, refresh_token: str) -> TokenResponse:
        """
        1. Decode refresh token
        2. Fetch user
        3. Generate new access + refresh tokens
        4. Return TokenResponse
        """
```

### `apps/api/app/services/user_service.py`

```python
class UserService:
    async def invite_user(self, org_id, email, password, name, role_name) -> User:
        """Create a user within the current org and assign role."""
    
    async def update_user(self, user_id, org_id, **kwargs) -> User: ...
    async def list_users(self, org_id) -> list[User]: ...
    async def assign_role(self, user_id, org_id, role_name) -> None: ...
```

### `apps/api/app/services/restaurant_service.py`

```python
class RestaurantService:
    async def create(self, org_id, **data) -> Restaurant: ...
    async def get(self, restaurant_id, org_id) -> Restaurant: ...
    async def list(self, org_id) -> list[Restaurant]: ...
    async def update(self, restaurant_id, org_id, **data) -> Restaurant: ...
    async def delete(self, restaurant_id, org_id) -> None: ...
```

---

## Step 2.8 — API Route Handlers

### `apps/api/app/api/auth.py`

```text
POST /api/v1/auth/register     → AuthService.register()
POST /api/v1/auth/login        → AuthService.login()
POST /api/v1/auth/refresh      → AuthService.refresh()
POST /api/v1/auth/logout       → (invalidate/no-op for JWT)
GET  /api/v1/auth/me           → Return current user (from dep)
```

### `apps/api/app/api/users.py`

```text
POST   /api/v1/users            → Invite user (OWNER, ADMIN only)
GET    /api/v1/users             → List users in org
GET    /api/v1/users/{id}        → Get user
PATCH  /api/v1/users/{id}        → Update user (OWNER, ADMIN only)
POST   /api/v1/users/{id}/role   → Assign role (OWNER only)
```

### `apps/api/app/api/organizations.py`

```text
GET    /api/v1/organizations/current   → Get current org
PATCH  /api/v1/organizations/current   → Update current org (OWNER only)
```

### `apps/api/app/api/restaurants.py`

```text
POST   /api/v1/restaurants         → Create restaurant (OWNER, ADMIN)
GET    /api/v1/restaurants          → List restaurants in org
GET    /api/v1/restaurants/{id}     → Get restaurant
PATCH  /api/v1/restaurants/{id}     → Update restaurant (OWNER, ADMIN)
DELETE /api/v1/restaurants/{id}     → Delete restaurant (OWNER only)
```

### Register Routers in `main.py`

```python
from app.api import auth, users, organizations, restaurants

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(restaurants.router, prefix="/api/v1/restaurants", tags=["restaurants"])
```

---

## Step 2.9 — Seed Roles Script

**File:** `apps/api/scripts/seed_roles.py`

**What:** Script that inserts the 5 roles into the `roles` table if they don't exist:
```text
OWNER, ADMIN, MANAGER, AGENT, VIEWER
```

Can also be done inside the Alembic migration as data migration.

---

## Step 2.10 — Rate Limiting

**File:** `apps/api/app/core/rate_limit.py`

**What:** Simple Redis-based rate limiter for auth endpoints.

```python
class RateLimiter:
    def __init__(self, redis_url: str, max_requests: int, window_seconds: int):
        ...
    
    async def check(self, key: str) -> bool:
        """Returns True if within limit, False if rate-limited."""
```

Apply to:
- `POST /auth/login` → 10 requests per minute per IP
- `POST /auth/register` → 5 requests per minute per IP

---

## Step 2.11 — Error Handling

**File:** `apps/api/app/core/exceptions.py`

```python
class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

# Pre-defined exceptions:
class NotFoundError(AppException): ...      # 404
class UnauthorizedError(AppException): ...  # 401
class ForbiddenError(AppException): ...     # 403
class ConflictError(AppException): ...      # 409
class ValidationError(AppException): ...    # 422
class RateLimitError(AppException): ...     # 429
```

**Register exception handlers in `main.py`:**
```python
@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}}
    )
```

Never leak stack traces, DB internals, or credentials in error responses.

---

## Phase 2 Completion Checklist

- [ ] `organizations` table created via Alembic migration
- [ ] `users` table created with `organization_id` FK
- [ ] `roles` table created, seeded with 5 roles
- [ ] `user_roles` join table created
- [ ] `restaurants` table created with `organization_id` FK
- [ ] Argon2 password hashing works
- [ ] JWT access token creation/validation works
- [ ] JWT refresh token creation/validation works
- [ ] `POST /auth/register` → creates org + user + OWNER role + returns tokens
- [ ] `POST /auth/login` → validates password, returns tokens
- [ ] `POST /auth/refresh` → rotates tokens
- [ ] `GET /auth/me` → returns authenticated user
- [ ] `get_current_user` dependency works on protected routes
- [ ] `require_roles()` dependency enforces role checks
- [ ] All repository queries filter by `organization_id`
- [ ] User CRUD API works (invite, list, get, update, assign role)
- [ ] Restaurant CRUD API works
- [ ] Rate limiting on auth endpoints
- [ ] Custom exception handler returns structured errors
- [ ] No password hashes leaked in any API response
- [ ] `git commit -m "Phase 2: Auth, RBAC, multi-tenancy"`

---

## Transition to Phase 3

Once all boxes are checked, proceed to [03-leads-verification.md](./03-leads-verification.md).

Phase 3 will add the Lead model, CSV import, the custom email verification engine (syntax/DNS/MX/SMTP), lead scoring, verification jobs via Celery, and progress tracking.
