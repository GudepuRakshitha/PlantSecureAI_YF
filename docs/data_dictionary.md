# Data dictionary

## Purpose

This document is the single human-readable reference for every CSV produced by
the project.  The machine-readable source of truth is
[`src/schema.py`](../src/schema.py); this file is the readable mirror.

All timestamps are **naive local plant time** (`Asia/Kolkata`, UTC+05:30) and are
stored as `YYYY-MM-DD HH:MM:SS`.  The timezone policy is deliberate: mixing naive
and aware timestamps silently corrupts interval arithmetic, so comparisons must
happen inside one naive frame.

---

## Populations

| Population | Contents | Use |
|---|---|---|
| `baseline` | All tables in `data/`, clean synthetic production-style data | Operational KPIs, SLA breaches, compliance reporting |
| `scenario` | Baseline rows + rows from `data/scenarios/injected_*.csv`, plus `data/scenarios/ground_truth.csv` | Detector harness only |

Baseline and scenario data must never be written to the same file.  Scenario
rows carry `case_id`; baseline rows carry `case_id = null`.

---

## Master data

### `plants` — `data/plants.csv`

| Column | Type | Notes |
|---|---|---|
| `plant_id` | text | PK |
| `plant_name` | text | |
| `location` | text | |
| `status` | enum | `ACTIVE`, `INACTIVE` |

### `safety_zones` — `data/safety_zones.csv`

| Column | Type | Notes |
|---|---|---|
| `zone_id` | text | PK |
| `plant_id` | text | FK → `plants.plant_id` |
| `zone_name` | text | |
| `risk_level` | enum | `LOW`, `MEDIUM`, `HIGH` |

### `machines` — `data/machines.csv`

| Column | Type | Notes |
|---|---|---|
| `machine_id` | text | PK |
| `plant_id` | text | FK → `plants.plant_id` |
| `zone_id` | text | FK → `safety_zones.zone_id` |
| `machine_name` | text | |
| `machine_type` | enum | `CONVEYOR`, `ROBOT`, `PRESS`, `MOTOR`, `PUMP` |
| `status` | enum | `ACTIVE`, `INACTIVE` |

### `interlocks` — `data/interlocks.csv`

| Column | Type | Notes |
|---|---|---|
| `interlock_id` | text | PK |
| `machine_id` | text | FK → `machines.machine_id` |
| `interlock_name` | text | |
| `required_state` | enum | `OPEN`, `CLOSED` |
| `current_state` | enum | `OPEN`, `CLOSED` |

### `alarm_definitions` — `data/alarm_definitions.csv`

| Column | Type | Notes |
|---|---|---|
| `alarm_definition_id` | text | PK |
| `machine_id` | text | FK → `machines.machine_id` |
| `alarm_name` | text | |
| `severity` | enum | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `acknowledgement_required` | boolean | |
| `acknowledgement_limit_minutes` | int | SLA limit per definition, > 0 |

---

## Alarm events and transactions

### `operator_shifts` — `data/operator_shifts.csv`

| Column | Type | Notes |
|---|---|---|
| `shift_id` | text | PK |
| `plant_id` | text | FK → `plants.plant_id` |
| `operator_id` | text | |
| `shift_start` | datetime | |
| `shift_end` | datetime | |

### `alarm_events` — `data/alarm_events.csv`

| Column | Type | Notes |
|---|---|---|
| `alarm_event_id` | text | PK |
| `machine_id` | text | FK → `machines.machine_id` |
| `alarm_definition_id` | text | FK → `alarm_definitions.alarm_definition_id` |
| `severity` | enum | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `event_timestamp` | datetime | |
| `machine_state` | enum | `RUNNING`, `STOPPED`, `WARNING` |
| `alarm_status` | enum | `ACTIVE`, `ACKNOWLEDGED`, `CLEARED`, `UNACKNOWLEDGED` |
| `acknowledged` | boolean | |
| `acknowledged_at` | datetime | nullable; null ⇒ unacknowledged |
| `cleared_at` | datetime | nullable; set after acknowledgement |
| `state_transition` | text | e.g. `ACTIVE>ACKNOWLEDGED>CLEARED` |
| `issue_type` | enum | `NONE` |

### `acknowledgements` — `data/acknowledgements.csv`

| Column | Type | Notes |
|---|---|---|
| `acknowledgement_id` | text | PK |
| `alarm_event_id` | text | FK → `alarm_events.alarm_event_id` |
| `operator_id` | text | |
| `shift_id` | text | FK → `operator_shifts.shift_id` |
| `ack_timestamp` | datetime | |
| `response_minutes` | int | |
| `status` | enum | `ON_TIME`, `DELAYED` |

### `incidents` — `data/incidents.csv`

| Column | Type | Notes |
|---|---|---|
| `incident_id` | text | PK |
| `alarm_event_id` | text | FK → `alarm_events.alarm_event_id` |
| `machine_id` | text | FK → `machines.machine_id` |
| `plant_id` | text | FK → `plants.plant_id` |
| `incident_type` | text | |
| `severity` | enum | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `created_at` | datetime | |
| `closed_at` | datetime | nullable |
| `status` | enum | `OPEN`, `INVESTIGATING`, `CLOSED` |

### `corrective_actions` — `data/corrective_actions.csv`

| Column | Type | Notes |
|---|---|---|
| `action_id` | text | PK |
| `incident_id` | text | FK → `incidents.incident_id` |
| `action_description` | text | |
| `assigned_to` | text | |
| `created_at` | datetime | |
| `closed_at` | datetime | nullable |
| `verified_at` | datetime | nullable |
| `status` | enum | `OPEN`, `IN_PROGRESS`, `PENDING_VERIFICATION`, `CLOSED` |
| `verification_status` | enum | `PENDING`, `VERIFIED`, `NOT_VERIFIED` |
| `effectiveness_status` | enum | `PENDING`, `EFFECTIVE`, `PARTIALLY_EFFECTIVE`, `NOT_EFFECTIVE` |

---

## Analytical outputs

### `sla_breaches` — `data/sla_breaches.csv`

Produced by `src/safety_analyzer.py`.  One row per **routine** late
acknowledgement (baseline population).

| Column | Type | Notes |
|---|---|---|
| `record_id` | text | PK — mirrors the alarm event id |
| `alarm_event_id` | text | |
| `acknowledgement_id` | text | |
| `plant_id` / `machine_id` / `alarm_definition_id` | text | |
| `severity` | enum | |
| `event_timestamp` / `acknowledged_at` | datetime | |
| `response_minutes` | real | |
| `acknowledgement_limit_minutes` | real | |
| `overdue_minutes` | real | |
| `is_routine_sla` | boolean | `true` — routine SLA breach |

### `analysis_exceptions` — `data/analysis_exceptions.csv`

Genuine anomalies detected by the scenario harness (not present in a clean
baseline run).

| Column | Type | Notes |
|---|---|---|
| `exception_type` | text | `ACK_BEFORE_ALARM`, `INTERLOCK_STATE_MISMATCH`, `INCIDENT_WITHOUT_VALID_TRIGGER`, `DUPLICATE_ALARM_REPLAY`, `CLOSED_WITHOUT_VERIFICATION` |
| `entity` | text | originating source entity |
| `record_id` | text | record under investigation |
| `severity` | enum | |
| `plant_id` / `machine_id` | text | nullable for unmapped findings |
| `case_id` | text | `EDGE-001` … `EDGE-005` or `NC-001` … `NC-003` |
| `is_routine_sla` | boolean | `false` for genuine anomalies |
| `description` | text | |

### `ground_truth` — `data/scenarios/ground_truth.csv`

Expected detector behaviour per injected case.  `expected_label` uses the
detector vocabulary; `is_anomaly` distinguishes injected cases from negative
controls.

---

## Database export

`src/build_database.py` materialises the baseline CSVs plus analytical outputs
into `data/industrial_safety.db` using `sql/schema.sql`.  The export is
relational (foreign keys enforced, integrity checked) and adds two convenience
views:

- `vw_ack_compliance` — activation-level acknowledgement compliance
- `vw_open_incidents` — open + investigating incidents
- `vw_action_pipeline` — corrective action status/verification/effectiveness mix

The SQLite export is a convenience only; the CSVs and `src/` modules remain the
authoritative artefacts.

---

## Key cardinality rules

1. One acknowledgement per alarm event (`acknowledgement_id` unique,
   `alarm_event_id` unique) — duplicates are collapsed during compliance build.
2. An alarm is acknowledged iff `acknowledged_at` is present; unacknowledged
   alarms carry `alarm_status = UNACKNOWLEDGED`.
3. `cleared_at` is always derived after acknowledgement; an acknowledged alarm
   may still be `ACKNOWLEDGED` at end of window.
4. Closed incidents must have at least one closed-and-verified corrective action;
   open/investigating incidents never carry `closed_at`.
