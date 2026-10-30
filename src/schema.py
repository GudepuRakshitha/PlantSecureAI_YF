"""Single source of truth for table columns, keys and enumerations.

The generators, validators, analyzer, dashboard and tests all import these
definitions, so a schema change only has to be made in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src import config


@dataclass(frozen=True)
class ForeignKey:
    """A foreign-key relationship between two tables."""

    columns: tuple[str, ...]
    ref_table: str
    ref_columns: tuple[str, ...]

    def __str__(self) -> str:
        left = ", ".join(self.columns)
        right = ", ".join(self.ref_columns)
        return f"{left} -> {self.ref_table}.{right}"


@dataclass(frozen=True)
class TableSpec:
    """Column contract for one CSV table."""

    name: str
    filename: str
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]
    enums: dict[str, tuple[str, ...]] = field(default_factory=dict)
    datetime_columns: tuple[str, ...] = ()
    boolean_columns: tuple[str, ...] = ()
    integer_columns: tuple[str, ...] = ()
    nullable: tuple[str, ...] = ()
    foreign_keys: tuple[ForeignKey, ...] = ()

    @property
    def required_columns(self) -> tuple[str, ...]:
        return tuple(c for c in self.columns if c not in self.nullable)

    @property
    def enum_columns(self) -> tuple[str, ...]:
        return tuple(self.enums)

    @property
    def non_nullable(self) -> tuple[str, ...]:
        return self.required_columns


def _fk(column: str, ref_table: str, ref_column: str) -> ForeignKey:
    return ForeignKey((column,), ref_table, (ref_column,))


# ---------------------------------------------------------------------------
# Master data
# ---------------------------------------------------------------------------

PLANTS = TableSpec(
    name="plants",
    filename="plants.csv",
    columns=("plant_id", "plant_name", "location", "status"),
    primary_key=("plant_id",),
    enums={"status": ("ACTIVE", "INACTIVE")},
)

SAFETY_ZONES = TableSpec(
    name="safety_zones",
    filename="safety_zones.csv",
    columns=("zone_id", "plant_id", "zone_name", "risk_level"),
    primary_key=("zone_id",),
    enums={"risk_level": config.ZONE_RISK_LEVELS},
    foreign_keys=(_fk("plant_id", "plants", "plant_id"),),
)

MACHINES = TableSpec(
    name="machines",
    filename="machines.csv",
    columns=(
        "machine_id",
        "plant_id",
        "zone_id",
        "machine_name",
        "machine_type",
        "status",
    ),
    primary_key=("machine_id",),
    enums={
        "machine_type": config.MACHINE_TYPES,
        "status": ("ACTIVE", "INACTIVE"),
    },
    foreign_keys=(
        _fk("plant_id", "plants", "plant_id"),
        _fk("zone_id", "safety_zones", "zone_id"),
    ),
)

INTERLOCKS = TableSpec(
    name="interlocks",
    filename="interlocks.csv",
    columns=(
        "interlock_id",
        "machine_id",
        "interlock_name",
        "required_state",
        "current_state",
    ),
    primary_key=("interlock_id",),
    enums={
        "required_state": config.INTERLOCK_STATES,
        "current_state": config.INTERLOCK_STATES,
    },
    foreign_keys=(_fk("machine_id", "machines", "machine_id"),),
)

ALARM_DEFINITIONS = TableSpec(
    name="alarm_definitions",
    filename="alarm_definitions.csv",
    columns=(
        "alarm_definition_id",
        "machine_id",
        "alarm_name",
        "severity",
        "acknowledgement_required",
        "acknowledgement_limit_minutes",
    ),
    primary_key=("alarm_definition_id",),
    enums={"severity": config.SEVERITIES},
    boolean_columns=("acknowledgement_required",),
    integer_columns=("acknowledgement_limit_minutes",),
    foreign_keys=(_fk("machine_id", "machines", "machine_id"),),
)

# ---------------------------------------------------------------------------
# Transaction data
# ---------------------------------------------------------------------------

ALARM_EVENTS = TableSpec(
    name="alarm_events",
    filename="alarm_events.csv",
    columns=(
        "alarm_event_id",
        "machine_id",
        "alarm_definition_id",
        "severity",
        "event_timestamp",
        "machine_state",
        "alarm_status",
        "acknowledged",
        "acknowledged_at",
        "cleared_at",
        "state_transition",
        "issue_type",
    ),
    primary_key=("alarm_event_id",),
    enums={
        "severity": config.SEVERITIES,
        "machine_state": config.MACHINE_STATES,
        "alarm_status": config.ALARM_STATUSES,
        "issue_type": config.ISSUE_TYPES,
    },
    datetime_columns=("event_timestamp", "acknowledged_at", "cleared_at"),
    boolean_columns=("acknowledged",),
    nullable=("acknowledged_at", "cleared_at"),
    foreign_keys=(
        _fk("machine_id", "machines", "machine_id"),
        _fk("alarm_definition_id", "alarm_definitions", "alarm_definition_id"),
    ),
)

OPERATOR_SHIFTS = TableSpec(
    name="operator_shifts",
    filename="operator_shifts.csv",
    columns=("shift_id", "plant_id", "operator_id", "shift_start", "shift_end"),
    primary_key=("shift_id",),
    datetime_columns=("shift_start", "shift_end"),
    foreign_keys=(_fk("plant_id", "plants", "plant_id"),),
)

ACKNOWLEDGEMENTS = TableSpec(
    name="acknowledgements",
    filename="acknowledgements.csv",
    columns=(
        "acknowledgement_id",
        "alarm_event_id",
        "operator_id",
        "shift_id",
        "ack_timestamp",
        "response_minutes",
        "status",
    ),
    primary_key=("acknowledgement_id",),
    enums={"status": config.ACK_STATUSES},
    datetime_columns=("ack_timestamp",),
    integer_columns=("response_minutes",),
    foreign_keys=(
        _fk("alarm_event_id", "alarm_events", "alarm_event_id"),
        _fk("shift_id", "operator_shifts", "shift_id"),
    ),
)

INCIDENTS = TableSpec(
    name="incidents",
    filename="incidents.csv",
    columns=(
        "incident_id",
        "alarm_event_id",
        "machine_id",
        "plant_id",
        "incident_type",
        "severity",
        "created_at",
        "closed_at",
        "status",
    ),
    primary_key=("incident_id",),
    enums={
        "severity": config.SEVERITIES,
        "incident_type": config.INCIDENT_TYPES,
        "status": config.INCIDENT_STATUSES,
    },
    datetime_columns=("created_at", "closed_at"),
    nullable=("closed_at",),
    foreign_keys=(
        _fk("alarm_event_id", "alarm_events", "alarm_event_id"),
        _fk("machine_id", "machines", "machine_id"),
        _fk("plant_id", "plants", "plant_id"),
    ),
)

CORRECTIVE_ACTIONS = TableSpec(
    name="corrective_actions",
    filename="corrective_actions.csv",
    columns=(
        "action_id",
        "incident_id",
        "action_description",
        "assigned_to",
        "created_at",
        "closed_at",
        "verified_at",
        "status",
        "verification_status",
        "effectiveness_status",
    ),
    primary_key=("action_id",),
    enums={
        "status": config.ACTION_STATUSES,
        "verification_status": config.VERIFICATION_STATUSES,
        "effectiveness_status": config.EFFECTIVENESS_STATUSES,
    },
    datetime_columns=("created_at", "closed_at", "verified_at"),
    nullable=("closed_at", "verified_at"),
    foreign_keys=(_fk("incident_id", "incidents", "incident_id"),),
)

# ---------------------------------------------------------------------------
# Analytical outputs (produced by src/safety_analyzer.py)
# ---------------------------------------------------------------------------

SLA_BREACHES = TableSpec(
    name="sla_breaches",
    filename="sla_breaches.csv",
    columns=(
        "record_id",
        "alarm_event_id",
        "acknowledgement_id",
        "plant_id",
        "machine_id",
        "alarm_definition_id",
        "severity",
        "event_timestamp",
        "acknowledged_at",
        "response_minutes",
        "acknowledgement_limit_minutes",
        "overdue_minutes",
        "is_routine_sla",
    ),
    primary_key=("record_id",),
    enums={"severity": config.SEVERITIES},
    datetime_columns=("event_timestamp", "acknowledged_at"),
    boolean_columns=("is_routine_sla",),
)

ANALYSIS_EXCEPTIONS = TableSpec(
    name="analysis_exceptions",
    filename="analysis_exceptions.csv",
    columns=(
        "exception_type",
        "entity",
        "record_id",
        "severity",
        "plant_id",
        "machine_id",
        "case_id",
        "is_routine_sla",
        "description",
    ),
    primary_key=(),
    enums={"severity": config.SEVERITIES},
    boolean_columns=("is_routine_sla",),
    nullable=("plant_id", "machine_id", "case_id"),
)

GROUND_TRUTH = TableSpec(
    name="ground_truth",
    filename="ground_truth.csv",
    columns=(
        "case_id",
        "scenario_type",
        "expected_label",
        "entity",
        "record_id",
        "is_anomaly",
        "description",
    ),
    primary_key=(),
    boolean_columns=("is_anomaly",),
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BASELINE_TABLES: tuple[TableSpec, ...] = (
    PLANTS,
    SAFETY_ZONES,
    MACHINES,
    INTERLOCKS,
    ALARM_DEFINITIONS,
    OPERATOR_SHIFTS,
    ALARM_EVENTS,
    ACKNOWLEDGEMENTS,
    INCIDENTS,
    CORRECTIVE_ACTIONS,
)

# Tables that participate in the injected-scenario test population.  Their
# files live under data/scenarios/ and are logically separate from baseline.
SCENARIO_TABLES: tuple[TableSpec, ...] = (
    ALARM_EVENTS,
    ACKNOWLEDGEMENTS,
    INTERLOCKS,
    INCIDENTS,
    CORRECTIVE_ACTIONS,
)

SCENARIO_FILENAMES = {
    ALARM_EVENTS.name: "injected_alarm_events.csv",
    ACKNOWLEDGEMENTS.name: "injected_acknowledgements.csv",
    INTERLOCKS.name: "injected_interlocks.csv",
    INCIDENTS.name: "injected_incidents.csv",
    CORRECTIVE_ACTIONS.name: "injected_corrective_actions.csv",
}

TABLES_BY_NAME = {spec.name: spec for spec in BASELINE_TABLES}

# Column used to detect a row that belongs to an injected scenario.
CASE_ID_COLUMN = "case_id"
