"""Generate transactional data: shifts, acknowledgements, incidents, actions,
and finalise the alarm-event lifecycle.

Draw order for the acknowledgement sample is preserved from the original
implementation, so the same seed still yields 45,031 acknowledgements and the
same on-time/late split.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, schema

ACTION_TEMPLATES = (
    "Inspect machine and verify safety interlock",
    "Replace faulty sensor and re-test interlock",
    "Review operator response and update alarm rationalisation",
    "Re-train shift crew on alarm handling procedure",
    "Service the guarding circuit and document the result",
)
ASSIGNEES = ("MAINTENANCE_TEAM", "SHIFT_ENGINEER", "SAFETY_OFFICER")

DATA_END = pd.Timestamp(config.DATASET_END)


def build_shifts(plants: pd.DataFrame) -> pd.DataFrame:
    """Three 8-hour shifts per plant for every day of the dataset."""
    shifts = []
    for plant_id in plants["plant_id"]:
        for day in pd.date_range("2026-10-01", "2026-10-31", freq="D"):
            for shift_no, (start_hour, end_hour) in enumerate(
                [(0, 8), (8, 16), (16, 24)], start=1
            ):
                shifts.append(
                    {
                        "shift_id": f"SHIFT-{plant_id}-{day:%Y%m%d}-{shift_no}",
                        "plant_id": plant_id,
                        "operator_id": f"OP-{plant_id}-{shift_no:02d}",
                        "shift_start": day + pd.Timedelta(hours=start_hour),
                        "shift_end": day + pd.Timedelta(hours=end_hour),
                    }
                )
    return pd.DataFrame(shifts)


def _shift_for(
    ack_time: pd.Timestamp, plant_id: str, shift_lookup: dict[tuple[str, str, int], tuple[str, str]]
) -> tuple[str, str]:
    """Return ``(shift_id, operator_id)`` owning an acknowledgement timestamp.

    Attribute the acknowledgement to the shift during which it was logged,
    not the shift of the alarm.  This removes the original off-by-boundary
    misattribution bug.
    """
    shift_no = ack_time.hour // 8 + 1
    key = (plant_id, ack_time.strftime("%Y%m%d"), shift_no)
    return shift_lookup[key]


def build_acknowledgements(
    events: pd.DataFrame,
    shifts: pd.DataFrame,
    seed: int = config.SEED,
) -> pd.DataFrame:
    """Sample acknowledgements with the original RNG draw order."""
    rng = np.random.default_rng(seed)
    shift_lookup = {
        (row.plant_id, row.shift_start.strftime("%Y%m%d"), row.shift_start.hour // 8 + 1): (
            row.shift_id,
            row.operator_id,
        )
        for row in shifts.itertuples(index=False)
    }

    acknowledgements: list[dict[str, object]] = []
    for row in events.itertuples(index=False):
        if rng.random() < config.ACK_PROBABILITY:
            if rng.random() < config.ON_TIME_PROBABILITY:
                delay_minutes = int(rng.integers(1, config.ON_TIME_MAX_MINUTES + 1))
            else:
                delay_minutes = int(
                    rng.integers(config.LATE_MIN_MINUTES, config.LATE_MAX_MINUTES + 1)
                )

            ack_time = pd.Timestamp(row.event_timestamp) + pd.Timedelta(
                minutes=delay_minutes
            )
            shift_id, operator_id = _shift_for(ack_time, row.plant_id, shift_lookup)
            acknowledgements.append(
                {
                    "acknowledgement_id": f"ACK-{row.alarm_event_id}-01",
                    "alarm_event_id": row.alarm_event_id,
                    "operator_id": operator_id,
                    "shift_id": shift_id,
                    "ack_timestamp": ack_time,
                    "response_minutes": delay_minutes,
                    "status": (
                        "DELAYED"
                        if delay_minutes > config.ACK_LIMIT_MINUTES
                        else "ON_TIME"
                    ),
                }
            )

    return pd.DataFrame(acknowledgements, columns=list(schema.ACKNOWLEDGEMENTS.columns))


def apply_event_lifecycle(
    events: pd.DataFrame,
    acknowledgements: pd.DataFrame,
    seed: int = config.LIFECYCLE_SEED,
) -> pd.DataFrame:
    """Add acknowledged/cleared state derived from the acknowledgement table."""
    events = events.copy()
    ack_times = acknowledgements.set_index("alarm_event_id")["ack_timestamp"]
    events["acknowledged_at"] = events["alarm_event_id"].map(ack_times)
    events["acknowledged"] = events["acknowledged_at"].notna()

    rng = np.random.default_rng(seed)
    # Alarms clear between 5 minutes and 7 days after acknowledgement.  A
    # multi-day tail is realistic for intermittent process alarms and, more
    # importantly, leaves recently acknowledged alarms still ACTIVE at the end
    # of the observation window so the ACKNOWLEDGED state actually occurs.
    clear_minutes = rng.integers(5, 7 * 24 * 60, size=len(events))
    cleared_at = events["acknowledged_at"] + pd.to_timedelta(clear_minutes, unit="m")
    # An alarm still active at the end of the window has no clear timestamp.
    cleared_at = cleared_at.where(cleared_at <= DATA_END)
    events["cleared_at"] = cleared_at

    events["alarm_status"] = np.select(
        [events["acknowledged_at"].isna(), events["cleared_at"].notna()],
        ["UNACKNOWLEDGED", "CLEARED"],
        default="ACKNOWLEDGED",
    )
    events["state_transition"] = np.select(
        [events["acknowledged_at"].isna(), events["cleared_at"].notna()],
        ["ACTIVE>UNACKNOWLEDGED", "ACTIVE>ACKNOWLEDGED>CLEARED"],
        default="ACTIVE>ACKNOWLEDGED",
    )
    events["acknowledged"] = events["acknowledged"].astype(bool)
    return events[list(schema.ALARM_EVENTS.columns)]


def build_incidents(
    events: pd.DataFrame,
    seed: int = config.SEED,
    lifecycle_seed: int = config.INCIDENT_LIFECYCLE_SEED,
) -> pd.DataFrame:
    """Select ~2% of qualifying alarms as incidents with a realistic lifecycle."""
    eligible = events[
        events["severity"].isin(["HIGH", "CRITICAL"])
        & (events["machine_state"] == "RUNNING")
    ]
    incident_count = max(1, int(len(eligible) * 0.02))
    selected = eligible.sample(
        n=min(incident_count, len(eligible)), random_state=seed
    ).sort_values("event_timestamp")

    rng = np.random.default_rng(lifecycle_seed)
    records = []
    for number, row in enumerate(selected.itertuples(index=False), start=1):
        created_at = pd.Timestamp(row.event_timestamp)
        draw = rng.random()
        if draw < 0.35:
            status = "OPEN"
        elif draw < 0.65:
            status = "INVESTIGATING"
        else:
            status = "CLOSED"

        closed_at = pd.NaT
        if status == "CLOSED":
            hours = int(rng.integers(4, 121))
            candidate = created_at + pd.Timedelta(hours=hours)
            if candidate <= DATA_END - pd.Timedelta(hours=1):
                closed_at = candidate
            else:
                # Too recent to have been closed inside the observed window.
                status = "OPEN"

        records.append(
            {
                "incident_id": f"INC-2026-{number:06d}",
                "alarm_event_id": row.alarm_event_id,
                "machine_id": row.machine_id,
                "plant_id": row.plant_id,
                "incident_type": "UNSAFE_MACHINE_RUNNING",
                "severity": row.severity,
                "created_at": created_at,
                "closed_at": closed_at,
                "status": status,
            }
        )

    return pd.DataFrame(records, columns=list(schema.INCIDENTS.columns))


def build_actions(
    incidents: pd.DataFrame,
    seed: int = config.ACTION_LIFECYCLE_SEED,
) -> pd.DataFrame:
    """One corrective action per incident, lifecycle-consistent with its incident."""
    rng = np.random.default_rng(seed)
    records = []
    for row in incidents.itertuples(index=False):
        created_at = pd.Timestamp(row.created_at) + pd.Timedelta(
            minutes=int(rng.integers(10, 61))
        )
        closed_at = pd.NaT
        verified_at = pd.NaT
        effectiveness = "PENDING"

        if row.status == "CLOSED":
            # Closed incidents must have a closed and verified action.
            closed_at = min(
                pd.Timestamp(row.closed_at) - pd.Timedelta(minutes=int(rng.integers(0, 121))),
                DATA_END,
            )
            closed_at = max(closed_at, created_at)
            verified_at = closed_at + pd.Timedelta(minutes=int(rng.integers(0, 61)))
            verified_at = min(verified_at, DATA_END)
            status = "CLOSED"
            verification = "VERIFIED"
            effectiveness = rng.choice(
                ["EFFECTIVE", "PARTIALLY_EFFECTIVE", "NOT_EFFECTIVE"],
                p=[0.7, 0.2, 0.1],
            )
        else:
            draw = rng.random()
            if draw < 0.2:
                status = "OPEN"
            elif draw < 0.6:
                status = "IN_PROGRESS"
            else:
                status = "PENDING_VERIFICATION"
            verification = "PENDING"

        records.append(
            {
                "action_id": f"ACT-{row.incident_id}-01",
                "incident_id": row.incident_id,
                "action_description": rng.choice(ACTION_TEMPLATES),
                "assigned_to": rng.choice(ASSIGNEES),
                "created_at": created_at,
                "closed_at": closed_at,
                "verified_at": verified_at,
                "status": status,
                "verification_status": verification,
                "effectiveness_status": str(effectiveness),
            }
        )

    return pd.DataFrame(records, columns=list(schema.CORRECTIVE_ACTIONS.columns))


def build_transactions(
    plants: pd.DataFrame,
    machines: pd.DataFrame,
    events: pd.DataFrame,
    seed: int = config.SEED,
) -> dict[str, pd.DataFrame]:
    """Build every transaction table and the finalised alarm-event table."""
    shifts = build_shifts(plants)

    event_plant = events.merge(
        machines[["machine_id", "plant_id"]], on="machine_id", validate="many_to_one"
    )
    acknowledgements = build_acknowledgements(event_plant, shifts, seed)
    events_with_lifecycle = apply_event_lifecycle(events, acknowledgements)
    incidents = build_incidents(event_plant, seed)
    actions = build_actions(incidents)

    return {
        "operator_shifts": shifts,
        "acknowledgements": acknowledgements,
        "incidents": incidents,
        "corrective_actions": actions,
        "alarm_events": events_with_lifecycle,
    }


def write_transactions(
    transactions: dict[str, pd.DataFrame], data_dir: Path = config.DATA_DIR
) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in transactions.items():
        spec = schema.TABLES_BY_NAME[name]
        frame.to_csv(
            data_dir / spec.filename,
            index=False,
            date_format="%Y-%m-%d %H:%M:%S",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--seed", type=int, default=config.SEED)
    args = parser.parse_args(argv)

    plants = pd.read_csv(args.data_dir / schema.PLANTS.filename)
    machines = pd.read_csv(args.data_dir / schema.MACHINES.filename)
    events = pd.read_csv(
        args.data_dir / schema.ALARM_EVENTS.filename,
        parse_dates=["event_timestamp"],
    )
    transactions = build_transactions(plants, machines, events, args.seed)
    write_transactions(transactions, args.data_dir)

    acks = transactions["acknowledgements"]
    print("\nTRANSACTION DATA GENERATED SUCCESSFULLY!")
    print("Operator shifts:", len(transactions["operator_shifts"]))
    print("Acknowledgements:", len(acks))
    print("Incidents:", len(transactions["incidents"]))
    print("Corrective actions:", len(transactions["corrective_actions"]))
    print("Alarm statuses:", transactions["alarm_events"]["alarm_status"].value_counts().to_dict())
    print("Incident statuses:", transactions["incidents"]["status"].value_counts().to_dict())
    print("Action statuses:", transactions["corrective_actions"]["status"].value_counts().to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
