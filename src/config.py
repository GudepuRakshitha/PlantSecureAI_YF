"""Central configuration for the Industrial Safety Monitoring System.

Every hard-coded threshold, enum, path and colour lives here so that the
generators, validators, analyzer and dashboard cannot drift apart.

Timezone policy
---------------
All timestamps are *naive local plant time* (Asia/Kolkata, UTC+05:30) as
recorded by the plant historians.  They are deliberately stored without an
offset: the synthetic source systems do not provide one, and mixing naive and
aware timestamps is a common source of silent bugs.  Any comparison with a
wall clock must therefore be done in the same naive local frame.  This is
documented in docs/data_dictionary.md and docs/architecture.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCENARIO_DIR = DATA_DIR / "scenarios"
CACHE_DIR = DATA_DIR / "cache"
EXPORT_DIR = DATA_DIR / "exports"
SQL_DIR = PROJECT_ROOT / "sql"
DB_PATH = DATA_DIR / "industrial_safety.db"

# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

SEED = 20261022
# Independent streams keep the original event/ack stream byte-stable while
# allowing the new lifecycle attributes to be added without reshuffling data.
LIFECYCLE_SEED = SEED + 101
INCIDENT_LIFECYCLE_SEED = SEED + 102
ACTION_LIFECYCLE_SEED = SEED + 103
SCENARIO_SEED = SEED + 104

# ---------------------------------------------------------------------------
# Dataset shape
# ---------------------------------------------------------------------------

N_PLANTS = 4
N_MACHINES = 60
N_ZONES_PER_PLANT = 3
N_INTERLOCKS_PER_MACHINE = 2
N_ALARM_DEFINITIONS = 200
TOTAL_EVENTS = 50_000

DATASET_START = "2026-10-01 00:00:00"
# Events cover 30 days; acknowledgements can run a few minutes past midnight
# on 31 October, so the shift roster and lifecycle window include that day.
DATASET_END = "2026-10-31 23:59:59"
EVENT_DAYS = 30

ACK_PROBABILITY = 0.90
ON_TIME_PROBABILITY = 0.80
ON_TIME_MAX_MINUTES = 5
LATE_MIN_MINUTES = 6
LATE_MAX_MINUTES = 15
ACK_LIMIT_MINUTES = 5

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
SEVERITY_RANK = {name: rank for rank, name in enumerate(SEVERITIES)}

ALARM_STATUSES = ("ACTIVE", "ACKNOWLEDGED", "CLEARED", "UNACKNOWLEDGED")
MACHINE_STATES = ("RUNNING", "STOPPED", "WARNING")
MACHINE_TYPES = ("CONVEYOR", "ROBOT", "PRESS", "MOTOR", "PUMP")
ZONE_RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")
INTERLOCK_STATES = ("OPEN", "CLOSED")
ACK_STATUSES = ("ON_TIME", "DELAYED")
INCIDENT_STATUSES = ("OPEN", "INVESTIGATING", "CLOSED")
INCIDENT_TYPES = ("UNSAFE_MACHINE_RUNNING",)
ACTION_STATUSES = ("OPEN", "IN_PROGRESS", "PENDING_VERIFICATION", "CLOSED")
VERIFICATION_STATUSES = ("PENDING", "VERIFIED", "NOT_VERIFIED")
EFFECTIVENESS_STATUSES = (
    "PENDING",
    "EFFECTIVE",
    "PARTIALLY_EFFECTIVE",
    "NOT_EFFECTIVE",
)
ISSUE_TYPES = ("NONE",)
ENTITY_TYPES = (
    "AlarmEvent",
    "Acknowledgement",
    "Interlock",
    "Incident",
    "CorrectiveAction",
)

# ---------------------------------------------------------------------------
# Analytical thresholds
#
# These are *synthetic detection settings* chosen for this dataset.  They are
# inspired by alarm-management practice (for example the common working rule
# that more than ten alarms in ten minutes constitutes a flood) but this
# project makes no claim of ISA-18.2 or IEC 61511 compliance.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DetectionThresholds:
    """Configurable chattering and flood detection settings."""

    chatter_n: int = 3
    chatter_window_minutes: int = 60
    flood_alarm_count: int = 10
    flood_window_minutes: int = 10


THRESHOLDS = DetectionThresholds()

# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

SEVERITY_COLORS = {
    "LOW": "#2f8f83",
    "MEDIUM": "#c99400",
    "HIGH": "#e8590c",
    "CRITICAL": "#b02a37",
}
ALARM_STATUS_COLORS = {
    "ON_TIME": "#2f8f83",
    "LATE": "#e8590c",
    "UNACKNOWLEDGED": "#b02a37",
}
INCIDENT_STATUS_COLORS = {
    "OPEN": "#b02a37",
    "INVESTIGATING": "#c99400",
    "CLOSED": "#2f8f83",
}
ACTION_STATUS_COLORS = {
    "OPEN": "#b02a37",
    "IN_PROGRESS": "#c99400",
    "PENDING_VERIFICATION": "#7a5ea8",
    "CLOSED": "#2f8f83",
}
PLANT_COLORS = ["#087b9b", "#12a6a6", "#f0b429", "#7a5ea8"]

DATASET_LABELS = {
    "baseline": "Baseline (production-style)",
    "scenario": "Scenario test (baseline + injected cases)",
}
DATASET_DESCRIPTIONS = {
    "baseline": (
        "Clean synthetic production-style data. Injected edge cases and "
        "negative controls are excluded from every KPI on this view."
    ),
    "scenario": (
        "Baseline data plus five injected anomalies and three negative "
        "control records. Use this view only to inspect detector behaviour; "
        "its KPIs are not production metrics."
    ),
}

# ---------------------------------------------------------------------------
# Reporting / exports
# ---------------------------------------------------------------------------

EXPECTED_CASE_IDS = (
    "EDGE-001",
    "EDGE-002",
    "EDGE-003",
    "EDGE-004",
    "EDGE-005",
)
NEGATIVE_CONTROL_CASE_IDS = ("NC-001", "NC-002", "NC-003")

# Canonical anomaly labels used when comparing detections with ground truth.
# Both the legacy names and the detector names normalise to the same code.
LABEL_ALIASES = {
    "ACK_BEFORE_ALARM": "ACK_BEFORE_ALARM",
    "ACK_BEFORE_EVENT": "ACK_BEFORE_ALARM",
    "IMPOSSIBLE_INTERLOCK_STATE": "INTERLOCK_STATE_MISMATCH",
    "INTERLOCK_STATE_MISMATCH": "INTERLOCK_STATE_MISMATCH",
    "INCIDENT_WITHOUT_TRIGGER": "INCIDENT_WITHOUT_VALID_TRIGGER",
    "INCIDENT_WITHOUT_VALID_TRIGGER": "INCIDENT_WITHOUT_VALID_TRIGGER",
    "ALARM_FLOOD_DUPLICATE_REPLAY": "DUPLICATE_ALARM_REPLAY",
    "DUPLICATE_ALARM_REPLAY": "DUPLICATE_ALARM_REPLAY",
    "CLOSED_WITHOUT_VERIFICATION": "CLOSED_WITHOUT_VERIFICATION",
    "NO_ANOMALY": "NO_ANOMALY",
}
