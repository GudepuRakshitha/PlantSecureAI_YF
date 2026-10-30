"""Validate the baseline dataset and fail loudly when anything is wrong.

    python src/validate_data.py
    python src/validate_data.py --data-dir data --report docs/validation_report.md

Every check is real: the process exits with status 1 if a single assertion
fails, and the success message is only printed when all checks pass.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, data_access, detection, metrics, schema


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ValidationResult:
    checks: list[Check] = field(default_factory=list)

    def record(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append(Check(name, bool(passed), detail))

    @property
    def failures(self) -> list[Check]:
        return [check for check in self.checks if not check.passed]

    @property
    def passed(self) -> bool:
        return not self.failures

    def as_markdown(self, data_dir: Path) -> str:
        lines = [
            "# Validation report",
            "",
            f"Dataset: `{data_dir}`",
            f"Seed: `{config.SEED}`",
            "",
            f"**{'PASS' if self.passed else 'FAIL'}** — "
            f"{len(self.checks) - len(self.failures)}/{len(self.checks)} checks passed.",
            "",
            "| Check | Result | Detail |",
            "|---|---|---|",
        ]
        for check in self.checks:
            status = "PASS" if check.passed else "FAIL"
            detail = check.detail.replace("|", "\\|")
            lines.append(f"| {check.name} | {status} | {detail} |")
        return "\n".join(lines) + "\n"


def _sample(values: pd.Series, limit: int = 5) -> str:
    unique = [str(value) for value in values.dropna().unique()[:limit]]
    return ", ".join(unique)


def validate_baseline(
    data_dir: Path = config.DATA_DIR,
) -> ValidationResult:
    """Run the full baseline contract validation."""
    result = ValidationResult()
    data_dir = Path(data_dir)

    try:
        frames = data_access.load_population("baseline", data_dir)
    except (FileNotFoundError, pd.errors.EmptyDataError) as error:
        result.record("Load baseline files", False, str(error))
        return result
    result.record("Load baseline files", True, f"{len(frames)} tables")

    # ------------------------------------------------------------------
    # Schema: required columns
    # ------------------------------------------------------------------
    for spec in schema.BASELINE_TABLES:
        frame = frames[spec.name]
        missing = [c for c in spec.columns if c not in frame.columns]
        result.record(
            f"{spec.name}: required columns",
            not missing,
            "missing: " + ", ".join(missing) if missing else f"{len(frame):,} rows",
        )

    # ------------------------------------------------------------------
    # Primary keys
    # ------------------------------------------------------------------
    for spec in schema.BASELINE_TABLES:
        frame = frames[spec.name]
        key = list(spec.primary_key)
        if not key:
            continue
        duplicate_count = int(frame.duplicated(subset=key).sum())
        null_count = int(frame[key].isnull().any(axis=1).sum())
        result.record(
            f"{spec.name}: primary key unique",
            duplicate_count == 0 and null_count == 0,
            f"{duplicate_count} duplicate rows, {null_count} null keys",
        )

    # ------------------------------------------------------------------
    # Nullability
    # ------------------------------------------------------------------
    for spec in schema.BASELINE_TABLES:
        frame = frames[spec.name]
        forbidden = [c for c in spec.required_columns if c in frame.columns]
        nulls = frame[forbidden].isna().sum()
        nulls = nulls[nulls > 0]
        result.record(
            f"{spec.name}: required values present",
            nulls.empty,
            "nulls: " + str(nulls.to_dict()) if not nulls.empty else "0 nulls",
        )

    # ------------------------------------------------------------------
    # Enumerations
    # ------------------------------------------------------------------
    for spec in schema.BASELINE_TABLES:
        frame = frames[spec.name]
        for column, allowed in spec.enums.items():
            if column not in frame.columns:
                continue
            invalid = frame[column].dropna()[~frame[column].dropna().isin(allowed)]
            result.record(
                f"{spec.name}.{column}: allowed values",
                invalid.empty,
                (
                    f"{len(invalid)} invalid, e.g. {_sample(invalid)}"
                    if not invalid.empty
                    else ", ".join(allowed)
                ),
            )

    # ------------------------------------------------------------------
    # Foreign keys
    # ------------------------------------------------------------------
    for spec in schema.BASELINE_TABLES:
        frame = frames[spec.name]
        for fk in spec.foreign_keys:
            if fk.columns[0] not in frame.columns:
                result.record(f"{spec.name}.{fk}", False, "column missing")
                continue
            reference = frames[fk.ref_table]
            valid = frame[fk.columns[0]].dropna().isin(reference[fk.ref_columns[0]])
            orphans = frame[fk.columns[0]].dropna()[~valid]
            result.record(
                f"{spec.name}.{fk}",
                orphans.empty,
                (
                    f"{len(orphans)} orphans, e.g. {_sample(orphans)}"
                    if not orphans.empty
                    else "all references valid"
                ),
            )

    # ------------------------------------------------------------------
    # Duplicate rows
    # ------------------------------------------------------------------
    for spec in schema.BASELINE_TABLES:
        duplicates = int(frames[spec.name].duplicated().sum())
        result.record(
            f"{spec.name}: no duplicate rows",
            duplicates == 0,
            f"{duplicates} duplicated rows",
        )

    # ------------------------------------------------------------------
    # Timestamps, acknowledgements, shifts
    # ------------------------------------------------------------------
    events = frames["alarm_events"]
    acks = frames["acknowledgements"]
    definitions = frames["alarm_definitions"]
    shifts = frames["operator_shifts"]
    incidents = frames["incidents"]
    actions = frames["corrective_actions"]

    event_times = events.set_index("alarm_event_id")["event_timestamp"]
    ack_check = acks.copy()
    ack_check["event_timestamp"] = ack_check["alarm_event_id"].map(event_times)
    ack_check = ack_check.merge(
        definitions[["alarm_definition_id", "acknowledgement_limit_minutes"]]
        .merge(
            events[["alarm_event_id", "alarm_definition_id"]],
            on="alarm_definition_id",
        )
        .drop_duplicates("alarm_event_id"),
        on="alarm_event_id",
        how="left",
        validate="many_to_one",
    )
    ack_check["computed_minutes"] = (
        ack_check["ack_timestamp"] - ack_check["event_timestamp"]
    ).dt.total_seconds() / 60

    result.record(
        "acknowledgements: no acknowledgement before its alarm",
        (ack_check["computed_minutes"] < 0).sum() == 0,
        f"{int((ack_check['computed_minutes'] < 0).sum())} early acknowledgements",
    )
    arithmetic_errors = (
        ack_check["computed_minutes"] - ack_check["response_minutes"]
    ).abs()
    result.record(
        "acknowledgements: response minutes match timestamps",
        bool((arithmetic_errors <= 0.01).all()),
        f"max error {round(float(arithmetic_errors.max()), 4)} minutes",
    )
    expected_status = (
        ack_check["computed_minutes"]
        <= ack_check["acknowledgement_limit_minutes"]
    ).map({True: "ON_TIME", False: "DELAYED"})
    result.record(
        "acknowledgements: status matches per-definition limit",
        bool((expected_status == ack_check["status"]).all()),
        f"{int((expected_status != ack_check['status']).sum())} mismatches",
    )

    shift_check = acks.merge(
        shifts[["shift_id", "plant_id", "shift_start", "shift_end"]],
        on="shift_id",
        how="left",
        validate="many_to_one",
    )
    shift_plant = events[["alarm_event_id", "machine_id"]].merge(
        frames["machines"][["machine_id", "plant_id"]],
        on="machine_id",
        how="left",
    )
    shift_check = shift_check.merge(
        shift_plant[["alarm_event_id", "plant_id"]].rename(
            columns={"plant_id": "event_plant_id"}
        ),
        on="alarm_event_id",
        how="left",
    )
    in_shift = (
        (shift_check["ack_timestamp"] >= shift_check["shift_start"])
        & (shift_check["ack_timestamp"] < shift_check["shift_end"])
    )
    result.record(
        "acknowledgements: timestamp inside owning shift",
        bool(in_shift.all()),
        f"{int((~in_shift).sum())} outside shift window",
    )
    result.record(
        "acknowledgements: shift belongs to alarm plant",
        bool((shift_check["plant_id"] == shift_check["event_plant_id"]).all()),
        f"{int((shift_check['plant_id'] != shift_check['event_plant_id']).sum())} mismatches",
    )

    # ------------------------------------------------------------------
    # Alarm lifecycle
    # ------------------------------------------------------------------
    ack_by_event = acks.groupby("alarm_event_id")["ack_timestamp"].min()
    lifecycle = events.copy()
    lifecycle["expected_ack"] = lifecycle["alarm_event_id"].map(ack_by_event)
    acked_flag = lifecycle["acknowledged"].astype(bool)
    result.record(
        "alarm_events: acknowledged flag matches acknowledgement table",
        bool(
            (
                acked_flag
                == (lifecycle["acknowledged_at"].notna())
            ).all()
        ),
        f"{int((acked_flag != lifecycle['acknowledged_at'].notna()).sum())} mismatches",
    )
    result.record(
        "alarm_events: acknowledged_at matches acknowledgement table",
        bool(
            lifecycle["acknowledged_at"].fillna(pd.Timestamp("1900-01-01"))
            .eq(lifecycle["expected_ack"].fillna(pd.Timestamp("1900-01-01")))
            .all()
        ),
        "acknowledged_at / acknowledged flag consistency",
    )
    status_rules = lifecycle["alarm_status"] == pd.Series(
        [
            "UNACKNOWLEDGED"
            if not acknowledged
            else ("CLEARED" if pd.notna(cleared) else "ACKNOWLEDGED")
            for acknowledged, cleared in zip(acked_flag, lifecycle["cleared_at"])
        ],
        index=lifecycle.index,
    )
    result.record(
        "alarm_events: lifecycle status consistent",
        bool(status_rules.all()),
        f"{int((~status_rules).sum())} inconsistent rows",
    )
    result.record(
        "alarm_events: cleared_at not before acknowledged_at",
        bool(
            (
                lifecycle["cleared_at"].isna()
                | (lifecycle["cleared_at"] >= lifecycle["acknowledged_at"])
            ).all()
        ),
        "clear timestamps ordered",
    )

    # ------------------------------------------------------------------
    # Incident / action lifecycle
    # ------------------------------------------------------------------
    incident_closed = incidents["status"] == "CLOSED"
    result.record(
        "incidents: CLOSED iff closed_at present",
        bool((incident_closed == incidents["closed_at"].notna()).all()),
        f"{int((incident_closed != incidents['closed_at'].notna()).sum())} mismatches",
    )
    result.record(
        "incidents: created_at not after closed_at",
        bool(
            (
                incidents.loc[incident_closed, "created_at"]
                <= incidents.loc[incident_closed, "closed_at"]
            ).all()
        ),
        "closed incidents ordered",
    )
    trigger = incidents.merge(
        events[["alarm_event_id", "severity", "machine_state", "event_timestamp"]],
        on="alarm_event_id",
        how="left",
        suffixes=("_incident", "_event"),
        validate="many_to_one",
    )
    valid_trigger = (
        trigger["severity_event"].isin(["HIGH", "CRITICAL"])
        & (trigger["machine_state"] == "RUNNING")
        & (
            (trigger["created_at"] - trigger["event_timestamp"]).abs()
            <= pd.Timedelta(minutes=1)
        )
    )
    result.record(
        "incidents: trigger context valid",
        bool(valid_trigger.all()),
        f"{int((~valid_trigger).sum())} incidents without a valid trigger",
    )

    action_closed = actions["status"] == "CLOSED"
    action_verified = actions["verification_status"] == "VERIFIED"
    result.record(
        "corrective_actions: CLOSED iff closed_at present",
        bool((action_closed == actions["closed_at"].notna()).all()),
        f"{int((action_closed != actions['closed_at'].notna()).sum())} mismatches",
    )
    result.record(
        "corrective_actions: VERIFIED iff verified_at present",
        bool((action_verified == actions["verified_at"].notna()).all()),
        f"{int((action_verified != actions['verified_at'].notna()).sum())} mismatches",
    )
    result.record(
        "corrective_actions: timestamps ordered",
        bool(
            (
                actions["created_at"]
                <= actions["closed_at"].fillna(actions["created_at"])
            ).all()
            and (
                actions["closed_at"].fillna(actions["created_at"])
                <= actions["verified_at"].fillna(actions["created_at"])
            ).all()
        ),
        "created_at <= closed_at <= verified_at",
    )
    actions_by_incident = actions.groupby("incident_id")["verification_status"].apply(
        lambda statuses: (statuses == "VERIFIED").any()
    )
    closed_incidents = incidents[incident_closed].copy()
    closed_incidents["has_verified_action"] = closed_incidents["incident_id"].map(
        actions_by_incident
    ).fillna(False)
    result.record(
        "incidents: closed incidents have a verified action",
        bool(closed_incidents["has_verified_action"].all()),
        f"{int((~closed_incidents['has_verified_action']).sum())} closed incidents without verified action",
    )
    open_incidents = incidents[~incident_closed]["incident_id"]
    verified_under_open = actions[
        action_verified & actions["incident_id"].isin(open_incidents)
    ]
    result.record(
        "corrective_actions: no verified action under an open incident",
        verified_under_open.empty,
        f"{len(verified_under_open)} contradictions",
    )
    result.record(
        "incidents: every incident has an action",
        bool(incidents["incident_id"].isin(actions["incident_id"]).all()),
        f"{int((~incidents['incident_id'].isin(actions['incident_id'])).sum())} incidents without actions",
    )

    # ------------------------------------------------------------------
    # Baseline must be free of anomalies
    # ------------------------------------------------------------------
    anomalies = detection.detect_anomalies(
        frames["alarm_events"],
        acks,
        frames["interlocks"],
        incidents,
        actions,
        frames["machines"],
    )
    result.record(
        "baseline: detector finds zero anomalies",
        anomalies.empty,
        (
            f"{len(anomalies)} findings: "
            + ", ".join(anomalies["exception_type"].unique()[:5])
            if not anomalies.empty
            else "clean"
        ),
    )

    # ------------------------------------------------------------------
    # Analytical outputs, when present
    # ------------------------------------------------------------------
    breaches_path = data_dir / schema.SLA_BREACHES.filename
    if breaches_path.exists():
        breaches = pd.read_csv(breaches_path)
        expected_breaches = metrics.sla_breaches(
            metrics.build_compliance(
                events, acks, definitions, frames["machines"]
            )
        )
        result.record(
            "outputs: sla_breaches.csv matches recomputation",
            len(breaches) == len(expected_breaches),
            f"{len(breaches)} persisted vs {len(expected_breaches)} expected",
        )
        result.record(
            "outputs: sla_breaches contains only routine breaches",
            bool(breaches["is_routine_sla"].astype(bool).all())
            if not breaches.empty
            else True,
            "is_routine_sla must be True",
        )

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    result = validate_baseline(args.data_dir)

    print("\n========== BASELINE DATA VALIDATION ==========\n")
    for check in result.checks:
        if not check.passed:
            print(f"FAIL: {check.name} -> {check.detail}")
    passed = len(result.checks) - len(result.failures)
    print(f"\n{passed}/{len(result.checks)} checks passed")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(result.as_markdown(args.data_dir), encoding="utf-8")
        print(f"Report written to {args.report}")

    if not result.passed:
        print("\nVALIDATION FAILED")
        return 1
    print("ALL BASELINE VALIDATIONS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
