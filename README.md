# CIT Campus Scheduling and Venue Management Platform

A unified, full-stack campus scheduling, venue management, examination planning, and disruption recovery platform for the Chennai Institute of Technology (CIT).

Built in strict compliance with the **CIT Scheduling Problem Statement**, official dataset (`cit_public.json`), and tournament `validator.py`.

---

## 🏛️ Architecture Overview

The system is organized into 5 fully integrated modules:

| Module | Core Responsibility | Engine / Tech Stack |
| :--- | :--- | :--- |
| **Module 1: Foundation & Data Ingestion** | Ingestion of courses, faculty, student groups, rooms, and constraints | FastAPI, Pydantic, SQLite / PostgreSQL |
| **Module 2: Regular Timetable Scheduler** | Automated semester timetable generation respecting all hard (H1-H12) & soft (S1-S6) rules | Google OR-Tools CP-SAT |
| **Module 3: Examination Scheduling** | Mid-semester exam scheduling with 50% half-capacity seating rule across multiple rooms | CP-SAT & First-Fit Decreasing Room Packing |
| **Module 4: Smart Venue Booking System** | Natural-language (English/Hinglish) + manual booking with deterministic priority arbitration | Gemini 2.5 Flash / Rule NLP + Deterministic Arbiter |
| **Module 5: Disruption & Rescheduling Engine** | Live blast-radius impact analysis and minimal-perturbation rescheduling | CP-SAT Perturbation Minimizer + Version Ledger |

---

## 🚀 Key Features

### Module 1 & 2: Timetable Optimization
- Satisfies all mandatory constraints (room type, capacity, faculty availability, student group non-overlap, basket slot synchronization).
- Enforces lunch break protections and consecutive period limits.
- Evaluates soft penalties ($S_1$ to $S_6$).

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
- Supports the 5 official change types:
  1. `faculty_unavailable`
  2. `room_unavailable`
  3. `add_faculty`
  4. `add_session`
  5. `remove_session`
- **Blast-Radius Impact Analysis**: Analyzes affected faculty, rooms, timetable sessions, and student groups without altering the active schedule.
- **Minimal Perturbation Objective**:
  $$\min \sum 100 \times \mathbb{I}(\text{time\_changed}) + 1 \times \mathbb{I}(\text{room\_only\_changed})$$
- **Human-in-the-Loop Approval Workflow**: Rescheduling generates a proposal (`PROP-...`). Baseline schedule is never overwritten automatically. Approval requires authorized roles (`admin` or `head_of_timetabling`) and enforces a self-approval ban.
- **Immutable Timetable Version Ledger**: Tracks version history (`baseline`, `v2_sample_disruption`, etc.) with atomic activations.
- **Cross-Module Festival Protection**: Rescheduling respects approved fest-week events and examinations, eliminating cross-module hard violations ($H_{13}$).

---

## 🛠️ Quickstart & Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Virtual environment in `.venv`

### 2. Installation
```powershell
# Navigate to directory
cd D:\iitbbsr\camp_scheduler

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Application
```powershell
# Start FastAPI backend & embedded frontend
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
- Open browser at: **`http://127.0.0.1:8000`**
- Interactive API Docs at: **`http://127.0.0.1:8000/docs`**

---

## 🧪 Testing and Validation

### Run Full Test Suite (14 Unit Tests)
```powershell
python -m unittest discover -s backend/tests -p "test_*.py"
```

### Validate Baseline Schedule with Tournament Validator
```powershell
python CrunchWeek_StarterPack\validator.py --data CrunchWeek_StarterPack\data\cit_public.json --schedule exports\schedule.json
```
**Results:**
- Hard violations: `0 {}`
- Soft penalty: `260`
- Bookings: score `61.0` (approved 26, alternatives 4, rejected 1)
- Exam soft penalty: `0`

### Validate Rescheduled Timetable after Disruption
```powershell
python CrunchWeek_StarterPack\validator.py --data CrunchWeek_StarterPack\data\cit_public.json --schedule exports\schedule_after.json --baseline exports\schedule.json --disruption CrunchWeek_StarterPack\examples\sample_disruption.json
```
**Results:**
- Hard violations: `0 {}`
- Stability: `11 sessions moved (3 changed time, 8 room only)`
- Soft penalty: `261`
- Bookings: score `61.0`
- Exam soft penalty: `0`

---

## 📂 Project Directory Structure

```
camp_scheduler/
├── backend/
│   ├── ai/                      # English/Hinglish NLP extractor & multi-turn dialog
│   ├── api/                     # REST endpoints (booking, disruption, schedule)
│   ├── bookings/                # Deterministic booking arbiter & room matcher
│   ├── db/                      # SQLAlchemy & SQLite database models
│   ├── disruptions/             # Impact analyzer, CP-SAT rescheduling engine, version manager
│   ├── engine/                  # Core timetable solver (Module 2)
│   ├── exams/                   # Exam solver & half-capacity room allocator (Module 3)
│   ├── schemas/                 # Pydantic schemas for requests/responses
│   ├── services/                # High-level domain services
│   ├── tests/                   # Automated unittest test suites
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
│   └── index.html               # Responsive single-page UI (Tailwind CSS, FontAwesome)
├── AI_USAGE.md                  # Comprehensive AI usage & ethical boundaries declaration
├── CONTRIBUTORS.md              # Project contributor recognition
└── requirements.txt             # Python dependencies
```

---

## 👥 Contributors

- **Saswat Das** ([@SASWATDAS406](https://github.com/SASWATDAS406))
  - **Email:** 2501020498@cgu-odisha.ac.in
  - **Role:** Lead Full-Stack Developer & Optimization Specialist

