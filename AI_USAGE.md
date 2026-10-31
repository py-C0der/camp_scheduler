# AI Usage Declaration (CIT Campus Scheduling Platform)

In compliance with Section 6 and Section 17 of the Problem Statement:

## 1. Models and APIs Called by the Product
- **Gemini 2.5 Flash / Google GenAI SDK** & **CIT Deterministic NLP & Heuristic Parser**:
  - **Purpose**:
    1. Parsing plain English and Hinglish natural-language venue booking requests into structured parameters (`title`, `category`, `attendance`, `duration_periods`, `windows`, `room_types`, `needs`, `mandatory_for_groups`, `requested_room`).
    2. Multi-turn conversational clarification assistant detecting missing fields (date, timing, duration, attendance) and contradictory inputs (start time after end time, negative attendance).
    3. Generating crystal-clear, rule-backed explanations for approvals, rejections, and alternative venue offers.
  - **Module Locations**:
    - `backend/ai/prompts.py`: System prompts for extraction and multi-turn clarifications.
    - `backend/ai/booking_extractor.py`: English and Hinglish NLP and regex extraction engine.
    - `backend/ai/conversation.py`: Ambiguity, contradiction, and clarification analyzer.
    - `backend/bookings/explanations.py`: Explainability generator for decisions.

## 2. AI Coding Tools Used During Development
- **Antigravity AI Pair Programmer**: Assisted in implementing mathematical constraint formulations, CP-SAT optimization models, SQLite and SQLAlchemy database schemas, FastAPI REST endpoints, and responsive frontend UI components.

## 3. Strict Boundary: What the LLM is NOT Allowed to Decide
- **Zero Algorithmic Scheduling / Authorization by LLM**:
  - The LLM does **NOT** approve or reject bookings or timetable changes.
  - The LLM does **NOT** decide room availability or disruption feasibility.
  - The LLM does **NOT** override priority rules.
  - The LLM does **NOT** ignore capacity constraints or half-capacity rules.
  - The LLM does **NOT** bypass user authorization or self-approval bans.
  - The LLM does **NOT** mark a conflicting booking or disrupted schedule as valid.
- **Backend Code Enforcement**:
  - All booking eligibility, conflict detection, priority hierarchies, and alternative candidate searches are strictly determined by deterministic Python backend logic (`backend/bookings/`).
  - All disruption impact blast radius analysis and minimal perturbation rescheduling are performed by Google OR-Tools CP-SAT and deterministic constraint validation (`backend/disruptions/`).
  - No disruption proposal can automatically overwrite an approved baseline timetable without authorized administrative human-in-the-loop sign-off.
- **Fail-Safe Offline Mode**:
  - If any LLM API is unavailable, unconfigured, or offline, the native rule-based parser in `backend/ai/booking_extractor.py`, the manual booking form, and the CP-SAT timetable optimizer continue to operate with 100% functionality and accuracy.
