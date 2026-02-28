📄 PRODUCT REQUIREMENTS DOCUMENT (Backend – FastAPI)
Product Name

Dealer Hygiene Compliance Backend

Version

Backend v1.0

Scope

Backend REST API system using Python + FastAPI

1️⃣ System Overview

The system is a multi-tenant, hierarchical compliance backend that supports:

Role-based access control (RBAC)

Organizational hierarchy (Super Admin → Zone → Facility → Employee)

Configurable audit checklist engine

Shift-based audit enforcement

AI-assisted image validation (placeholder)

Consolidated analytics APIs

Search and filtering APIs

Frontend/mobile apps are consumers of this backend.

2️⃣ Roles & Access Control
Roles

SUPER_ADMIN (seeded manually in DB)

STELLANTIS_ADMIN

DEALERSHIP

EMPLOYEE

Core Rule

Super Admin bypasses all restrictions.

All other roles are restricted to their hierarchy.

3️⃣ Core Domain Model
3.1 Organization
Zone
 → Facility (Dealership)
     → Employees

Optional future:

Country → Zone
3.2 Audit Hierarchy
Category (L1)
 → Subcategory (L2)
     → Checkpoint (Facility-specific)

Checkpoints are configurable per facility.

4️⃣ Functional Modules
MODULE 1: Authentication & RBAC
Requirements

JWT-based login

Password hashing (bcrypt)

Role-based dependency in FastAPI

Hierarchy validation middleware

Acceptance Criteria

Invalid role → 403

Unauthorized entity access → 403

Expired token → 401

MODULE 2: Organizational Management
Zones

Create

Get all

Get by ID

Update

Delete

Filter by country (future-ready)

Dealerships (Facilities)

Create

Get all

Get by ID

Filter by zone

Search by name

Update

Delete

Employees

Create

Get by dealership

Update

Delete

MODULE 3: Audit Checklist Configuration
Categories (L1)

Managed by:

Super Admin

Stellantis Admin

CRUD required.

Subcategories (L2)

Belongs to Category.

CRUD required.

Checkpoints

Belongs to:

Subcategory

Facility

Created/edited by:

Dealership

Super Admin

Must support:

Create

Update

Delete

Get by facility

Get by subcategory

Checkpoint properties:

name

description

requires_photo (boolean)

active (boolean)

MODULE 4: Shift Engine

Shifts are time-bound:

Example:

MORNING: 08:00–14:00

EVENING: 14:00–20:00

APIs required:

Get current shift

Validate shift before audit creation

Prevent future shift audit creation

Prevent duplicate audit per shift per facility

MODULE 5: Audit Execution Engine
Create Audit

Constraints:

Only current shift allowed

Only one per shift per facility

Audit states:

IN_PROGRESS

AI_PENDING

FINALIZED

Record Checkpoint Result

For each checkpoint:

compliant / non-compliant

optional manual flag

optional image

Image Upload (AI Hook)

FastAPI must:

Accept image

Store in object storage (S3/local for now)

Create AI_PENDING status

Return placeholder AI response

Future:

Async task queue (Celery / BackgroundTasks)

Call third-party AI service

Finalize Audit

Rules:

Only dealership or employee of same facility

Lock audit

Immutable after finalization

MODULE 6: Analytics Engine

Must support aggregated queries.

Country Summary

Total audits

Compliance %

Monthly trend

Zone Summary

Facility ranking

Compliance %

Audit count

Facility Summary

Shift performance

Category compliance

Failure rate per checkpoint

Filtering Requirements

All analytics must support:

date range

zone filter

facility filter

shift filter

MODULE 7: Search Engine

Global search endpoint:

Search types:

dealership

employee

audit

Must support:

Partial match (ILIKE)

Pagination

Role-based restriction

5️⃣ API Requirements

All list endpoints must support:

page

limit

sort

order

filters

Example:

GET /dealerships?page=1&limit=20&zone_id=xxx
6️⃣ Data Integrity Rules

No cross-zone data leakage.

Facility cannot see another facility’s audits.

Checkpoints cannot belong to multiple facilities.

Audit cannot be edited after FINALIZED.

AI output does not override human decision.

7️⃣ Non-Functional Requirements
Performance

Index on:

zone_id

facility_id

created_at

shift_type

Analytics queries optimized via aggregation tables (future)

Security

JWT with expiry

Password hashing

Rate limiting

Input validation (Pydantic models)

File type validation for image upload

Scalability

PostgreSQL recommended

Async FastAPI endpoints

Background AI processing ready

8️⃣ Technical Stack (Backend Only)

Python 3.11+

FastAPI

SQLAlchemy or Tortoise ORM

PostgreSQL

Alembic migrations

Pydantic v2

JWT (python-jose)

bcrypt

Optional: Celery / Redis for AI async

9️⃣ Development Phases
Phase 1

Auth

RBAC

Zones

Dealerships

Employees

Phase 2

Checklist configuration

Shift engine

Audit creation

Finalization

Phase 3

AI image placeholder

Analytics endpoints

Search endpoints

Phase 4

Optimization

Index tuning

Background AI jobs

🔟 Success Criteria

Zero cross-tenant data leakage

Audit locking works reliably

Shift enforcement works correctly

Analytics accurate within 1% margin

API response time < 300ms (excluding image upload)