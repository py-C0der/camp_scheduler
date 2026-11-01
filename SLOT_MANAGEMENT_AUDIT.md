# CIT Campus Platform — Slot Management & Time Model Audit

This document describes the temporal and spatial scheduling model used by the CIT Campus Platform.

---

## 1. Campus Time Model Structure

- **Academic Days**: Monday (`MON`) to Friday (`FRI`).
- **Teaching Periods (P1 – P9)**:
  - `P1`: 08:00 – 09:00
  - `P2`: 09:00 – 10:00 (Standard Morning Lab Block Start)
  - `P3`: 10:00 – 11:00
  - `P4`: 11:00 – 12:00
  - `P5`: 12:00 – 13:00
  - **Lunch Break**: 13:00 – 14:00 (Mandatory Institutional Recess)
  - `P6`: 14:00 – 15:00 (Standard Afternoon Lab Block Start)
  - `P7`: 15:00 – 16:00
  - `P8`: 16:00 – 17:00
  - `P9`: 17:00 – 18:00
- **Campus Event Periods (P10 – P13)**:
  - `P10`: 18:00 – 19:00
  - `P11`: 19:00 – 20:00
  - `P12`: 20:00 – 21:00
  - `P13`: 21:00 – 22:00
  *(Teaching is strictly restricted to P1–P9; campus events, cultural talks, and club activities utilize P10–P13).*

---

## 2. Lab Block Alignment (3 Continuous Hours)

- In the CIT curriculum, lab sessions (`kind: "lab"`) require 3 continuous teaching hours.
- **Rule Enforcement**:
  - Labs can start **only at Period 2 (09:00)** or **Period 6 (14:00)**.
  - A morning lab starting at P2 occupies `P2, P3, P4` (finishing at 12:00).
  - An afternoon lab starting at P6 occupies `P6, P7, P8` (finishing at 17:00).
  - This guarantees that no lab collides with or spans across the P5/P6 lunch break boundary.

---

## 3. Elective Basket Alignment (`OEB-1`)

- Year 3 engineering students choose between 3 Open Elective courses:
  - `OE301`: Applied Optimization
  - `OE302`: Environmental Management
  - `OE303`: Financial Engineering
- Because Year 3 groups (`Y3-CSE`, `Y3-ECE`, `Y3-EE`, `Y3-ME`, `Y3-CE`) have members distributed across all three electives, these sessions share the basket identifier `basket_slot: "OEB-1"`.
- **Enforcement Rules**:
  1. All sessions with basket slot `OEB-1` are constrained to run in parallel at the **exact same day and start period**.
  2. Each session must occupy an **independent non-clashing venue** with adequate capacity.
  3. While basket sessions do not clash with each other for groups, they prevent any other regular session from being scheduled for Year 3 groups in that time slot.

---

## 4. Mid-Semester Examination Slots (Week 8)

- **Exam Calendar**: Monday to Saturday (`MON`–`SAT`).
- **Exam Sessions**:
  - `AM Session`: 09:30 – 11:30
  - `PM Session`: 14:00 – 16:00
- **Half-Capacity Seating Rule**:
  - During examinations, rooms seat only $\lfloor capacity / 2 \rfloor$ students to prevent academic malpractice.
  - Large cohorts (e.g. `MA101` with 180 students) are automatically partitioned across multiple rooms (e.g. `AUD`, `LH-1`, `LH-2`) with zero clashes between concurrent student groups.
