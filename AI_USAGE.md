# AI Usage Declaration (CIT Campus Scheduling Platform)

In compliance with Section 6 of the Crunch Week Problem Statement:

## 1. Models and APIs Called by the Product
- **Gemini API (`gemini-2.5-flash` / Google GenAI SDK)** & **Local Deterministic Fallback Parser**:
  - **Purpose**: Parsing plain-language English and Hinglish venue booking requests into structured form parameters (`attendance`, `duration_periods`, `windows`, `needs`, `room_types`, `mandatory_for_groups`), asking clarifying questions for vague requests, and formulating human-readable explanations for scheduling decisions.
  - **Prompt Locations**: Stored deterministically in `backend/services/nlp_service.py`.

## 2. AI Coding Tools Used During Development
- **Antigravity AI Pair Programmer**: Assisted in implementing mathematical constraint formulations (OR-Tools CP-SAT model constraints), SQLite database schema design, and FastAPI endpoint routes.

## 3. Strict Boundary: What the LLM is NOT Allowed to Decide
- **Zero Algorithmic Scheduling by LLM**: The LLM is **strictly prohibited** from deciding whether a schedule, booking, or timetable move is valid.
- **Backend Code Enforcement**: All constraint checks (room availability, capacity, student group non-overlap, faculty load limits, accessibility, elective baskets) and priority dispute rankings are strictly computed by deterministic Python code and Google OR-Tools CP-SAT.
- **Fail-Safe Offline Mode**: If the LLM API fails, runs out of quota, or is offline, the built-in deterministic regex/rule parser and manual booking forms continue to function seamlessly without loss of capability.
