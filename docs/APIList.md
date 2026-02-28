🔐 1️⃣ AUTHENTICATION APIs
Login
POST /auth/login
Refresh Token
POST /auth/refresh
Logout
POST /auth/logout
Get Current User
GET /auth/me
👑 2️⃣ SUPER ADMIN APIs

(Super Admin can call ANY API below. These are exclusive system-level controls.)

Create Stellantis Admin
POST /admin/stellantis
Get All Stellantis Admins
GET /admin/stellantis
Get Stellantis Admin by ID
GET /admin/stellantis/{id}
Update Stellantis Admin
PATCH /admin/stellantis/{id}
Delete Stellantis Admin
DELETE /admin/stellantis/{id}
System Stats
GET /admin/system-stats
Force Analytics Rebuild
POST /admin/rebuild-analytics
🌍 3️⃣ COUNTRY APIs (Optional but future-ready)
Create Country
POST /countries
Get Countries
GET /countries
Get Country by ID
GET /countries/{id}
Update Country
PATCH /countries/{id}
Delete Country
DELETE /countries/{id}
📍 4️⃣ ZONE APIs
Create Zone
POST /zones
Get All Zones
GET /zones

Supports:

pagination

filter by country

Get Zone by ID
GET /zones/{id}
Update Zone
PATCH /zones/{id}
Delete Zone
DELETE /zones/{id}
🏢 5️⃣ FACILITY (DEALERSHIP) APIs
Create Dealership
POST /dealerships
Get All Dealerships
GET /dealerships

Supports:

filter by zone

search by name

pagination

Example:

GET /dealerships?zone_id=xxx&search=abc&page=1&limit=20
Get Dealership by ID
GET /dealerships/{id}
Update Dealership
PATCH /dealerships/{id}
Delete Dealership
DELETE /dealerships/{id}
👷 6️⃣ EMPLOYEE APIs
Create Employee
POST /employees
Get Employees
GET /employees

Supports:

filter by dealership

search by name

Get Employee by ID
GET /employees/{id}
Update Employee
PATCH /employees/{id}
Delete Employee
DELETE /employees/{id}
📋 7️⃣ AUDIT CHECKLIST CONFIGURATION APIs
Category (Level 1)
Create Category
POST /audit/categories
Get Categories
GET /audit/categories
Get Category by ID
GET /audit/categories/{id}
Update Category
PATCH /audit/categories/{id}
Delete Category
DELETE /audit/categories/{id}
Subcategory (Level 2)
Create Subcategory
POST /audit/subcategories
Get Subcategories
GET /audit/subcategories

Supports:

filter by category

Get Subcategory by ID
GET /audit/subcategories/{id}
Update Subcategory
PATCH /audit/subcategories/{id}
Delete Subcategory
DELETE /audit/subcategories/{id}
Checkpoints (Facility-level)
Create Checkpoint
POST /audit/checkpoints
Get Checkpoints
GET /audit/checkpoints

Supports:

filter by facility

filter by subcategory

Get Checkpoint by ID
GET /audit/checkpoints/{id}
Update Checkpoint
PATCH /audit/checkpoints/{id}
Delete Checkpoint
DELETE /audit/checkpoints/{id}
⏰ 8️⃣ SHIFT APIs
Get Current Shift
GET /shifts/current
Get Shift Config
GET /shifts/config
Update Shift Config (Admin)
PATCH /shifts/config
Get Shift History
GET /shifts/history?date=YYYY-MM-DD
📝 9️⃣ AUDIT EXECUTION APIs
Create Audit
POST /audits
Get Audits
GET /audits

Supports filters:

zone_id

facility_id

shift

date

status

pagination

Get Audit by ID
GET /audits/{id}
Record Checkpoint Result
POST /audits/{audit_id}/checkpoints/{checkpoint_id}
Upload Image (AI Hook)
POST /audits/{audit_id}/checkpoints/{checkpoint_id}/image
Get AI Result
GET /audits/{audit_id}/checkpoints/{checkpoint_id}/ai-result
Finalize Audit
PATCH /audits/{audit_id}/finalize
Reopen Audit (Admin Only)
PATCH /audits/{audit_id}/reopen
📊 🔟 ANALYTICS APIs
Country Summary
GET /analytics/country-summary
Zone Summary
GET /analytics/zone-summary?zone_id=xxx
Facility Summary
GET /analytics/facility-summary?facility_id=xxx
Audit Trends
GET /analytics/trends

Filters:

zone

facility

period (daily/monthly)

Category Compliance Breakdown
GET /analytics/category-breakdown
Top Non-Compliant Checkpoints
GET /analytics/top-issues
🔍 1️⃣1️⃣ GLOBAL SEARCH API
Unified Search
GET /search

Parameters:

type (dealership, employee, audit)

query

pagination

⚙️ 1️⃣2️⃣ USER MANAGEMENT APIs
Get All Users (Admin)
GET /users
Get User by ID
GET /users/{id}
Update User
PATCH /users/{id}
Change Password
PATCH /users/change-password
🗂 1️⃣3️⃣ FILE / IMAGE APIs
Get Audit Images
GET /audits/{audit_id}/images
Delete Image (Admin)
DELETE /images/{id}
🧠 1️⃣4️⃣ HEALTH & MONITORING
Health Check
GET /health
Readiness Check
GET /ready