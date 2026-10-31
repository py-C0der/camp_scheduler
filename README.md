# CIT Campus Scheduling and Venue Management Platform

A unified, full-stack campus scheduling, venue management, examination planning, disruption recovery, and AI-powered operations platform for the Chennai Institute of Technology (CIT).

Built in strict compliance with the **CIT Scheduling Problem Statement**, official dataset (`cit_public.json`), and tournament `validator.py`.

---

## 🏛️ Comprehensive Architecture & Modules (1–10)

The system integrates 10 distinct modules into a unified single-source-of-truth platform:

| Module | Core Responsibility | Engine / Tech Stack |
| :--- | :--- | :--- |
| **Module 1: Foundation & Data Ingestion** | Ingestion of courses, faculty, student groups, rooms, and constraints | FastAPI, Pydantic, SQLite / PostgreSQL |
| **Module 2: Regular Timetable Scheduler** | Automated semester timetable generation respecting all hard (H1-H12) & soft (S1-S6) rules | Google OR-Tools CP-SAT |
| **Module 3: Examination Scheduling** | Mid-semester exam scheduling with 50% half-capacity seating rule across multiple rooms | CP-SAT & First-Fit Decreasing Room Packing |
| **Module 4: Smart Venue Booking System** | Natural-language (English/Hinglish) + manual booking with deterministic priority arbitration | Gemini 2.5 Flash / Rule NLP + Deterministic Arbiter |
| **Module 5: Disruption & Rescheduling Engine** | Live blast-radius impact analysis and minimal-perturbation rescheduling | CP-SAT Perturbation Minimizer + Version Ledger |
| **Module 6: Notification & Communication Hub** | Centralized real-time alerts, user preferences, and multi-channel adapters | WebSockets, SQLite Ledger, SMTP / Twilio / Meta Adapters |
| **Module 7: Admin Dashboard, Reports & Views** | 7 authoritative KPI cards, 3-mode timetable views, room utilisation, and pending approvals | SQLite / FastAPI / HTML5 Canvas / Responsive Dashboard |
| **Module 8: AI Scheduling Assistant** | Conversational faculty rescheduling, parameter extraction, and decision explainability | Gemini 2.5 Flash / Regex Heuristics + Grounded Evidence |
| **Module 9: System Integration & E2E Testing** | End-to-end multi-persona workflows, tournament validation, cross-module clash checks | Python Unittest (66 tests) + Official `validator.py` |
| **Module 10: Deployment & Release Preparation** | Serverless production deployment, environment management, and documentation | Vercel Serverless ASGI (`api/index.py`), Uvicorn |

---

## 👥 Demo User Personas & 1-Click Role Login

The platform includes built-in role-based access control (RBAC). Use the **🔑 Login / Switch User** button in the top navigation bar to switch between official personas:

| Role | User ID | Name / Title | Department | Permissions & Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin_1` | Dean Academics | Dean's Office | Master timetable solver, disruption proposal sign-off, system reset, exports |
| **Coordinator** | `coord_cse` | Dr. Preeti Deshmukh | Computer Science | Department timetable views, exam review, venue bookings |
| **Faculty** | `F01` | Dr. Arvind Rao | Mathematics | Personal teaching schedule ($\le 4\text{h}$ daily load), leave requests, AI assistant |
| **Club Rep** | `club_robotics` | Robotics Society Lead | Student Council | Spectra-week venue booking requests in English/Hinglish, status tracking |

---

## 🚀 Key Architectural Highlights

### Module 1 & 2: Timetable Optimization
- Satisfies all mandatory constraints (room type, capacity, faculty availability, student group non-overlap, basket slot synchronization).
- Enforces lunch break protections (Period 5/6 barrier) and consecutive period limits.
- Strict daily caps: student cohorts $\le 6\text{h}/\text{day}$, faculty $\le 4\text{h}/\text{day}$.
- Strictly evaluates soft penalties ($S_1$ to $S_6$).

### Module 3: Examination Management
- Accurately schedules all 41 mid-semester examinations.
- Enforces the strict **half-capacity rule** ($\text{room\_capacity} \ge 2 \times \text{students}$) across single or multi-room allocations.
- Prevents student group and room conflicts during the exam window.
- Exports validated `exams.json`.

### Module 4: Smart Venue Booking & Approval
- Ingests all 25 Spectra-week festival booking requests.
- Accepts natural language requests in **English and Hinglish**.
- Extracts parameters dynamically: attendee counts, time windows, equipment requirements, mandatory groups.
- Evaluates strict hierarchy: `institute_event` > `guest_lecture` > `department_event` > `club_event` > `informal`.
- Never uses an LLM for algorithmic authorization; decisions are 100% deterministic with human-in-the-loop audit logs.
- Produces explainable decision summaries and exports official `bookings.json`.

### Module 5: Disruption Management & Rescheduling
- Supports the 5 official change types: `faculty_unavailable`, `room_unavailable`, `add_faculty`, `add_session`, `remove_session`.
- **Blast-Radius Impact Analysis**: Analyzes affected faculty, rooms, timetable sessions, and student groups without altering the active schedule.
- **Minimal Perturbation Objective**:
  $$\min \sum 100 \times \mathbb{I}(\text{time\_changed}) + 1 \times \mathbb{I}(\text{room\_only\_changed})$$
- **Human-in-the-Loop Approval Workflow**: Rescheduling generates a proposal (`PROP-...`). Baseline schedule is never overwritten automatically. Approval requires authorized roles (`admin` or `head_of_timetabling`) and enforces a self-approval ban.
- **Immutable Timetable Version Ledger**: Tracks version history (`baseline`, `v2_sample_disruption`, etc.) with atomic activations.
- **Cross-Module Festival Protection**: Rescheduling respects approved fest-week events and examinations, eliminating cross-module hard violations ($H_{13}$).

### Module 6: Notification, Alerts & Communication Management
- **Event-Driven Architecture**: Centralized in-memory `EventBus` listening to domain lifecycle triggers across Modules 2–5.
- **Role-Based Targeting & Recipient Resolver**: Dynamic routing to affected users (`admin`, `dept_coordinator`, `faculty`, `club_representative`).
- **User Notification Preferences**: Granular opt-in/opt-out matrix across channels (in-app, email, whatsapp, sms) and categories.
- **Real-Time Delivery & Tracking**: WebSocket live broadcast, unread badge counters, delivery logs with retry counters.
- **CIT Branded Templates**: Responsive HTML email notifications with fallback text formats.

### Module 7: Admin Dashboard, Reports & Timetable Views
- **7 Authoritative KPI Cards**: Real-time DB counts for teaching sessions, exams, bookings, pending approvals, unresolved conflicts, available rooms, and average room utilisation.
- **3-Way Weekly Timetable Viewers**:
  - **Student Group View**: 5-day $\times$ 9-period grid with free periods, combined cohorts, and elective baskets.
  - **Faculty View**: Daily teaching loads ($\le 4\text{h}$ cap), assigned cohorts, rooms, and unavailable blocks.
  - **Room View**: Distinguishes scheduled classes vs. venue bookings vs. maintenance with unused period detection.
- **Unified Pending Approvals**: Single hub for venue bookings (Mod 4) and disruption proposals (Mod 5) with role verification.
- **Live Conflict Monitor**: Real-time auditing of $H_1 - H_{14}$ hard constraints and $S_1 - S_6$ soft rules.
- **Room Utilisation Report**: Computed using the exact formula:
  $$\text{Utilisation Percentage} = \frac{\text{Occupied Available Periods}}{\text{Total Available Periods}} \times 100$$

### Module 8: AI Assistant & Decision Explainability
- Conversational schedule adjustments in English and Hinglish with security prompt-injection interception.
- Grounded explainability engine citing authoritative database rows and constraints ($H_1$–$H_{14}$, $S_1$–$S_6$).
- Deterministic offline fallback operating with 100% functionality when external LLM APIs are offline.

### Module 9 & 10: System Integration, E2E Testing & Vercel Deployment
- 66 comprehensive automated tests verifying all 10 modules end-to-end.
- 0 hard violations under official tournament `validator.py`.
- Zero-downtime serverless architecture on Vercel with path rewriting and automatic writable `/tmp` staging.

---

## 🧪 Testing and Tournament Validation

### Run Full Test Suite (66 Unit & Integration Tests)
```bash
python -m unittest discover -s backend/tests -p "test_*.py"
```
**Test Summary:**
```
Ran 66 tests in 21.878s
OK (All 66 passing, 0 errors, 0 failures)
```

### Validate Baseline Schedule with Official Tournament Validator
```bash
python CrunchWeek_StarterPack/validator.py --data CrunchWeek_StarterPack/data/cit_public.json --schedule exports/schedule.json
```
**Official Validator Output:**
```
Dataset: cit-public-v1   Schedule says: cit-public-v1   Team: CIT-DevOps
Hard violations: 0  {}
Soft penalty: 230  {'S1': 0, 'S2': 113, 'S3': 0, 'S4': 117, 'S5': 0, 'S6': 0}
Bookings: score 61.0 | approved 20, alternatives 4, rejected 1, session overrides 0, priority inversions 0
Exam soft penalty: 0
Return code: 0
```

### Validate Rescheduled Timetable after Disruption
```bash
python CrunchWeek_StarterPack/validator.py --data CrunchWeek_StarterPack/data/cit_public.json --schedule exports/schedule_after.json --baseline exports/schedule.json --disruption CrunchWeek_StarterPack/examples/sample_disruption.json
```
**Results:**
- Hard violations: `0 {}`
- Stability: Minimal perturbation (time changes heavily penalized, room moves preferred)
- Soft penalty strictly bounded
- Cross-module fest-week events fully preserved

---

## 🌐 Deployment Guide (Vercel & Local)

### Option A: 1-Click Vercel Deployment
The repository is fully pre-configured for Vercel deployment using serverless Python ASGI:
1. Connect repository `https://github.com/py-C0der/camp_scheduler.git` to **Vercel**.
2. Framework Preset: **Other**.
3. In **Project Settings &rarr; Environment Variables**, optionally add:
   - `GEMINI_API_KEY`: *(Optional)* Your Gemini API key (built-in offline NLP works without key).
4. Click **Deploy**. Vercel will read `vercel.json`, deploy `api/index.py` as serverless ASGI, and serve static assets from `public/`.

### Option B: Local Development
```bash
# 1. Clone repository
git clone https://github.com/py-C0der/camp_scheduler.git
cd camp_scheduler

# 2. Create and activate virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Start development server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
- Web Application: **`http://127.0.0.1:8000`**
- Interactive Swagger API Docs: **`http://127.0.0.1:8000/docs`**
- System Health Check: **`http://127.0.0.1:8000/health`**

---

## 📂 Project Directory Structure

```
camp_scheduler/
├── api/
│   └── index.py                 # Vercel serverless ASGI handler
├── backend/
│   ├── ai/                      # English/Hinglish NLP extractor, assistant & multi-turn dialog
│   ├── api/                     # REST API routers (dashboard, timetable, booking, disruption, ai)
│   ├── bookings/                # Deterministic booking arbiter & room matcher
│   ├── data_store/              # SQLite database (cit_campus.db)
│   ├── db/                      # Database models and connection management
│   ├── disruptions/             # Blast radius impact analyzer & CP-SAT perturbation minimizer
│   ├── engine/                  # Core timetable solver (Module 2)
│   ├── exams/                   # Exam solver & half-capacity room allocator (Module 3)
│   ├── notifications/           # EventBus, WebSocket hub, multi-channel notification engine
│   ├── schemas/                 # Pydantic schemas for requests and responses
│   ├── services/                # Master domain orchestration services
│   ├── tests/                   # 66 comprehensive unit and E2E integration test suites
│   ├── config.py                # Environment-aware database and export path resolver
│   └── main.py                  # FastAPI application entrypoint
├── CrunchWeek_StarterPack/
│   ├── data/cit_public.json     # Official CIT benchmark dataset
│   ├── examples/                # Official sample disruption & schedule files
│   └── validator.py             # Official competition tournament validator
├── exports/
│   ├── bookings.json            # Official booking decisions export
│   ├── exams.json               # Mid-semester exam schedule export
│   ├── schedule.json            # Baseline semester timetable export
│   └── schedule_after.json      # Disruption-recovered timetable export
├── frontend/
│   └── index.html               # Source single-page web application UI
├── public/
│   └── index.html               # Synced static bundle for Vercel deployment
├── .env.example                 # Environment variable templates
├── .gitignore                   # Git exclusion rules (safely excludes .env)
├── .vercelignore                # Vercel lambda deployment size optimizer
├── AI_USAGE.md                  # Comprehensive AI usage & ethical boundaries declaration
├── README.md                    # System architecture and documentation
├── requirements.txt             # Python dependencies
├── THIRD_PARTY.md               # Third-party libraries & solver declaration
└── vercel.json                  # Vercel serverless routing and rewrite rules
```

---

## 👥 Contributors

- **Saswat Das** ([@SASWATDAS406](https://github.com/SASWATDAS406))
  - **Email:** 2501020498@cgu-odisha.ac.in
  - **Role:** Lead Full-Stack Developer & Optimization Specialist

- **Omm Priyanshu Pati** ([@OMM-PRIYANSHU-PATI](https://github.com/OMM-PRIYANSHU-PATI) / [@py-C0der](https://github.com/py-C0der))
  - **Email:** ommpriyanshu4@gmail.com
  - **Role:** Full-Stack & System Integration Engineer
  - **Key Contributions:**
    - Module 9: System Integration, Multi-Persona End-to-End Workflow Verification & Tournament Validation Suite (66/66 automated tests passing)
    - Module 10: Full-Stack Vercel Serverless ASGI deployment configuration, path routing, and writable /tmp staging
    - Authentication & RBAC Service Layer (`auth_service.py`, `auth_routes.py`) with 1-click persona switching
    - Unified Dataset Management & Official Validator UI Console in `frontend/index.html`
    - Deterministic export serialization and disruption validation verification (0 hard violations)
