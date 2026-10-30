# Architecture

## Overview

The project is a layered, single-source-of-truth codebase:

```
dashboard/   presentation only (Streamlit + Plotly)
src/         configuration, schema, data access, metrics, detection, generators,
            validators, analyzer, database export
data/        generated CSVs, scenario files, analysis outputs, SQLite export
sql/         SQLite export DDL
docs/        human documentation
tests/       automated contract and behaviour tests
```

No presentation-layer business logic lives in `dashboard/`.  Every KPI, filter
predicate, chart aggregation and export is imported from `src.metrics` / `src.data_access`.

## Layers

### 1. `src/config.py`

Single place for paths, seed, dataset shape, enumerations, SLA limits and
detection thresholds.

### 2. `src/schema.py`

Single source of truth for table names, columns, keys, enums, datetime and
boolean columns, foreign keys and file names.

### 3. `src/data_access.py`

- `fingerprint(mode)` — cache invalidation key over source files.
- `read_table(spec, path)` — schema-driven CSV reader with type coercion.
- `load_population(mode)` — baseline or scenario frame set.
- `prepare_population(mode)` — enriched frames + metrics-ready aggregates.

### 4. `src/metrics.py`

The **only** analytical layer:

- `build_compliance` — one row per alarm activation with ack outcome.
- `ack_compliance_metrics` — activation-denominated rates (ack rate, on-time,
  late, unacknowledged; median/p95 response).
- `mtta_statistics` — mean/median/p95 of acknowledgement latency.
- `sla_breaches` — routine SLA breaches (`response_minutes > limit`).
- `unacknowledged_alarms` — per-activation unacknowledged records.
- `priority_compliance` — compliance by severity.
- alarm counting / distribution / trend helpers.
- `detect_chattering`, `detect_floods`.
- `incident_statistics`, `corrective_action_statistics`, `exception_kpis`.
- `Filters` + `apply_filters` — one predicate, reused by dashboard and reports.

### 5. `src/detection.py`

Anomaly detection rules:

- `ACK_BEFORE_ALARM`
- `INTERLOCK_STATE_MISMATCH`
- `INCIDENT_WITHOUT_VALID_TRIGGER`
- `DUPLICATE_ALARM_REPLAY`
- `CLOSED_WITHOUT_VERIFICATION`

plus `evaluate_detection` against `data/scenarios/ground_truth.csv`.

### 6. `dashboard/`

- `theme.py` — palette, CSS, Plotly layout (`style_figure`).
- `components.py` — KPI cards, sections, badges, notices, charts, search, tables,
  downloads, empty states.
- `app.py` — sidebar navigation, header, global filters, page renderers, state
  assembly, friendly error handling.

### 7. `src/safety_analyzer.py`, `src/build_database.py`, `src/validate_*.py`

Reporting, SQLite export and quality gates.

## Data flow

```
generators -> CSVs -> validators -> metrics -> analyzer -> dashboard
                                   \-> SQLite export
```

Every analytical number shown in the dashboard is recomputed from the shared
population prepared by `data_access.prepare_population`; nothing is cached as a
hard-coded KPI.

## Caching

`dashboard/app.py` uses `@st.cache_data(show_spinner=False, max_entries=4)` keyed
by `(mode, fingerprint)`.  The fingerprint covers source file mtime/size, so
regenerating data invalidates the cache automatically; the header's **Refresh
data** button clears the Streamlit cache for an immediate rerun.

## Determinism

- Generator seed: `20261022` (`src.config.SEED`).
- Independent lifecycle seeds (`SEED + 101 … + 104`) keep original streams
  stable while allowing new lifecycle attributes.
- All generators use `random.Random` / `numpy.default_rng`; no wall-clock or
  dict-order dependence.

## Safety boundaries

- No ISA-18.2 / IEC 61511 compliance claim is made anywhere in the UI, docs or
  code comments.
- Detection thresholds (`chatter_n=3`, `window=60m`; `flood_alarm_count=10`,
  `window=10m`) are synthetic settings documented in `src/config.py`.
