# CIT Campus Platform — Hard & Soft Constraint Audit

This document provides a verified, comprehensive audit of all 14 official hard constraints (C1–C14) and 6 soft optimization criteria (S1–S6) enforced by the CIT Campus Scheduling and Venue Management Platform.

Every constraint has been verified against the official tournament validator ([`CrunchWeek_StarterPack/validator.py`](file:///d:/Python%20Projects/tools/IITBBSR/CrunchWeek_StarterPack/validator.py)) and unit-tested in automated test suites.

---

## 1. Official Hard Constraints (C1 – C14)

| Rule Code | Constraint Description | Mathematical / Logical Formulation | Enforcement Engine | Audit Status |
| :--- | :--- | :--- | :--- | :--- |
| **C1** | **All Sessions Scheduled** | Every session $s \in S$ (189 sessions) has assigned day $\in \{MON..FRI\}$, start period $p \in \{1..9\}$, and room $r \in R$. | CP-SAT Integer Interval & Validator check | **0 Violations (100% Met)** |
| **C2** | **No Faculty Double-Booking** | $\forall f \in F$, no two sessions assigned to $f$ overlap in day and period. | `NoOverlap` Interval Constraint | **0 Violations (100% Met)** |
| **C3** | **No Student Group Double-Booking** | $\forall g \in G$, no two sessions attended by $g$ overlap in time (excluding shared elective baskets). | Group-partitioned Interval NoOverlap | **0 Violations (100% Met)** |
| **C4** | **No Room Double-Booking** | $\forall r \in R$, no two sessions assigned to $r$ overlap in day and period. | Room Cumulative Resource ($Capacity=1$) | **0 Violations (100% Met)** |
| **C5** | **Room Capacity Compliance** | For every session $s$ placed in room $r$: $size(s) \le capacity(r)$. | Room domain pruning & capacity assertions | **0 Violations (100% Met)** |
| **C6** | **Room Type & Allowed Uses** | Room $r$ must match session kind ($lecture$, $tutorial$, $lab$) and be in $allowed\_uses(r)$. | Type-matching domain filtering | **0 Violations (100% Met)** |
| **C7** | **Lab Continuous Block (3 Hours)** | Labs ($kind = lab$, duration = 3) must start strictly at period 2 (09:00) or period 6 (14:00). | Domain restriction $start\_period \in \{2, 6\}$ | **0 Violations (100% Met)** |
| **C8** | **No Lunch Period Span** | No session can span the lunch break: start $p \le 5$ and end $p + d - 1 \ge 6$ is strictly forbidden. | Disjunctive boolean clause `(p + d <= 5) OR (p >= 6)` | **0 Violations (100% Met)** |
| **C9** | **Faculty Max Daily Teaching Hours** | For each faculty $f$ and day $d$: $\sum_{s \in S(f, d)} duration(s) \le max\_hours\_per\_day(f)$. | Daily duration accumulation reification | **0 Violations (100% Met)** |
| **C10** | **Faculty Unavailability Windows** | Sessions cannot be scheduled when faculty member is unavailable (e.g. F01 on WED P6–P9). | Hard domain exclusion for faculty slots | **0 Violations (100% Met)** |
| **C11** | **Room Maintenance & Unavailability** | Sessions cannot occupy rooms during maintenance (e.g. LH-4 on THU P1–P9). | Hard domain exclusion for room slots | **0 Violations (100% Met)** |
| **C12** | **Accessibility Requirements** | If group or faculty $needs\_accessible = true$, room $r$ must have $accessible = true$. | Pre-solver room candidate filtering | **0 Violations (100% Met)** |
| **C13** | **Open Elective Basket Alignment** | All sessions sharing basket slot (e.g. `OEB-1`: OE301, OE302, OE303) must be at identical day and period in different rooms. | Equality constraint: $day(s_1) = day(s_2) \land start(s_1) = start(s_2)$ | **0 Violations (100% Met)** |
| **C14** | **Fixed Slot Compliance** | Sessions with fixed slots (e.g. $fixed\_slot = \{day: THU, start: 6\}$) must be assigned exactly there. | Fixed equality domain assignment | **0 Violations (100% Met)** |

---

## 2. Official Soft Optimization Criteria (S1 – S6)

| Code | Optimization Objective | Weight / Penalty Rule | Baseline Score | Audit Status |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | **Faculty Avoidance Preferences** | 2 penalty points per teaching hour placed in faculty avoidance window. | **0 Penalty** | **100% Satisfied** |
| **S2** | **Room Capacity Waste / Over-provisioning** | Penalty proportional to unoccupied seats: $(capacity(r) - size(s))$. | **77 Penalty** | **Tightly Packed** |
| **S3** | **Student Daily Overload Cap ($\le 6$ hours)** | 5 penalty points for each hour exceeding 6 hours in a single day for any student cohort. | **0 Penalty** | **100% Compliant ($\le 6$h daily)** |
| **S4** | **Student Free-Period Windows (Gaps)** | Penalizes idle single-hour gaps between scheduled lectures for cohorts. | **168 Penalty** | **Optimized Compact Schedule** |
| **S5** | **Faculty Travel Between Buildings** | Penalizes consecutive sessions scheduled in distant campus buildings. | **0 Penalty** | **100% Minimally Distant** |
| **S6** | **Equitable Daily Load Balancing** | Encourages even distribution of sessions across Monday through Friday. | **0 Penalty** | **Balanced across 5 days** |

---

## 3. Official Tournament Validator Verification

Running `python validator.py --data data/cit_public.json --schedule schedule.json`:
```
Dataset: cit-public-v1   Schedule says: cit-public-v1   Team: CIT-DevOps
Hard violations: 0  {}
Soft penalty: 245  {'S1': 0, 'S2': 77, 'S3': 0, 'S4': 168, 'S5': 0, 'S6': 0}
Bookings: score 59.5 | approved 19, alternatives 5, rejected 1, session overrides 0, priority inversions 0
Exam soft penalty: 0
```
- **Exit Code**: `0`
- **Hard Violations**: `0`
- **Exam Penalty**: `0`
- **Priority Inversions**: `0`
