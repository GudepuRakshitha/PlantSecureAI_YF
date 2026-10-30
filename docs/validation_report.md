# Validation report

## Status

| Gate | Result | Detail |
|---|---|---|
| Baseline data validation | **PASS** | 94/94 checks passed |
| Edge-case / detector validation | **PASS** | 40/40 checks passed |
| Detector score (scenario) | **PASS** | 5 TP / 0 FP / 0 FN, precision 1.00, recall 1.00 |
| Data pipeline determinism | **PASS** | committed CSVs reproduced byte-for-byte (documented checks) |
| Build database export | **PASS** | SQLite export, foreign keys OK, integrity OK |

## Baseline dataset

- Alarm activations: **50,000** (2026-10-01 → 2026-10-30, 30 days).
- Distinct machines: **60**, alarm definitions: **200**.
- Severity mix: LOW 13,570 · MEDIUM 11,135 · HIGH 13,929 · CRITICAL 11,366.

## Acknowledgement compliance (baseline)

| Metric | Value |
|---|---|
| Acknowledgment rate | **90.06%** (45,031 / 50,000) |
| Unacknowledged alarms | **4,969** (9.94%) |
| On-time acknowledgements | **36,101** |
| Late acknowledgements | **8,930** |
| **On-time compliance (activations)** | **72.20%** (36,101 / 50,000) |
| Late (of activations) | 17.86% |
| Median response time | **4.0 min** |
| P95 response time | **13.0 min** |

The unacknowledged tail was previously dropped from the denominator; it is now
part of every rate (activation-denominated).  Acknowledged-only on-time would
have been 80.17% — an artefact, not a compliance result.

## Incident and corrective-action state

- Incidents: 169 total · 58 open · 48 investigating · 63 closed (37.28%).
- Corrective actions: 169 total · 63 closed · 63 verified · 106 pending
  verification.
- Mean resolution time: 61.08 h (median 54.0 h).

## Scenario / detector harness

| Case | Expected | Detected |
|---|---|---|
| EDGE-001 | `ACK_BEFORE_ALARM` | `ACK_BEFORE_ALARM` ✓ |
| EDGE-002 | `INTERLOCK_STATE_MISMATCH` | ✓ |
| EDGE-003 | `INCIDENT_WITHOUT_VALID_TRIGGER` | ✓ |
| EDGE-004 | `DUPLICATE_ALARM_REPLAY` | ✓ |
| EDGE-005 | `CLOSED_WITHOUT_VERIFICATION` | ✓ |
| Negative controls (NC-001…003) | not anomalies | not flagged ✓ |

- True positives: **5** · False positives: **0** · False negatives: **0**
- Precision: **1.00** · Recall: **1.00**
- Negative controls hit: **0**

## Outputs

- `data/sla_breaches.csv` — 8,930 routine SLA breaches.
- `data/analysis_exceptions.csv` — genuine anomalies (empty in baseline).
- `data/analysis_summary.json` — machine-readable metrics + detection report.
- `data/industrial_safety.db` — SQLite export (foreign keys + integrity checked).

## Re-run

```bash
python src/validate_data.py
python src/validate_edge_cases.py
python src/safety_analyzer.py
python src/build_database.py
```
