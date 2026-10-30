"""Anomaly detection and ground-truth scoring.

The detector is intentionally rule-based and readable.  It works on any
population (baseline or scenario), attributes every finding to a plant,
machine and case, and never emits routine SLA breaches -- those live in
``metrics.sla_breaches``.
"""

from __future__ import annotations

import pandas as pd

from src import config, schema


def normalize_label(label: object) -> str:
    """Map expected and detected labels onto one canonical vocabulary."""
    key = str(label).strip().upper()
    return config.LABEL_ALIASES.get(key, key)


def _empty_detections() -> pd.DataFrame:
    return pd.DataFrame(columns=list(schema.ANALYSIS_EXCEPTIONS.columns))


def _context_columns(frame: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    columns = {}
    if "plant_id" in frame.columns:
        columns[f"{prefix}plant_id"] = frame["plant_id"]
    if "machine_id" in frame.columns:
        columns[f"{prefix}machine_id"] = frame["machine_id"]
    return pd.DataFrame(columns, index=frame.index)


def detect_anomalies(
    events: pd.DataFrame,
    acknowledgements: pd.DataFrame,
    interlocks: pd.DataFrame,
    incidents: pd.DataFrame,
    actions: pd.DataFrame,
    machines: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Detect data-quality and safety anomalies in a population.

    Returns one row per finding with the schema required by
    ``data/analysis_exceptions.csv``.  Baseline data is expected to produce
    zero findings; injected scenarios produce the five known cases.
    """
    rows: list[dict[str, object]] = []

    def add(
        exception_type: str,
        entity: str,
        record_id: object,
        severity: object,
        description: str,
        *,
        plant_id: object = None,
        machine_id: object = None,
        case_id: object = None,
    ) -> None:
        rows.append(
            {
                "exception_type": exception_type,
                "entity": entity,
                "record_id": str(record_id),
                "severity": str(severity) if pd.notna(severity) else "MEDIUM",
                "plant_id": plant_id if pd.notna(plant_id) else None,
                "machine_id": machine_id if pd.notna(machine_id) else None,
                "case_id": case_id if pd.notna(case_id) else None,
                "is_routine_sla": False,
                "description": description,
            }
        )

    if events.empty and acknowledgements.empty:
        return _empty_detections()

    # ------------------------------------------------------------------
    # Machine context
    # ------------------------------------------------------------------
    machines_context = None
    if machines is not None and "machine_id" in machines.columns:
        context_columns = [
            c for c in ("machine_id", "plant_id") if c in machines.columns
        ]
        machines_context = machines[context_columns].drop_duplicates("machine_id")

    events = events.copy()
    if "case_id" not in events.columns:
        events["case_id"] = None
    if machines_context is not None and "plant_id" not in events.columns:
        events = events.merge(
            machines_context, on="machine_id", how="left", validate="many_to_one"
        )

    # ------------------------------------------------------------------
    # 1. Acknowledgement arithmetic
    # ------------------------------------------------------------------
    if not acknowledgements.empty:
        acks = acknowledgements.copy()
        if "case_id" not in acks.columns:
            acks["case_id"] = None
        acks["ack_timestamp"] = pd.to_datetime(acks["ack_timestamp"], errors="coerce")
        event_context_columns = [
            c
            for c in (
                "alarm_event_id",
                "event_timestamp",
                "machine_id",
                "plant_id",
                "severity",
            )
            if c in events.columns
        ]
        ack_context = acks.merge(
            events[event_context_columns].drop_duplicates("alarm_event_id"),
            on="alarm_event_id",
            how="left",
            validate="many_to_one",
        )
        ack_context["event_timestamp"] = pd.to_datetime(
            ack_context["event_timestamp"], errors="coerce"
        )

        unknown = ack_context[ack_context["event_timestamp"].isna()]
        for row in unknown.itertuples(index=False):
            add(
                "ACK_WITHOUT_ALARM",
                "Acknowledgement",
                row.acknowledgement_id,
                "HIGH",
                "Acknowledgement references an alarm event that does not exist.",
                case_id=getattr(row, "case_id", None),
            )

        before = ack_context[
            ack_context["event_timestamp"].notna()
            & (ack_context["ack_timestamp"] < ack_context["event_timestamp"])
        ]
        for row in before.itertuples(index=False):
            add(
                "ACK_BEFORE_ALARM",
                "Acknowledgement",
                row.acknowledgement_id,
                "CRITICAL",
                "Acknowledgement timestamp precedes its alarm activation.",
                plant_id=getattr(row, "plant_id", None),
                machine_id=getattr(row, "machine_id", None),
                case_id=getattr(row, "case_id", None),
            )

    # ------------------------------------------------------------------
    # 2. Interlock state contradiction
    # ------------------------------------------------------------------
    if not interlocks.empty:
        interlock_frame = interlocks.copy()
        if "case_id" not in interlock_frame.columns:
            interlock_frame["case_id"] = None
        if machines_context is not None and "plant_id" not in interlock_frame.columns:
            interlock_frame = interlock_frame.merge(
                machines_context, on="machine_id", how="left", validate="many_to_one"
            )
        mismatched = interlock_frame[
            interlock_frame["current_state"] != interlock_frame["required_state"]
        ]
        for row in mismatched.itertuples(index=False):
            add(
                "INTERLOCK_STATE_MISMATCH",
                "Interlock",
                row.interlock_id,
                "CRITICAL",
                "Current interlock state contradicts the required safe state.",
                plant_id=getattr(row, "plant_id", None),
                machine_id=getattr(row, "machine_id", None),
                case_id=getattr(row, "case_id", None),
            )

    # ------------------------------------------------------------------
    # 3. Incident trigger context (severity, machine state and time)
    # ------------------------------------------------------------------
    if not incidents.empty:
        incidents_frame = incidents.copy()
        if "case_id" not in incidents_frame.columns:
            incidents_frame["case_id"] = None
        incidents_frame["created_at"] = pd.to_datetime(
            incidents_frame["created_at"], errors="coerce"
        )
        trigger_columns = [
            c
            for c in ("alarm_event_id", "event_timestamp", "severity", "machine_state")
            if c in events.columns
        ]
        trigger = incidents_frame.merge(
            events[trigger_columns].drop_duplicates("alarm_event_id"),
            on="alarm_event_id",
            how="left",
            suffixes=("_incident", "_event"),
            validate="many_to_one",
        )
        event_timestamp = pd.to_datetime(
            trigger.get("event_timestamp"), errors="coerce"
        )
        valid_trigger = (
            trigger["severity_event"].isin(["HIGH", "CRITICAL"])
            & (trigger["machine_state"] == "RUNNING")
            & event_timestamp.notna()
            & (
                (trigger["created_at"] - event_timestamp).abs()
                <= pd.Timedelta(minutes=1)
            )
        ).fillna(False)
        invalid = trigger[~valid_trigger]
        for row in invalid.itertuples(index=False):
            add(
                "INCIDENT_WITHOUT_VALID_TRIGGER",
                "Incident",
                row.incident_id,
                getattr(row, "severity_incident", "HIGH"),
                "Incident has no qualifying HIGH/CRITICAL alarm on a RUNNING "
                "machine at the incident creation time.",
                plant_id=getattr(row, "plant_id", None),
                machine_id=getattr(row, "machine_id", None),
                case_id=getattr(row, "case_id", None),
            )

    # ------------------------------------------------------------------
    # 4. Duplicate alarm primary keys (replay)
    # ------------------------------------------------------------------
    if not events.empty:
        duplicates = events["alarm_event_id"].value_counts()
        duplicates = duplicates[duplicates > 1]
        for event_id in duplicates.index:
            sample = events[events["alarm_event_id"] == event_id].iloc[0]
            add(
                "DUPLICATE_ALARM_REPLAY",
                "AlarmEvent",
                event_id,
                sample["severity"],
                f"Alarm event primary key appears {int(duplicates[event_id])} times.",
                plant_id=sample.get("plant_id"),
                machine_id=sample.get("machine_id"),
                case_id=sample.get("case_id"),
            )

    # ------------------------------------------------------------------
    # 5. Closed corrective action without verification
    # ------------------------------------------------------------------
    if not actions.empty:
        actions_frame = actions.copy()
        if "case_id" not in actions_frame.columns:
            actions_frame["case_id"] = None
        unverified = actions_frame[
            (actions_frame["status"] == "CLOSED")
            & (actions_frame["verification_status"] != "VERIFIED")
        ]
        incident_context = (
            incidents[["incident_id", "plant_id", "machine_id", "severity"]]
            .drop_duplicates("incident_id")
            if not incidents.empty
            else pd.DataFrame(columns=["incident_id", "plant_id", "machine_id", "severity"])
        )
        unverified = unverified.merge(
            incident_context,
            on="incident_id",
            how="left",
            suffixes=("", "_incident"),
            validate="many_to_one",
        )
        for row in unverified.itertuples(index=False):
            add(
                "CLOSED_WITHOUT_VERIFICATION",
                "CorrectiveAction",
                row.action_id,
                getattr(row, "severity_incident", "HIGH"),
                "Corrective action is CLOSED without successful verification.",
                plant_id=getattr(row, "plant_id_incident", getattr(row, "plant_id", None)),
                machine_id=getattr(
                    row, "machine_id_incident", getattr(row, "machine_id", None)
                ),
                case_id=getattr(row, "case_id", None),
            )

    # ------------------------------------------------------------------
    # 6. Lifecycle contradictions
    # ------------------------------------------------------------------
    if not incidents.empty:
        incidents_frame = incidents.copy()
        if "case_id" not in incidents_frame.columns:
            incidents_frame["case_id"] = None
        closed_at = pd.to_datetime(incidents_frame["closed_at"], errors="coerce")
        has_closed_at = closed_at.notna()
        is_closed = incidents_frame["status"] == "CLOSED"
        for row in incidents_frame[is_closed != has_closed_at].itertuples(index=False):
            add(
                "LIFECYCLE_INCONSISTENCY",
                "Incident",
                row.incident_id,
                row.severity,
                "Incident status and closed_at disagree.",
                plant_id=row.plant_id,
                machine_id=row.machine_id,
                case_id=getattr(row, "case_id", None),
            )

    if not actions.empty:
        actions_frame = actions.copy()
        if "case_id" not in actions_frame.columns:
            actions_frame["case_id"] = None
        actions_frame["created_at"] = pd.to_datetime(
            actions_frame["created_at"], errors="coerce"
        )
        actions_frame["closed_at"] = pd.to_datetime(
            actions_frame["closed_at"], errors="coerce"
        )
        actions_frame["verified_at"] = pd.to_datetime(
            actions_frame["verified_at"], errors="coerce"
        )
        closed = actions_frame["status"] == "CLOSED"
        verified = actions_frame["verification_status"] == "VERIFIED"
        bad_closed = closed & actions_frame["closed_at"].isna()
        bad_verified = verified & actions_frame["verified_at"].isna()
        time_errors = (
            (actions_frame["closed_at"] < actions_frame["created_at"])
            | (actions_frame["verified_at"] < actions_frame["closed_at"])
        ).fillna(False)
        incident_links = (
            incidents[["incident_id", "status", "plant_id", "machine_id", "severity"]]
            .drop_duplicates("incident_id")
            .rename(columns={"status": "incident_status"})
            if not incidents.empty
            else pd.DataFrame(
                columns=[
                    "incident_id",
                    "incident_status",
                    "plant_id",
                    "machine_id",
                    "severity",
                ]
            )
        )
        merged = actions_frame.merge(
            incident_links,
            on="incident_id",
            how="left",
            suffixes=("", "_incident"),
            validate="many_to_one",
        )
        inconsistent_incident = (
            closed
            & verified
            & (merged["incident_status"] != "CLOSED")
        ).fillna(False)

        for row in merged[
            bad_closed | bad_verified | time_errors | inconsistent_incident
        ].itertuples(index=False):
            add(
                "LIFECYCLE_INCONSISTENCY",
                "CorrectiveAction",
                row.action_id,
                getattr(row, "severity_incident", "MEDIUM"),
                "Corrective action lifecycle timestamps or incident state disagree.",
                plant_id=getattr(row, "plant_id_incident", getattr(row, "plant_id", None)),
                machine_id=getattr(
                    row, "machine_id_incident", getattr(row, "machine_id", None)
                ),
                case_id=getattr(row, "case_id", None),
            )

    if not events.empty:
        acknowledged_at = pd.to_datetime(
            events["acknowledged_at"], errors="coerce"
        )
        cleared_at = pd.to_datetime(events["cleared_at"], errors="coerce")
        acknowledged = events["acknowledged"].astype(bool)
        status = events["alarm_status"]
        bad = (
            (acknowledged != acknowledged_at.notna())
            | (acknowledged & (status == "UNACKNOWLEDGED"))
            | (cleared_at.notna() & (status != "CLEARED"))
            | ((status == "CLEARED") & cleared_at.isna())
            | (cleared_at < acknowledged_at)
        ).fillna(False)
        for row in events[bad].itertuples(index=False):
            add(
                "LIFECYCLE_INCONSISTENCY",
                "AlarmEvent",
                row.alarm_event_id,
                row.severity,
                "Alarm lifecycle status, acknowledgement and clear timestamps disagree.",
                plant_id=getattr(row, "plant_id", None),
                machine_id=row.machine_id,
                case_id=getattr(row, "case_id", None),
            )

    if not rows:
        return _empty_detections()

    detections = pd.DataFrame(rows, columns=list(schema.ANALYSIS_EXCEPTIONS.columns))
    return detections.drop_duplicates(
        subset=["exception_type", "record_id"], keep="first"
    ).reset_index(drop=True)


def evaluate_detection(
    detections: pd.DataFrame, ground_truth: pd.DataFrame
) -> dict[str, object]:
    """Score detected anomalies against ground truth with label normalisation."""
    truth = ground_truth.copy()
    expected = truth[truth["is_anomaly"].astype(bool)].copy()
    negatives = truth[~truth["is_anomaly"].astype(bool)].copy()

    expected["label"] = expected["expected_label"].map(normalize_label)
    expected["record_id"] = expected["record_id"].astype(str)
    expected_pairs = set(zip(expected["label"], expected["record_id"]))

    detected = detections.copy()
    if detected.empty:
        detected_pairs: set[tuple[str, str]] = set()
    else:
        detected["label"] = detected["exception_type"].map(normalize_label)
        detected["record_id"] = detected["record_id"].astype(str)
        detected_pairs = set(zip(detected["label"], detected["record_id"]))

    true_positives = expected_pairs & detected_pairs
    false_negatives = expected_pairs - detected_pairs
    false_positives = detected_pairs - expected_pairs

    expected_cases = set(expected["case_id"])
    detected_case_ids = set(
        detected["case_id"].dropna().astype(str)
    ) if not detected.empty else set()
    # A case counts as detected only when one of its expected records matched.
    matched_records = {record for _, record in true_positives}
    detected_cases = set(
        expected.loc[expected["record_id"].isin(matched_records), "case_id"]
    )
    missing_cases = sorted(expected_cases - detected_cases)

    negative_ids = set(negatives["record_id"].astype(str))
    flagged_negatives = sorted(
        {
            record_id
            for _, record_id in detected_pairs
            if record_id in negative_ids
        }
    )

    def safe_ratio(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator else 0.0

    return {
        "expected_anomalies": int(len(expected_pairs)),
        "detected_anomalies": int(len(detected_pairs)),
        "true_positives": int(len(true_positives)),
        "false_positives": int(len(false_positives)),
        "false_negatives": int(len(false_negatives)),
        "precision": safe_ratio(len(true_positives), len(true_positives) + len(false_positives)),
        "recall": safe_ratio(len(true_positives), len(true_positives) + len(false_negatives)),
        "expected_cases": sorted(expected_cases),
        "detected_cases": sorted(detected_cases),
        "missing_cases": missing_cases,
        "negative_controls": int(len(negatives)),
        "negative_controls_flagged": flagged_negatives,
        "false_negative_details": sorted(false_negatives),
        "false_positive_details": sorted(false_positives),
    }
