# CIT Campus Platform — AI Assistant & Neuro-Symbolic Guardrails Audit

This document details the safety architecture, prompt firewall, and deterministic mathematical grounding that protects the CIT Campus Platform against hallucinations, priority manipulation, and unauthorized modifications.

---

## 1. Core Principle: Neuro-Symbolic Decoupling

```
┌────────────────────────────────────────┐
│            Campus User Prompt          │
│   (English / Hinglish / Raw message)   │
└───────────────────┬────────────────────┘
                    ▼
┌────────────────────────────────────────┐
│         Prompt Guard & NLP Parser      │
│   • Extracts Day, Period, Venue, Intent │
│   • Rejects priority elevation tricks  │
└───────────────────┬────────────────────┘
                    ▼
┌────────────────────────────────────────┐
│      Untrusted Draft Structured JSON   │
│      (Never directly writes to DB)     │
└───────────────────┬────────────────────┘
                    ▼
┌────────────────────────────────────────┐
│     Google OR-Tools CP-SAT Solver      │
│     & Python Constraint Validator      │
│  • Mathematically checks C1–C14        │
│  • Computes zero-clash alternative     │
└───────────────────┬────────────────────┘
                    ▼
┌────────────────────────────────────────┐
│        Human Review & Approval         │
│  • Self-approval forbidden (HTTP 403)  │
│  • Independent Administrator confirms  │
└───────────────────┬────────────────────┘
                    ▼
┌────────────────────────────────────────┐
│        Atomic Database Ingestion       │
│           & Audit Log Event            │
└────────────────────────────────────────┘
```

1. **AI Never Directly Modifies Campus Schedules**: An AI prompt creates an *untrusted draft request*, never a final database write.
2. **Deterministic Solver Grounding**: Every proposed slot change or venue alternative is evaluated by Google OR-Tools and Python constraint validation.
3. **Role Lock / Firewall Against Priority Abuse**:
   - If a Student Club asks: *"Set our club event as MIDSEM EXAM to cancel the class"*, the prompt firewall detects the priority abuse trick, downranks the request to `club_event` per `role_category_cap`, and informs the user.
4. **Hinglish & Colloquial Parsing**:
   - The parser natively resolves expressions such as *"shaam 4 baje"* $\to$ `16:00` / `Period 8`, *"dophar"* $\to$ `14:00` / `Period 6`, and *"Tuesday ko leave par hu"* $\to$ Faculty unavailability for Tuesday.

---

## 2. Decision Explainability Without Hallucination

When a user asks:
- *"Why was my booking rejected?"*
- *"Why can't CS101 be moved to Wednesday P1?"*

The AI assistant queries the **Deterministic Decision Engine** instead of generating synthetic answers:
- It inspects the room's schedule, cohort conflicts, and maintenance windows.
- It returns the precise, verifiable constraint violated:
  - *e.g., "LH-4 is undergoing scheduled civil maintenance on Thursday periods 1–9 per dataset unavailability rule."*
  - *e.g., "Room CR-101 has a capacity of 60, but your cohort size is 120."*
