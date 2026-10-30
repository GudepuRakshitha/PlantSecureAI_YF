"""Build the injected scenario population and the ground-truth labels.

Five genuine anomalies (EDGE-001..005) and three negative controls
(NC-001..003).  Scenario records are written to ``data/scenarios/`` and are
never mixed into the baseline files.

Design rules enforced here:
* scenario rows carry their own ``case_id`` column;
* injected rows use new primary keys (no baseline collisions, no duplicate
  primary keys leaking into the baseline contract);
* enum values stay inside the baseline vocabulary, so a detector cannot win by
  string-matching a magic status;
* negative controls are valid records that a correct detector must not flag.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, schema

DATASET_END = pd.Timestamp(config.DATASET_END)


def _new_event_row(
    base: pd.Series, event_id: str, timestamp: pd.Timestamp, case_id: str
) -> dict[str, object]:
    row = base.to_dict()
    row.update(
        {
            "alarm_event_id": event_id,
            "event_timestamp": timestamp,
            "acknowledged": False,
            "acknowledged_at": pd.NaT,
            "cleared_at": pd.NaT,
            "alarm_status": "UNACKNOWLEDGED",
            "state_transition": "ACTIVE>UNACKNOWLEDGED",
            "case_id": case_id,
        }
    )
    return row


def _shift_fields(plant_id: str, timestamp: pd.Timestamp) -> tuple[str, str]:
    shift_no = timestamp.hour // 8 + 1
    return (
        f"SHIFT-{plant_id}-{timestamp:%Y%m%d}-{shift_no}",
        f"OP-{plant_id}-{shift_no:02d}",
    )


def build_scenarios(baseline: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Return the scenario tables and ground truth for a baseline dataset."""
    events = baseline["alarm_events"].copy()
    machines = baseline["machines"]
    acknowledgements = baseline["acknowledgements"]
    incidents = baseline["incidents"]
    actions = baseline["corrective_actions"]
    interlocks = baseline["interlocks"]

    # Alarm events are normalised (machine -> plant); scenario builders need
    # the plant for shift attribution.
    events = events.merge(
        machines[["machine_id", "plant_id"]],
        on="machine_id",
        validate="many_to_one",
    )

    acknowledged_ids = set(acknowledgements["alarm_event_id"])
    unacknowledged = events[
        ~events["alarm_event_id"].isin(acknowledged_ids)
    ].sort_values("event_timestamp")

    scenario_events: list[dict[str, object]] = []
    scenario_acks: list[dict[str, object]] = []
    scenario_interlocks: list[dict[str, object]] = []
    scenario_incidents: list[dict[str, object]] = []
    scenario_actions: list[dict[str, object]] = []
    ground_truth: list[dict[str, object]] = []

    def truth(
        case_id: str,
        scenario_type: str,
        label: str,
        entity: str,
        record_id: str,
        is_anomaly: bool,
        description: str,
    ) -> None:
        ground_truth.append(
            {
                "case_id": case_id,
                "scenario_type": scenario_type,
                "expected_label": label,
                "entity": entity,
                "record_id": record_id,
                "is_anomaly": is_anomaly,
                "description": description,
            }
        )

    # ------------------------------------------------------------------
    # EDGE-001: acknowledgement timestamp before its alarm
    # ------------------------------------------------------------------
    edge1_event = unacknowledged.iloc[0]
    ack_time = pd.Timestamp(edge1_event["event_timestamp"]) - pd.Timedelta(minutes=2)
    shift_id, operator_id = _shift_fields(edge1_event["plant_id"], ack_time)
    edge1_ack_id = "ACK-EDGE-001-01"
    scenario_acks.append(
        {
            "acknowledgement_id": edge1_ack_id,
            "alarm_event_id": edge1_event["alarm_event_id"],
            "operator_id": operator_id,
            "shift_id": shift_id,
            "ack_timestamp": ack_time,
            "response_minutes": -2.0,
            "status": "DELAYED",
            "case_id": "EDGE-001",
        }
    )
    truth(
        "EDGE-001",
        "ACK_BEFORE_ALARM",
        "ACK_BEFORE_ALARM",
        "Acknowledgement",
        edge1_ack_id,
        True,
        "Acknowledgement is logged two minutes before its alarm event.",
    )

    # ------------------------------------------------------------------
    # EDGE-002: interlock current state contradicts required safe state
    # ------------------------------------------------------------------
    edge2_id = "INT-EDGE-002"
    scenario_interlocks.append(
        {
            "interlock_id": edge2_id,
            "machine_id": "MCH-001",
            "interlock_name": "Injected state fault",
            "required_state": "CLOSED",
            "current_state": "OPEN",
            "case_id": "EDGE-002",
        }
    )
    truth(
        "EDGE-002",
        "IMPOSSIBLE_INTERLOCK_STATE",
        "INTERLOCK_STATE_MISMATCH",
        "Interlock",
        edge2_id,
        True,
        "Current interlock state contradicts the required safe state.",
    )

    # ------------------------------------------------------------------
    # EDGE-003: incident raised from a non-qualifying alarm context
    # ------------------------------------------------------------------
    context = events[
        (events["severity"] == "LOW") & (events["machine_state"] == "STOPPED")
    ].iloc[0]
    edge3_id = "INC-EDGE-003"
    scenario_incidents.append(
        {
            "incident_id": edge3_id,
            "alarm_event_id": context["alarm_event_id"],
            "machine_id": context["machine_id"],
            "plant_id": context["plant_id"],
            "incident_type": "UNSAFE_MACHINE_RUNNING",
            "severity": "LOW",
            "created_at": context["event_timestamp"],
            "closed_at": pd.NaT,
            "status": "OPEN",
            "case_id": "EDGE-003",
        }
    )
    truth(
        "EDGE-003",
        "INCIDENT_WITHOUT_TRIGGER",
        "INCIDENT_WITHOUT_VALID_TRIGGER",
        "Incident",
        edge3_id,
        True,
        "Incident is linked to a LOW severity STOPPED alarm, not a qualifying trigger.",
    )

    # ------------------------------------------------------------------
    # EDGE-004: duplicate alarm event primary key (replay)
    # ------------------------------------------------------------------
    flood_base = unacknowledged.iloc[1]
    edge4_id = "ALM-EDGE-004-01"
    for _ in range(2):
        scenario_events.append(
            _new_event_row(
                flood_base,
                event_id=edge4_id,
                timestamp=pd.Timestamp(flood_base["event_timestamp"]),
                case_id="EDGE-004",
            )
        )
    truth(
        "EDGE-004",
        "ALARM_FLOOD_DUPLICATE_REPLAY",
        "DUPLICATE_ALARM_REPLAY",
        "AlarmEvent",
        edge4_id,
        True,
        "The same alarm event primary key is replayed twice.",
    )

    # ------------------------------------------------------------------
    # EDGE-005: action closed without verification on an open incident
    # ------------------------------------------------------------------
    open_incident = incidents[
        (incidents["status"] != "CLOSED")
        & (incidents["created_at"] < DATASET_END - pd.Timedelta(hours=4))
    ].iloc[0]
    edge5_created = pd.Timestamp(open_incident["created_at"]) + pd.Timedelta(minutes=30)
    edge5_id = "ACT-EDGE-005"
    scenario_actions.append(
        {
            "action_id": edge5_id,
            "incident_id": open_incident["incident_id"],
            "action_description": "Injected closed-without-verification action",
            "assigned_to": "MAINTENANCE_TEAM",
            "created_at": edge5_created,
            "closed_at": edge5_created + pd.Timedelta(hours=2),
            "verified_at": pd.NaT,
            "status": "CLOSED",
            "verification_status": "NOT_VERIFIED",
            "effectiveness_status": "PENDING",
            "case_id": "EDGE-005",
        }
    )
    truth(
        "EDGE-005",
        "CLOSED_WITHOUT_VERIFICATION",
        "CLOSED_WITHOUT_VERIFICATION",
        "CorrectiveAction",
        edge5_id,
        True,
        "Action is CLOSED but verification_status is NOT_VERIFIED.",
    )

    # ------------------------------------------------------------------
    # NC-001: acknowledgement exactly at the 5-minute limit (valid)
    # ------------------------------------------------------------------
    nc1_event = unacknowledged.iloc[2]
    nc1_ack_time = pd.Timestamp(nc1_event["event_timestamp"]) + pd.Timedelta(
        minutes=config.ACK_LIMIT_MINUTES
    )
    shift_id, operator_id = _shift_fields(nc1_event["plant_id"], nc1_ack_time)
    nc1_id = "ACK-NC-001-01"
    scenario_acks.append(
        {
            "acknowledgement_id": nc1_id,
            "alarm_event_id": nc1_event["alarm_event_id"],
            "operator_id": operator_id,
            "shift_id": shift_id,
            "ack_timestamp": nc1_ack_time,
            "response_minutes": float(config.ACK_LIMIT_MINUTES),
            "status": "ON_TIME",
            "case_id": "NC-001",
        }
    )
    truth(
        "NC-001",
        "NEGATIVE_CONTROL_ACK_AT_LIMIT",
        "NO_ANOMALY",
        "Acknowledgement",
        nc1_id,
        False,
        "Acknowledgement exactly at the configured limit is on time.",
    )

    # ------------------------------------------------------------------
    # NC-002: closed incident with a verified action (valid lifecycle)
    # ------------------------------------------------------------------
    used_event_ids = set(incidents["alarm_event_id"])
    nc2_events = events[
        events["severity"].isin(["HIGH", "CRITICAL"])
        & (events["machine_state"] == "RUNNING")
        & (events["event_timestamp"] < DATASET_END - pd.Timedelta(hours=25))
    ]
    nc2_events = nc2_events[~nc2_events["alarm_event_id"].isin(used_event_ids)]
    if nc2_events.empty:
        raise ValueError("No eligible baseline event available for NC-002.")
    nc2_event = nc2_events.iloc[0]
    nc2_created = pd.Timestamp(nc2_event["event_timestamp"])
    nc2_closed = nc2_created + pd.Timedelta(hours=24)
    nc2_id = "INC-NC-002"
    scenario_incidents.append(
        {
            "incident_id": nc2_id,
            "alarm_event_id": nc2_event["alarm_event_id"],
            "machine_id": nc2_event["machine_id"],
            "plant_id": nc2_event["plant_id"],
            "incident_type": "UNSAFE_MACHINE_RUNNING",
            "severity": nc2_event["severity"],
            "created_at": nc2_created,
            "closed_at": nc2_closed,
            "status": "CLOSED",
            "case_id": "NC-002",
        }
    )
    scenario_actions.append(
        {
            "action_id": "ACT-NC-002",
            "incident_id": nc2_id,
            "action_description": "Negative control: verified corrective action",
            "assigned_to": "SAFETY_OFFICER",
            "created_at": nc2_created + pd.Timedelta(minutes=20),
            "closed_at": nc2_closed - pd.Timedelta(minutes=10),
            "verified_at": nc2_closed,
            "status": "CLOSED",
            "verification_status": "VERIFIED",
            "effectiveness_status": "EFFECTIVE",
            "case_id": "NC-002",
        }
    )
    truth(
        "NC-002",
        "NEGATIVE_CONTROL_CONSISTENT_LIFECYCLE",
        "NO_ANOMALY",
        "Incident",
        nc2_id,
        False,
        "Closed incident with a verified, effective corrective action is valid.",
    )

    # ------------------------------------------------------------------
    # NC-003: two alarms close together but with distinct identities
    # ------------------------------------------------------------------
    nc3_base = unacknowledged.iloc[3]
    nc3_time = pd.Timestamp(nc3_base["event_timestamp"])
    nc3_ids = ("ALM-NC-003-01", "ALM-NC-003-02")
    for offset_minutes, event_id in zip((0, 3), nc3_ids):
        scenario_events.append(
            _new_event_row(
                nc3_base,
                event_id=event_id,
                timestamp=nc3_time + pd.Timedelta(minutes=offset_minutes),
                case_id="NC-003",
            )
        )
    for event_id in nc3_ids:
        truth(
            "NC-003",
            "NEGATIVE_CONTROL_NEAR_DUPLICATE",
            "NO_ANOMALY",
            "AlarmEvent",
            event_id,
            False,
            "Two distinct alarms three minutes apart are not a duplicate replay.",
        )

    # ------------------------------------------------------------------
    # Assemble frames
    # ------------------------------------------------------------------
    def frame(records: list[dict[str, object]], spec: schema.TableSpec) -> pd.DataFrame:
        columns = list(spec.columns) + ["case_id"]
        if not records:
            return pd.DataFrame(columns=columns)
        return pd.DataFrame(records)[columns]

    scenario = {
        "alarm_events": frame(scenario_events, schema.ALARM_EVENTS),
        "acknowledgements": frame(scenario_acks, schema.ACKNOWLEDGEMENTS),
        "interlocks": frame(scenario_interlocks, schema.INTERLOCKS),
        "incidents": frame(scenario_incidents, schema.INCIDENTS),
        "corrective_actions": frame(scenario_actions, schema.CORRECTIVE_ACTIONS),
        "ground_truth": pd.DataFrame(
            ground_truth, columns=list(schema.GROUND_TRUTH.columns)
        ),
    }
    return scenario


def write_scenarios(
    scenario: dict[str, pd.DataFrame], scenario_dir: Path = config.SCENARIO_DIR
) -> None:
    scenario_dir.mkdir(parents=True, exist_ok=True)
    for name, filename in schema.SCENARIO_FILENAMES.items():
        scenario[name].to_csv(
            scenario_dir / filename,
            index=False,
            date_format="%Y-%m-%d %H:%M:%S",
        )
    scenario["ground_truth"].to_csv(scenario_dir / "ground_truth.csv", index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    args = parser.parse_args(argv)

    baseline = {}
    for spec in schema.BASELINE_TABLES:
        frame = pd.read_csv(args.data_dir / spec.filename)
        for column in spec.datetime_columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
        baseline[spec.name] = frame

    scenario = build_scenarios(baseline)
    write_scenarios(scenario, args.data_dir / "scenarios")

    print("\nEDGE CASES CREATED SUCCESSFULLY!")
    for name in schema.SCENARIO_TABLES:
        print(f"  scenario {name}: {len(scenario[name.name])} rows")
    print("  ground truth labels:", len(scenario["ground_truth"]))
    print("  anomalies:", int(scenario["ground_truth"]["is_anomaly"].sum()))
    print("  negative controls:", int((~scenario["ground_truth"]["is_anomaly"]).sum()))
    print(f"Output folder: {args.data_dir / 'scenarios'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
