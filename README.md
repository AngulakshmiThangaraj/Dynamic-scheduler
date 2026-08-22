# Dynamic Event Scheduling & Conflict Resolver

An enterprise production full-stack platform for intelligent event scheduling, multi-dimensional conflict detection across 9 categories, weighted optimization scoring, what-if schedule simulation, cascading conflict protection, and 1-click automatic resolution.

---

## Technical Stack & Architecture

- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System with Glassmorphism, Dark Theme, Micro-animations), Vanilla JavaScript SPA (`api.js`, `app.js`).
- **Backend API**: Python FastAPI with Pydantic validation, JWT Authentication, and OpenAPI Docs (`/docs`).
- **Database**: PostgreSQL / SQLite with SQLAlchemy ORM, relational schemas, foreign keys, indexes, and transactions.
- **Scheduling & Conflict Engine**: Multi-dimensional conflict detector, 6-factor weighted slot optimizer, dry-run what-if simulator, and auto-resolver.

---

## Quick Start (Local Execution)

### 1. Install & Run Backend Server
```powershell
& "C:\Users\ANGULAKSHMI T\AppData\Local\Programs\Python\Python313\python.exe" -m uvicorn backend.main:app --port 5000 --reload
```
Open your browser at `http://localhost:5000`.

### 2. Default Seed Credentials

| Role | Email | Password | Full Name |
| :--- | :--- | :--- | :--- |
| **ADMIN** | `admin@company.com` | `admin123` | Sarah Jenkins |
| **ORGANIZER** | `organizer@company.com` | `org123` | Alex Rivera |
| **PARTICIPANT** | `dev1@company.com` | `dev123` | David Chen |
| **PARTICIPANT** | `dev2@company.com` | `dev123` | Elena Rostova |

---

## Key Features

1. **Multi-Dimensional Conflict Engine (9 Categories)**:
   - Time Conflicts
   - Participant Conflicts
   - Room Conflicts
   - Resource Conflicts
   - Working Hour Conflicts
   - Holiday Conflicts
   - Buffer/Travel Conflicts
   - Recurring Event Conflicts
   - Room Capacity Conflicts

2. **Smart Slot Optimizer (Weighted Scoring)**:
   - Participant Availability (30%)
   - Priority Compatibility (20%)
   - Room Availability (15%)
   - Preferred Time (15%)
   - Deadline Compatibility (10%)
   - Buffer Compatibility (10%)

3. **What-If Simulation**:
   - Clones schedule state in memory to evaluate conflicts removed vs new conflicts before committing changes to the database.

4. **Cascading Conflict Protection & Auto-Resolution**:
   - Rejects candidate slots that induce secondary hard conflicts on affected participants or rooms.

5. **Schedule History & Audit Log**:
   - Full tracking of who changed what, old vs new values, reason, and timestamps.
