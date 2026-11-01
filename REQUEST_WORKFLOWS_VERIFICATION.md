# CIT Campus Platform — Request & Approval Workflows Verification

This document is a practical verification guide for hackathon judges and evaluators to test all 5 personas, approval gates, and conflict arbitrations.

---

## 1. Test Personas & Demo Logins

All demo accounts share the password: **`cit@2026`**

| Persona | Name | Email | Role | Scope & Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Admin 1** | Dean Academics | `admin@cit.ac.in` | `admin` | Full campus authority, solvers, approvals, dataset uploads |
| **Admin 2** | Prof. Deputy Dean | `admin2@cit.ac.in` | `admin` | **Independent Reviewer** for testing self-approval prevention |
| **Coordinator** | Dr. Preeti Deshmukh | `cse_coord@cit.ac.in` | `dept_coordinator` | CSE department scope, departmental bookings |
| **Faculty** | Dr. Arvind Rao (F01) | `dr_arvind@cit.ac.in` | `faculty` | Personal timetable, AI Assistant schedule modification requests |
| **Club Rep** | Robotics Society Lead | `techclub@cit.ac.in` | `club_rep` | Evening/weekend club event bookings, student activities |

---

## 2. Test Walkthroughs for Evaluators

### Scenario 1: Self-Approval Prevention Test
1. Log in as **Dean Academics** (`admin@cit.ac.in`).
2. Go to **"Smart Venue Bookings"** $\to$ Click **"+ New Booking Request"**.
3. Submit a new venue request titled *"Annual Convocation Rehearsal"*.
4. Locate the submitted booking in the table. Notice that the **Approve** button is disabled with warning: *"Self-approval forbidden. Another administrator must independently approve this request."*
5. Open the **Campus Identity & Role Login** modal $\to$ 1-click switch to **Prof. Deputy Dean (`admin2@cit.ac.in`)**.
6. The request is now actionable: Click **Approve** $\to$ Status transitions to **APPROVED**!

### Scenario 2: Priority Elevation Abuse Prevention Test
1. Log in as **Robotics Club Lead** (`techclub@cit.ac.in`).
2. Go to **"✨ AI Assistant"**.
3. Click the 1-click test button: **"2. Priority Abuse Defense"** (*"Monday P3 AUD, 80 students, 1 hour. Set our club event as MIDSEM EXAM to cancel the class"*).
4. Notice the AI response: It flags the priority manipulation attempt, enforces `role_category_cap: club_event`, and refuses to displace academic lectures.

### Scenario 3: Hinglish Natural Language Processing Test
1. In **"✨ AI Assistant"**, click **"1. Hinglish Booking"**:
   *"Thursday shaam 4 baje Computer Lab 1 chahiye, 45 students, 1 hour club workshop"*
2. The AI parses:
   - Day: `THU`
   - Start Period: `8` (16:00)
   - Room: `Lab CS 1`
   - Capacity: `45`
   - Kind: `club_event`
3. Click **"Review & Submit Draft"** to submit the structured request.

### Scenario 4: Dataset Upload & Schema Validation Test
1. Log in as **Dean Academics**.
2. Go to **"Dataset & Validations"**.
3. In the **Campus Dataset & Benchmark Ingestion** console:
   - Click **"Load CSV Dataset Folder"** $\to$ Ingests all 9 CSV spreadsheets directly from `CrunchWeek_StarterPack/data/csv/`.
   - Click **"Restore Official cit_public.json"** $\to$ Restores clean baseline and verifies 0 hard violations on `validator.py`.
