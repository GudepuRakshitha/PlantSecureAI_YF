"""Shared metric calculation layer.

The analyzer, the validators, the tests and the dashboard all call these
functions.  No metric definition is duplicated elsewhere.

Denominator policy
------------------
Every acknowledgement percentage is denominated by *alarm activations*, not by
acknowledgement rows.  An alarm with no acknowledgement is therefore counted
as non-compliant instead of disappearing from the calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from src import config, schema

COMPLIANCE_STATUSES = ("ON_TIME", "LATE", "UNACKNOWLEDGED")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pct(numerator: float, denominator: float) -> float:
    """Percentage with a zero-safe denominator, rounded to 2 decimals."""
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, 2)


def _to_datetime(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(pd.NaT, index=frame.index)
    return pd.to_datetime(frame[column], errors="coerce")


def _with_machine_context(
    frame: pd.DataFrame, machines: pd.DataFrame | None
) -> pd.DataFrame:
    if machines is None or "machine_id" not in frame.columns:
        return frame
    context_columns = [
        column
        for column in ("machine_id", "plant_id", "machine_name", "zone_id")
        if column in machines.columns
    ]
    context = machines[context_columns].drop_duplicates("machine_id")
    extra = [c for c in context_columns if c not in frame.columns or c == "machine_id"]
    result = frame.merge(
        context[extra], on="machine_id", how="left", validate="many_to_one"
    )
    return result


# ---------------------------------------------------------------------------
# Acknowledgement compliance
# ---------------------------------------------------------------------------


def build_compliance(
    events: pd.DataFrame,
    acknowledgements: pd.DataFrame,
    definitions: pd.DataFrame,
    machines: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return one row per alarm activation with its acknowledgement outcome."""
    required = {"alarm_event_id", "event_timestamp", "machine_id", "severity"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"alarm events missing columns: {sorted(missing)}")

    events = events.copy()
    events["event_timestamp"] = _to_datetime(events, "event_timestamp")
    # The acknowledgement outcome must come from the acknowledgement table, not
    # from the cached lifecycle columns on the event, so drop them before the
    # left join to avoid a column collision.
    events = events.drop(
        columns=[c for c in ("acknowledged", "acknowledged_at") if c in events.columns]
    )

    acks = acknowledgements.copy()
    if not acks.empty:
        acks["ack_timestamp"] = _to_datetime(acks, "ack_timestamp")
        # Scenario data may contain duplicate acknowledgements; keep the first
        # logged row so a duplicate cannot fan out activation counts.
        acks = (
            acks.sort_values(["ack_timestamp", "acknowledgement_id"])
            .drop_duplicates("alarm_event_id", keep="first")
            .rename(columns={"ack_timestamp": "acknowledged_at"})
        )
        ack_columns = [
            c
            for c in (
                "alarm_event_id",
                "acknowledgement_id",
                "acknowledged_at",
                "operator_id",
                "shift_id",
            )
            if c in acks.columns
        ]
        acks = acks[ack_columns]
    else:
        acks = pd.DataFrame(
            columns=[
                "alarm_event_id",
                "acknowledgement_id",
                "acknowledged_at",
                "operator_id",
                "shift_id",
            ]
        )

    compliance = events.merge(
        acks, on="alarm_event_id", how="left", validate="many_to_one"
    )

    limits = definitions[["alarm_definition_id", "acknowledgement_limit_minutes"]]
    compliance = compliance.merge(
        limits, on="alarm_definition_id", how="left", validate="many_to_one"
    )

    compliance = _with_machine_context(compliance, machines)

    compliance["response_minutes"] = (
        compliance["acknowledged_at"] - compliance["event_timestamp"]
    ).dt.total_seconds() / 60.0
    compliance["acknowledged"] = compliance["acknowledged_at"].notna()
    compliance["acknowledgement_limit_minutes"] = pd.to_numeric(
        compliance["acknowledgement_limit_minutes"], errors="coerce"
    ).fillna(config.ACK_LIMIT_MINUTES)

    is_late = compliance["acknowledged"] & (
        compliance["response_minutes"]
        > compliance["acknowledgement_limit_minutes"]
    )
    compliance["ack_status"] = np.select(
        [~compliance["acknowledged"], is_late],
        ["UNACKNOWLEDGED", "LATE"],
        default="ON_TIME",
    )
    compliance["event_date"] = compliance["event_timestamp"].dt.date
    compliance["event_hour"] = compliance["event_timestamp"].dt.hour
    return compliance


def ack_compliance_metrics(compliance: pd.DataFrame) -> dict[str, object]:
    """Headline acknowledgement KPIs, all activation-denominated."""
    total = int(len(compliance))
    acknowledged = int(compliance["acknowledged"].sum())
    on_time = int((compliance["ack_status"] == "ON_TIME").sum())
    late = int((compliance["ack_status"] == "LATE").sum())
    unacknowledged = int((compliance["ack_status"] == "UNACKNOWLEDGED").sum())
    response = pd.to_numeric(compliance["response_minutes"], errors="coerce").dropna()

    return {
        "total_activations": total,
        "total_acknowledged": acknowledged,
        "total_unacknowledged": unacknowledged,
        "on_time_acknowledgements": on_time,
        "late_acknowledgements": late,
        "acknowledgement_rate_pct": pct(acknowledged, total),
        "on_time_compliance_pct": pct(on_time, total),
        "late_acknowledgement_pct": pct(late, total),
        "unacknowledged_pct": pct(unacknowledged, total),
        "median_response_minutes": round(float(response.median()), 2)
        if not response.empty
        else 0.0,
        "p95_response_minutes": round(float(response.quantile(0.95)), 2)
        if not response.empty
        else 0.0,
        "mean_response_minutes": round(float(response.mean()), 2)
        if not response.empty
        else 0.0,
    }


def mtta_statistics(compliance: pd.DataFrame) -> dict[str, float]:
    """Median / p95 / mean response time over acknowledged activations."""
    metrics = ack_compliance_metrics(compliance)
    return {
        "median_response_minutes": metrics["median_response_minutes"],
        "p95_response_minutes": metrics["p95_response_minutes"],
        "mean_response_minutes": metrics["mean_response_minutes"],
    }


def sla_breaches(compliance: pd.DataFrame) -> pd.DataFrame:
    """Routine late acknowledgements, kept out of the anomaly stream."""
    late = compliance[compliance["ack_status"] == "LATE"].copy()
    if late.empty:
        return pd.DataFrame(columns=list(schema.SLA_BREACHES.columns))

    late["record_id"] = late["alarm_event_id"]
    late["overdue_minutes"] = (
        late["response_minutes"] - late["acknowledgement_limit_minutes"]
    ).round(2)
    late["is_routine_sla"] = True
    columns = [
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
    ]
    for column in columns:
        if column not in late.columns:
            late[column] = pd.NA
    return late[columns].reset_index(drop=True)


def unacknowledged_alarms(compliance: pd.DataFrame) -> pd.DataFrame:
    """Activation-level rows with no acknowledgement record."""
    columns = [
        "alarm_event_id",
        "plant_id",
        "machine_id",
        "alarm_definition_id",
        "severity",
        "event_timestamp",
        "alarm_status",
        "response_minutes",
        "acknowledgement_limit_minutes",
    ]
    missing = [c for c in columns if c not in compliance.columns]
    unacked = compliance[compliance["ack_status"] == "UNACKNOWLEDGED"]
    return unacked[[c for c in columns if c in unacked.columns]].reset_index(drop=True)


def priority_compliance(compliance: pd.DataFrame) -> pd.DataFrame:
    """Compliance split by alarm priority (severity)."""
    rows = []
    for severity in config.SEVERITIES:
        subset = compliance[compliance["severity"] == severity]
        metrics = ack_compliance_metrics(subset)
        rows.append(
            {
                "severity": severity,
                "activations": metrics["total_activations"],
                "acknowledged": metrics["total_acknowledged"],
                "on_time": metrics["on_time_acknowledgements"],
                "late": metrics["late_acknowledgements"],
                "unacknowledged": metrics["total_unacknowledged"],
                "acknowledgement_rate_pct": metrics["acknowledgement_rate_pct"],
                "on_time_compliance_pct": metrics["on_time_compliance_pct"],
                "unacknowledged_pct": metrics["unacknowledged_pct"],
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Alarm volume / distributions
# ---------------------------------------------------------------------------


def alarm_counts(events: pd.DataFrame) -> dict[str, int]:
    """Basic alarm counters."""
    return {
        "total_alarm_activations": int(len(events)),
        "critical_alarms": int((events["severity"] == "CRITICAL").sum()),
        "high_alarms": int((events["severity"] == "HIGH").sum()),
        "distinct_machines": int(events["machine_id"].nunique()),
        "distinct_definitions": int(events["alarm_definition_id"].nunique()),
    }


def severity_distribution(events: pd.DataFrame) -> pd.DataFrame:
    """Counts and share of activations by severity, in priority order."""
    counts = (
        events["severity"].value_counts().reindex(config.SEVERITIES, fill_value=0)
    )
    total = int(counts.sum())
    return pd.DataFrame(
        {
            "severity": counts.index,
            "count": counts.to_numpy(dtype=int),
            "percentage": [
                pct(value, total) for value in counts.to_numpy(dtype=int)
            ],
        }
    )


def severity_pareto(events: pd.DataFrame) -> pd.DataFrame:
    """Pareto view: count, share and cumulative share by priority."""
    pareto = severity_distribution(events).sort_values(
        "count", ascending=False
    ).reset_index(drop=True)
    pareto["cumulative_pct"] = pareto["percentage"].cumsum().round(2)
    return pareto


def alarm_counts_by(
    events: pd.DataFrame,
    by: str,
    context: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Count activations by an arbitrary column, with context labels."""
    if by not in events.columns:
        raise ValueError(f"unknown grouping column: {by}")
    counts = (
        events.groupby(by, dropna=False)
        .size()
        .reset_index(name="alarms")
        .sort_values("alarms", ascending=False)
    )
    if context is not None and by in context.columns:
        label_columns = [
            c
            for c in ("machine_id", "machine_name", "plant_id", "plant_name")
            if c in context.columns and c not in counts.columns
        ]
        counts = counts.merge(
            context[[by, *label_columns]].drop_duplicates(by),
            on=by,
            how="left",
            validate="one_to_one",
        )
    return counts


def plant_alarm_distribution(events: pd.DataFrame) -> pd.DataFrame:
    return alarm_counts_by(events, "plant_id").rename(
        columns={"alarms": "alarm_count"}
    )


def machine_alarm_distribution(
    events: pd.DataFrame, machines: pd.DataFrame | None = None
) -> pd.DataFrame:
    result = alarm_counts_by(events, "machine_id", machines)
    return result.rename(columns={"alarms": "alarm_count"})


# ---------------------------------------------------------------------------
# Time-based analytics
# ---------------------------------------------------------------------------


def daily_alarm_trend(events: pd.DataFrame) -> pd.DataFrame:
    """Alarms per calendar day, split by criticality."""
    frame = events.copy()
    frame["date"] = pd.to_datetime(
        frame["event_timestamp"], errors="coerce"
    ).dt.normalize()
    trend = (
        frame.groupby("date")
        .agg(
            alarms=("alarm_event_id", "size"),
            critical=("severity", lambda s: int((s == "CRITICAL").sum())),
            high=("severity", lambda s: int((s == "HIGH").sum())),
        )
        .reset_index()
    )
    return trend


def hourly_alarm_distribution(events: pd.DataFrame) -> pd.DataFrame:
    """Alarm volume per hour of day, with the per-day average."""
    frame = events.copy()
    frame["hour"] = pd.to_datetime(
        frame["event_timestamp"], errors="coerce"
    ).dt.hour
    # Number of distinct calendar days in the population.
    day_count = (
        pd.to_datetime(frame["event_timestamp"], errors="coerce").dt.date.nunique()
        or 1
    )
    counts = frame["hour"].value_counts().reindex(range(24), fill_value=0)
    return pd.DataFrame(
        {
            "hour": list(range(24)),
            "alarms": counts.to_numpy(dtype=int),
            "average_per_day": [
                round(value / day_count, 2) for value in counts.to_numpy(dtype=int)
            ],
        }
    )


def response_time_trend(compliance: pd.DataFrame) -> pd.DataFrame:
    """Daily median / p95 response time and compliance."""
    frame = compliance.dropna(subset=["acknowledged_at"]).copy()
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "median_response_minutes",
                "p95_response_minutes",
                "on_time_compliance_pct",
                "acknowledged",
            ]
        )
    frame["date"] = pd.to_datetime(frame["event_timestamp"]).dt.normalize()
    trend = (
        frame.groupby("date")
        .agg(
            median_response_minutes=(
                "response_minutes",
                lambda values: round(float(values.median()), 2),
            ),
            p95_response_minutes=(
                "response_minutes",
                lambda values: round(float(values.quantile(0.95)), 2),
            ),
            on_time=("ack_status", lambda values: int((values == "ON_TIME").sum())),
            acknowledged=("response_minutes", "size"),
        )
        .reset_index()
    )
    trend["on_time_compliance_pct"] = [
        pct(on_time, acknowledged)
        for on_time, acknowledged in zip(trend["on_time"], trend["acknowledged"])
    ]
    return trend.drop(columns=["on_time"])


def incident_trends(incidents: pd.DataFrame) -> pd.DataFrame:
    """Daily count of incidents opened and closed."""
    frame = incidents.copy()
    frame["opened_date"] = pd.to_datetime(
        frame["created_at"], errors="coerce"
    ).dt.normalize()
    opened = frame.groupby("opened_date").size().rename("opened")
    closed = (
        frame.dropna(subset=["closed_at"])
        .assign(
            closed_date=lambda df: pd.to_datetime(df["closed_at"]).dt.normalize()
        )
        .groupby("closed_date")
        .size()
        .rename("closed")
    )
    trend = pd.concat([opened, closed], axis=1, sort=False).fillna(0).sort_index()
    trend.index.name = "date"
    return trend.reset_index()


# ---------------------------------------------------------------------------
# Chattering / flood detection
# ---------------------------------------------------------------------------


def detect_chattering(
    events: pd.DataFrame,
    thresholds: config.DetectionThresholds = config.THRESHOLDS,
    definitions: pd.DataFrame | None = None,
    machines: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Find (machine, alarm definition) pairs repeating N times within T minutes.

    This is a configurable synthetic detection rule, not a compliance claim.
    """
    columns = [
        "plant_id",
        "machine_id",
        "machine_name",
        "alarm_definition_id",
        "alarm_name",
        "severity",
        "max_alarms_in_window",
        "episodes",
        "first_episode",
        "last_episode",
    ]
    if events.empty:
        return pd.DataFrame(columns=columns)

    frame = events.copy()
    if definitions is not None:
        frame = frame.merge(
            definitions[["alarm_definition_id", "alarm_name"]],
            on="alarm_definition_id",
            how="left",
            validate="many_to_one",
        )
    if machines is not None:
        frame = _with_machine_context(frame, machines)
    if "plant_id" not in frame.columns:
        frame["plant_id"] = pd.NA
    if "machine_name" not in frame.columns:
        frame["machine_name"] = frame["machine_id"]
    if "alarm_name" not in frame.columns:
        frame["alarm_name"] = frame["alarm_definition_id"]

    window = f"{thresholds.chatter_window_minutes}min"
    rows = []
    frame["event_timestamp"] = pd.to_datetime(
        frame["event_timestamp"], errors="coerce"
    )
    for (machine_id, definition_id), group in frame.sort_values(
        "event_timestamp"
    ).groupby(["machine_id", "alarm_definition_id"]):
        indexed = group.set_index("event_timestamp").sort_index()
        rolling_counts = indexed["alarm_event_id"].rolling(window).count()
        hits = rolling_counts[rolling_counts >= thresholds.chatter_n]
        if hits.empty:
            continue
        episode_ids = (
            hits.index.to_series().diff()
            > pd.Timedelta(minutes=thresholds.chatter_window_minutes)
        ).cumsum()
        rows.append(
            {
                "plant_id": group["plant_id"].iloc[0],
                "machine_id": machine_id,
                "machine_name": group["machine_name"].iloc[0],
                "alarm_definition_id": definition_id,
                "alarm_name": group["alarm_name"].iloc[0],
                "severity": group["severity"].iloc[0],
                "max_alarms_in_window": int(hits.max()),
                "episodes": int(episode_ids.nunique()),
                "first_episode": hits.index.min(),
                "last_episode": hits.index.max(),
            }
        )
    result = pd.DataFrame(rows, columns=columns)
    return result.sort_values(
        ["max_alarms_in_window", "episodes"], ascending=False
    ).reset_index(drop=True)


def detect_floods(
    events: pd.DataFrame,
    thresholds: config.DetectionThresholds = config.THRESHOLDS,
    plants: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Find plant-level windows where alarms per window exceed the threshold."""
    columns = [
        "plant_id",
        "plant_name",
        "window_start",
        "window_end",
        "alarm_count",
        "critical_count",
        "episodes",
    ]
    if events.empty or "plant_id" not in events.columns:
        return pd.DataFrame(columns=columns)

    frame = events.copy()
    frame["event_timestamp"] = pd.to_datetime(
        frame["event_timestamp"], errors="coerce"
    )
    if plants is not None:
        frame = frame.merge(
            plants[["plant_id", "plant_name"]],
            on="plant_id",
            how="left",
            validate="many_to_one",
        )
    if "plant_name" not in frame.columns:
        frame["plant_name"] = frame["plant_id"]

    window = pd.Timedelta(minutes=thresholds.flood_window_minutes)
    rows = []
    for plant_id, group in frame.sort_values("event_timestamp").groupby("plant_id"):
        indexed = group.set_index("event_timestamp").sort_index()
        rolling_counts = indexed["alarm_event_id"].rolling(window).count()
        hits = rolling_counts[rolling_counts >= thresholds.flood_alarm_count]
        if hits.empty:
            continue
        episode_ids = (hits.index.to_series().diff() > window).cumsum()
        for _, episode in hits.groupby(episode_ids):
            window_end = episode.index.max()
            window_start = window_end - window
            in_window = indexed.loc[
                (indexed.index > window_start) & (indexed.index <= window_end)
            ]
            rows.append(
                {
                    "plant_id": plant_id,
                    "plant_name": group["plant_name"].iloc[0],
                    "window_start": window_start,
                    "window_end": window_end,
                    "alarm_count": int(len(in_window)),
                    "critical_count": int(
                        (in_window["severity"] == "CRITICAL").sum()
                    ),
                    "episodes": int(len(episode)),
                }
            )
    return pd.DataFrame(rows, columns=columns).sort_values(
        "alarm_count", ascending=False
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Incidents / corrective actions
# ---------------------------------------------------------------------------


def incident_statistics(
    incidents: pd.DataFrame, actions: pd.DataFrame | None = None
) -> dict[str, object]:
    """Incident counts, lifecycle and resolution time."""
    total = int(len(incidents))
    status_counts = incidents["status"].value_counts().to_dict()
    closed = incidents[incidents["status"] == "CLOSED"].copy()
    resolution_hours = (
        (
            pd.to_datetime(closed["closed_at"], errors="coerce")
            - pd.to_datetime(closed["created_at"], errors="coerce")
        ).dt.total_seconds()
        / 3600
    ).dropna()

    closed_without_verified = 0
    if actions is not None and not actions.empty and not closed.empty:
        verified = actions[
            (actions["status"] == "CLOSED")
            & (actions["verification_status"] == "VERIFIED")
        ]["incident_id"]
        closed_without_verified = int(
            (~closed["incident_id"].isin(verified)).sum()
        )

    return {
        "total_incidents": total,
        "open_incidents": int(status_counts.get("OPEN", 0)),
        "investigating_incidents": int(status_counts.get("INVESTIGATING", 0)),
        "closed_incidents": int(status_counts.get("CLOSED", 0)),
        "closed_pct": pct(len(closed), total),
        "mean_resolution_hours": round(float(resolution_hours.mean()), 2)
        if not resolution_hours.empty
        else 0.0,
        "median_resolution_hours": round(float(resolution_hours.median()), 2)
        if not resolution_hours.empty
        else 0.0,
        "closed_without_verified_action": closed_without_verified,
        "by_severity": {
            severity: int((incidents["severity"] == severity).sum())
            for severity in config.SEVERITIES
        },
        "by_status": {str(key): int(value) for key, value in status_counts.items()},
    }


def corrective_action_statistics(actions: pd.DataFrame) -> dict[str, object]:
    """Corrective-action counts and effectiveness distribution."""
    total = int(len(actions))
    status_counts = actions["status"].value_counts().to_dict()
    verification_counts = actions["verification_status"].value_counts().to_dict()
    effectiveness_counts = actions["effectiveness_status"].value_counts().to_dict()
    closed = actions[actions["status"] == "CLOSED"]
    closure_hours = (
        (
            pd.to_datetime(closed["closed_at"], errors="coerce")
            - pd.to_datetime(closed["created_at"], errors="coerce")
        ).dt.total_seconds()
        / 3600
    ).dropna()

    return {
        "total_actions": total,
        "open_actions": int(status_counts.get("OPEN", 0)),
        "in_progress_actions": int(status_counts.get("IN_PROGRESS", 0)),
        "pending_verification_actions": int(
            status_counts.get("PENDING_VERIFICATION", 0)
        ),
        "closed_actions": int(status_counts.get("CLOSED", 0)),
        "verified_actions": int(verification_counts.get("VERIFIED", 0)),
        "not_verified_actions": int(verification_counts.get("NOT_VERIFIED", 0)),
        "pending_verification": int(
            (actions["verification_status"] == "PENDING").sum()
        ),
        "mean_closure_hours": round(float(closure_hours.mean()), 2)
        if not closure_hours.empty
        else 0.0,
        "by_status": {str(key): int(value) for key, value in status_counts.items()},
        "by_verification": {
            str(key): int(value) for key, value in verification_counts.items()
        },
        "by_effectiveness": {
            str(key): int(value) for key, value in effectiveness_counts.items()
        },
    }


def exception_kpis(exceptions: pd.DataFrame) -> dict[str, object]:
    """Separate genuine anomalies from routine SLA breaches."""
    if exceptions.empty:
        return {
            "genuine_anomalies": 0,
            "routine_sla_breaches": 0,
            "by_type": {},
            "by_severity": {},
        }
    routine = exceptions["is_routine_sla"].astype(bool)
    genuine = exceptions[~routine]
    return {
        "genuine_anomalies": int(len(genuine)),
        "routine_sla_breaches": int(routine.sum()),
        "by_type": {
            str(key): int(value)
            for key, value in genuine["exception_type"].value_counts().items()
        },
        "by_severity": {
            str(key): int(value)
            for key, value in genuine["severity"].value_counts().items()
        },
    }


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Filters:
    """Dashboard / report filter selection."""

    plant_id: str | None = None
    machine_id: str | None = None
    severity: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    def is_empty(self) -> bool:
        return not any(
            (
                self.plant_id,
                self.machine_id,
                self.severity,
                self.start_date,
                self.end_date,
            )
        )


def _date_column(frame: pd.DataFrame, preferred: str | None) -> str | None:
    if preferred and preferred in frame.columns:
        return preferred
    for candidate in (
        "event_timestamp",
        "created_at",
        "acknowledged_at",
        "ack_timestamp",
    ):
        if candidate in frame.columns:
            return candidate
    return None


def apply_filters(
    frame: pd.DataFrame,
    filters: Filters,
    date_column: str | None = None,
) -> pd.DataFrame:
    """Apply plant, machine, severity and date filters consistently.

    Columns that do not exist are ignored, but severity and date filters are
    only applied where the column exists; callers pass enriched frames so the
    same predicate works across alarms, acknowledgements, incidents, actions
    and exceptions.
    """
    result = frame
    if filters.plant_id and "plant_id" in result.columns:
        result = result[result["plant_id"].astype(str) == filters.plant_id]
    if filters.machine_id and "machine_id" in result.columns:
        result = result[result["machine_id"].astype(str) == filters.machine_id]
    if filters.severity and "severity" in result.columns:
        result = result[result["severity"].astype(str) == filters.severity]

    column = _date_column(result, date_column)
    if column and (filters.start_date or filters.end_date):
        values = pd.to_datetime(result[column], errors="coerce")
        if filters.start_date:
            result = result[
                values >= pd.Timestamp(filters.start_date)
            ]
            values = pd.to_datetime(result[column], errors="coerce")
        if filters.end_date:
            end = pd.Timestamp(filters.end_date) + pd.Timedelta(days=1)
            result = result[values < end]
    return result


def unmapped_context_count(exceptions: pd.DataFrame) -> int:
    """Rows that could not be attributed to a plant or machine."""
    if exceptions.empty:
        return 0
    mask = exceptions["plant_id"].isna() | exceptions["machine_id"].isna()
    return int(mask.sum())
