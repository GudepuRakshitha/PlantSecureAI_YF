# Project review — yottaflex industrial safety monitoring

Three independent reviews, three lenses:

| Reviewer | Lens | Focus |
|---|---|---|
| A | Data pipeline & quality | generators, CSVs, keys, determinism, validators |
| B | Safety-domain analytics | metric definitions, join logic, ISA-18.2 / IEC 61511 validity |
| C | Dashboard & engineering | Streamlit app, performance, UX, repo scaffolding |

Findings below were verified by execution, not inspection alone. Numbers in **Measured** columns were reproduced on the committed data.

---

## Remediation status — 2026-10-30

The findings above have since been addressed in the current codebase:

| Item | Status |
|---|---|
| C1 ack compliance activation denominator | **Fixed** — rates are now activation-denominated |
| C2 exception plant/machine filters | **Fixed** — predicate applied via shared `Filters` |
| C3 exception severity source | **Fixed** — severity derived from source records |
| C4 routine vs genuine exceptions | **Fixed** — `sla_breaches.csv` + `analysis_exceptions.csv` split |
| C5 fail-loud validators | **Fixed** — validators exit 1 on failure |
| C6 alarm lifecycle fields | **Fixed** — `acknowledged`, `cleared_at`, incident/action lifecycle |
| C7 reproducibility pack | **Fixed** — requirements, README, docs, tests, CI, Makefile, DB export |

The sections below are kept for traceability of the original audit.

---

## 0. Verified baseline

| Item | Value |
|---|---|
| Alarm events | 50,000 (1 Oct 2026 → 30 Oct 2026, tz-naive) |
| Acknowledgements | 45,031 (90.06%) → **4,969 alarms never acknowledged** |
| On-time ack (per the app) | 36,101 / 45,031 = **80.17%** |
| On-time ack (true, per activation) | 36,101 / 50,000 = **72.20%** |
| Exceptions | 8,935 = 8,930 `LATE_ACKNOWLEDGEMENT` + 5 injected anomalies |
| Incident / action state | 169/169 `OPEN`; 169/169 actions `CLOSED`+`VERIFIED` |
| FK orphans / PK duplicates / nulls | 0 / 0 / 0 across all 10 baseline tables |
| `dashboard/app.py` | 1,085 lines, 0-arg cached loader, 8 figures + 6 tables per rerun |

The data model itself is clean. The problems are in **semantics, exposure of results, and engineering scaffolding** — not in referential integrity.

---

## 1. Critical issues (fix first)

### C1. Ack compliance is survivorship-biased — KPI inflated by ~8 pp
`src/safety_analyzer.py:88-121`, `dashboard/app.py:478-493`

Latency is computed only over rows present in `acknowledgements.csv`. The 4,969 unacknowledged alarms (the worst ISA-18.2 failure) are counted nowhere: not in the KPI, not in the exception file.

- Reported on-time: **80.17%**
- True on-time over activations: **72.20%**
- True non-compliance: **27.80%**, not 19.83%

**Fix:** left-join events → acks; emit `UNACKNOWLEDGED` exceptions by priority; denominate every rate by alarm activations.

### C2. Plant/machine filters silently do nothing to exceptions
`dashboard/app.py:296` guards on `"entity_id" in exceptions.columns`; the real column is `record_id` (`data/analysis_exceptions.csv:1`). Choosing PLT-003 still shows all 8,935 rows instead of 2,018.

**Fix:** export `plant_id`/`machine_id`/`case_id` from the analyzer; join on them; show an "unmapped rows" count instead of silently skipping.

### C3. Exception severity ≠ alarm severity, so the severity filter lies
`dashboard/app.py:457-467` filters exceptions with the alarm severity list. Exception rows are only MEDIUM/HIGH/CRITICAL, so `LOW` shows **0** rows while **2,471 LOW late-acks exist**; `HIGH` shows 3 unrelated rows. Acks are not severity-filtered at all, so "On-time Acknowledgements" prints 80.17% for every severity.

**Fix:** derive severity from the source alarm/record, use one vocabulary, apply the predicate to all five frames.

### C4. 99.94% of "safety exceptions" are designed SLA noise
`safety_analyzer.py:108-121` → `analysis_exceptions.csv`

8,930 of 8,935 rows are routine `LATE_ACKNOWLEDGEMENT`. The 5 real anomalies are 0.011% of the signal, which is why the dashboard already needs a workaround tab to find them.

**Fix:** split routine SLA breaches (`sla_breaches.csv`) from anomalies (`exceptions.csv`); add `is_routine_sla` and surface the non-late count prominently.

### C5. Validators can never fail
`src/validate_data.py:29-34`, `src/validate_edge_cases.py:8-14,73-84`

Both exit 0 on the current dataset. `validate_edge_cases.py` re-derives the injected conditions from the injection files and then prints "All injected edge cases were detected successfully!" — it tests the *injector*, never the *detector*. `ground_truth.csv` is only checked for `len == 5`.

**Fix:** assert `ground_truth.record_id ⊆ exceptions.record_id` **and** that no baseline id appears; `sys.exit(1)` on violation; wire into CI.

### C6. Data model has no lifecycle → MTTR, standing-alarm and trend analysis are impossible
`event_generator.py:43-44`, `data/incidents.csv`, `transaction_generator.py:168-175`

- `alarm_status = ACTIVE` for 50,000/50,000; no `cleared_at`, no acknowledged flag.
- All 169 incidents `OPEN`, all 169 actions `CLOSED`+`VERIFIED`, every action duration exactly 110.0 min (std 0).
- "Open incident with verified closed action" is a semantic contradiction.

**Fix:** add `acknowledged`, `cleared_at`, `state_transition`, incident `closed_at`, CAPA `verified_at/effectiveness`; vary generator states.

### C7. Fresh clone is not reproducible
No `requirements.txt`/`pyproject.toml`, README is one heading line, `tests/` and `docs/` empty, no CI, no LICENSE. Verified interpreter: Python 3.12.10, pandas 3.1.0, streamlit 1.66.1, plotly 7.1.0, pyarrow 26.0.0.

**Fix:** pin deps, write quickstart + regeneration order, add pytest smoke test and CI.

---

## 2. High-severity issues

| # | Issue | Where | Evidence |
|---|---|---|---|
| H1 | Injected cases are leaked by enums absent from baseline | `inject_edge_cases.py:62,174` | baseline ack `status` ∈ {ON_TIME, DELAYED}; injected uses `INVALID_EARLY_ACK`. A detector scores 100% by string-matching |
| H2 | Injected rows collide with baseline primary keys | `inject_edge_cases.py:78-88,146-158` | injected interlock reuses `INT-001-01`; 3/3 injected events reuse existing `alarm_event_id` |
| H3 | Acks are not clamped to the owning shift | `transaction_generator.py:87-96` | 417 of 45,031 acks fall outside their shift; 4 after the last event |
| H4 | Cache never invalidates after regeneration | `dashboard/app.py:161-186` | zero-arg `@st.cache_data` → stale KPIs until process restart |
| H5 | Incidents are sampled *from* alarms → trigger check is tautological | `transaction_generator.py:114-128`, `safety_analyzer.py:143-169` | 169/169 `created_at == event_timestamp`; incident severity copies alarm severity 1:1 |
| H6 | No time dimension anywhere in the UI | `app.py:184` | 30 days of timestamps never parsed; no trend, no date filter |
| H7 | "Repeated Alarm Definitions" is base-rate noise | `app.py:525-532` | all 200 definitions flagged (208–292 events each); χ² p≈0.35 |
| H8 | Analyzer and dashboard disagree on population | `safety_analyzer.py:25-35` vs `app.py:164-173` | analyzer reads baseline + injected (50,003 events); dashboard reads baseline only (50,000) |
| H9 | Per-interaction cost 300–380 ms, mostly uncacheable joins | `app.py:220-262,428-534` | merges alone 184–253 ms; 50k×10 frame serialized in full on every rerun |
| H10 | No schema validation on load → raw traceback in browser | `app.py:189-194` | only `FileNotFoundError` caught; unguarded column access at `:371,404,479,497,889,950` |

---

## 3. Metric definitions audit

| Metric | Computed now | Problem | Recommended |
|---|---|---|---|
| Alarm count | `len(events)` | includes replays; no dedup | distinct activations per 10 min |
| Ack rate | never shown | 4,969 unacked invisible | acked / activated, by priority |
| Late ack | `response_minutes > limit` | acks-only denominator | recompute from timestamps + never-acked |
| On-time % | hard-coded `<= 5` | ignores per-definition limit | join `acknowledgement_limit_minutes` |
| MTTA | `mean(response_minutes)` | survivor subset, integer minutes | median + p95 over all activations |
| Repeated alarms | `count > 1` | 200/200 flagged, p≈0.35 | N-in-T chattering + control limit |
| Most affected machine | raw count | generator artifact (20 machines get 4 definitions, 40 get 3) | exposure-normalized rate + CI |
| Priority mix | absent | 50.59% HIGH+CRITICAL vs ISA-18.2 target ≲5% critical | Pareto + rationalization report |
| Alarm flood | absent | PLT-001 peaks at 13 alarms/10 min | rolling >10/10 min/operator alert |

## 4. Scenario harness

| Case | Expected | Detected | Note |
|---|---|---|---|
| EDGE-001 | `ACK_BEFORE_ALARM` | `ACK_BEFORE_ALARM` | ok |
| EDGE-002 | `IMPOSSIBLE_INTERLOCK_STATE` | `INTERLOCK_STATE_MISMATCH` | label mismatch |
| EDGE-003 | `INCIDENT_WITHOUT_TRIGGER` | `INCIDENT_WITHOUT_VALID_TRIGGER` | label mismatch |
| EDGE-004 | `ALARM_FLOOD_DUPLICATE_REPLAY` | `DUPLICATE_ALARM_REPLAY` | replay ≠ flood |
| EDGE-005 | `CLOSED_WITHOUT_VERIFICATION` | `CLOSED_WITHOUT_VERIFICATION` | ok |

Recall 5/5 by record join. **Precision is not measurable** — zero negative controls, 3/5 labels not joinable programmatically.

---

## 5. Prioritized backlog

### P0 — correctness (days)
1. Activation-denominated compliance funnel: ack rate → on-time → late → never-acked, by priority.
2. Fix filter semantics end-to-end: one predicate, severity propagation, exception joins (`app.py:296,432-467`).
3. Split routine SLA breaches from anomalies; surface the real 5.
4. Make validators fail loudly + ground-truth equality gate; add to CI.

### P1 — capability (1–2 weeks)
5. Lifecycle fields (`acknowledged`, `cleared_at`, incident `closed_at`, CAPA effectiveness) → enables MTTR/standing alarms.
6. Chattering (N-in-T) and flood (>10/10 min/operator) detectors with SPC/Poisson limits, replacing the current noisy charts.
7. Date-range filter + trend charts; parse timestamps once with an explicit timezone policy.
8. Single metric layer (`metrics.json` / `src/metrics.py`) consumed by analyzer **and** dashboard; kill the duplicated KPIs and the four hard-coded 5-minute thresholds.
9. Scenario harness with negative controls, label normalization map, per-case TP/FP/FN.

### P2 — engineering & UX (parallel)
10. `requirements.txt` (pinned), `.python-version`, README quickstart + regeneration order, `docs/data_dictionary.md`, MIT LICENSE.
11. Pytest setup: schema/FK/`ack ≥ event` invariants, filter unit tests, `AppTest` smoke test.
12. GitHub Actions: ruff + pytest on PR.
13. Cache prepared joins by file `(mtime, size)`; write Parquet (pyarrow already installed, ~10× smaller); `usecols` + dtypes at load.
14. Extract `src/config.py` (colors, thresholds, enums, paths) and `src/dashboard_data.py`; thin the 1,085-line `app.py`.
15. UX: semantic severity palette (LOW→CRITICAL), machine/plant names instead of ids, split exception chart, consistent empty states, `width="stretch"` instead of deprecated `use_container_width`, export buttons.

## 6. Top five by value / effort

1. **Activation-denominated compliance funnel** — fixes the number leadership will actually read. ~1 day.
2. **Filter correctness + joinable exceptions** — prevents wrong plant-level decisions. ~4 h.
3. **Fail-loud validators + ground-truth gate + CI** — makes every later change safe. ~3 h.
4. **Reproducibility pack** (requirements, README, pytest smoke, CI) — unblocks anyone else running it. ~2 h.
5. **Lifecycle + chattering/flood analytics** — turns the dashboard from a count viewer into an alarm-management tool. ~3 days.

## 7. What is already good

- Referential integrity is genuinely clean: 0 orphans on all 13 FK edges, 0 duplicate PKs, 0 nulls.
- Generators are deterministic and reproduce committed files byte-for-byte in the pinned env.
- `dashboard/app.py:18` anchors the data path to `__file__` (not cwd), and merges use `validate="many_to_one"`.
- `AppTest` runs the app with **zero** exceptions; no secrets, no `eval`/`exec`, `unsafe_allow_html` only with static strings.
- `.gitignore` correctly excludes `venv/`, caches and secrets.
