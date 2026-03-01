# Dealer Hygiene Compliance Backend

Production-grade FastAPI backend for multi-tenant, hierarchical compliance: RBAC, audit checklist engine, shift-based audits, and analytics.

## Stack

- Python 3.11+
- FastAPI, Pydantic v2
- SQLAlchemy 2.0 (async), PostgreSQL, Alembic
- JWT (python-jose), bcrypt

## Setup

1. **Create virtualenv and install dependencies**

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Configure environment**

   Copy `.env.example` to `.env` and set at least:

   - `APP_POSTGRES_*` for PostgreSQL
   - `APP_JWT_SECRET_KEY` for production

3. **Run migrations**

   Ensure `postgres_migrations/env.py` imports all schema classes (see `.cursor/rules/migrations-and-env.mdc`). Then:

   ```bash
   alembic -c alembic.ini upgrade head
   ```

   If using a custom Alembic config that points at `postgres_migrations/`, run that instead.

4. **Seed Super Admin (optional)**

   Insert a user with `role_type = 'SUPER_ADMIN'` and a bcrypt-hashed password into the `user` table (e.g. via SQL or a one-off script).

5. **Start the app**

   ```bash
   python -m src.main
   ```

   Or:

   ```bash
   uvicorn src.app:app --host 0.0.0.0 --port 8000
   ```

## API

- **OpenAPI:** `GET /docs` (Swagger), `GET /redoc` (ReDoc)
- **Auth:** `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`
- **Zones:** `POST/GET/PATCH/DELETE /zones`
- **Dealerships:** `POST/GET/PATCH/DELETE /dealerships`
- **Employees:** `POST/GET/PATCH/DELETE /employees`
- **Categories:** `POST/GET/PATCH/DELETE /categories` (facility-scoped)
- **Checkpoints:** `POST/GET/PATCH/DELETE /checkpoints` (facility-scoped, image required on create)
- **Checkpoint-Categories:** `POST/GET/DELETE /checkpoints/{id}/categories` (many-to-many)
- **Shifts:** `GET /shifts/current`, `GET /shifts/config`
- **Audits:** `POST/GET /audits`, checkpoint result, image upload, finalize, reopen
- **Analytics:** `/analytics/country-summary`, `/zone-summary`, `/facility-summary`, etc.
- **Search:** `GET /search?type=dealership|employee|audit&query=...`
- **Health:** `GET /health`, `GET /ready`

All list endpoints support `?page=1&limit=20&sort=created_at&order=desc` and role-based access. Super Admin bypasses hierarchy; others are scoped by zone/facility.

## Project layout

- `src/api/` – HTTP layer (routers, dependencies)
- `src/business_services/` – domain logic
- `src/database/` – base, session, `postgres/schema/` (SQLAlchemy), `repositories/` and `repositories/schemas/` (Pydantic)
- `postgres_migrations/` – Alembic migrations
- `src/di/` – container and service wiring
- `src/configs/`, `src/logging/`, `src/exceptions/`, `src/utils/`

## Rules

- Follow `.cursor/rules/*.mdc` (Python standards, architecture, migrations, tests).
- No emojis in logs; use `[OK]`, `[ERROR]`, etc.
- API uses only business services via `Depends(get_*_service)`; repositories return Pydantic; hierarchy enforced in services.
