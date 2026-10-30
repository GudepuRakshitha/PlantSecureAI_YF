
import pandas as pd
import numpy as np
from pathlib import Path

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022
rng = np.random.default_rng(SEED)

DATA = Path("data")

# Read existing datasets
plants = pd.read_csv(DATA / "plants.csv")
machines = pd.read_csv(DATA / "machines.csv")
events = pd.read_csv(DATA / "alarm_events.csv")

events["event_timestamp"] = pd.to_datetime(
    events["event_timestamp"]
)

# --------------------------------------------------
# 1. GENERATE OPERATOR SHIFTS
# --------------------------------------------------

shifts = []

for plant in plants["plant_id"]:
    for day in pd.date_range("2026-10-01", "2026-10-30"):
        for shift_no, (start_hour, end_hour) in enumerate(
            [(0, 8), (8, 16), (16, 24)], start=1
        ):
            shifts.append({
                "shift_id": f"SHIFT-{plant}-{day:%Y%m%d}-{shift_no}",
                "plant_id": plant,
                "operator_id": f"OP-{plant}-{shift_no:02d}",
                "shift_start": day + pd.Timedelta(hours=start_hour),
                "shift_end": day + pd.Timedelta(hours=end_hour)
            })

shifts_df = pd.DataFrame(shifts)
shifts_df.to_csv(DATA / "operator_shifts.csv", index=False)

# --------------------------------------------------
# MAP EVENTS TO PLANTS AND OPERATOR SHIFTS
# --------------------------------------------------

events = events.merge(
    machines[["machine_id", "plant_id"]],
    on="machine_id",
    validate="many_to_one"
)

events["shift_date"] = events["event_timestamp"].dt.strftime(
    "%Y%m%d"
)

events["shift_no"] = (
    events["event_timestamp"].dt.hour // 8
) + 1

events["shift_id"] = (
    "SHIFT-" + events["plant_id"] + "-"
    + events["shift_date"] + "-"
    + events["shift_no"].astype(str)
)

# --------------------------------------------------
# 2. GENERATE ACKNOWLEDGEMENTS
# --------------------------------------------------

acknowledgements = []

for row in events.itertuples(index=False):

    # 90% of alarms receive acknowledgement
    if rng.random() < 0.90:

        # 80% on-time, 20% delayed
        if rng.random() < 0.80:
            delay_minutes = int(rng.integers(1, 6))
        else:
            delay_minutes = int(rng.integers(6, 16))

        ack_time = row.event_timestamp + pd.Timedelta(
            minutes=delay_minutes
        )

        acknowledgements.append({
            "acknowledgement_id": f"ACK-{row.alarm_event_id}-01",
            "alarm_event_id": row.alarm_event_id,
            "operator_id": f"OP-{row.plant_id}-{row.shift_no:02d}",
            "shift_id": row.shift_id,
            "ack_timestamp": ack_time,
            "response_minutes": delay_minutes,
            "status": (
                "DELAYED" if delay_minutes > 5 else "ON_TIME"
            )
        })

acks_df = pd.DataFrame(acknowledgements)

acks_df.to_csv(
    DATA / "acknowledgements.csv",
    index=False
)

# --------------------------------------------------
# 3. GENERATE INCIDENTS
# --------------------------------------------------

eligible = events[
    events["severity"].isin(["HIGH", "CRITICAL"])
    & (events["machine_state"] == "RUNNING")
]

# Select approximately 2% of eligible events
incident_count = max(
    1,
    int(len(eligible) * 0.02)
)

selected = eligible.sample(
    n=min(incident_count, len(eligible)),
    random_state=SEED
)

incidents = []

for number, row in enumerate(
    selected.itertuples(index=False), start=1
):
    incidents.append({
        "incident_id": f"INC-2026-{number:06d}",
        "alarm_event_id": row.alarm_event_id,
        "machine_id": row.machine_id,
        "plant_id": row.plant_id,
        "incident_type": "UNSAFE_MACHINE_RUNNING",
        "severity": row.severity,
        "created_at": row.event_timestamp,
        "status": "OPEN"
    })

incidents_df = pd.DataFrame(incidents)

incidents_df.to_csv(
    DATA / "incidents.csv",
    index=False
)

# --------------------------------------------------
# 4. GENERATE CORRECTIVE ACTIONS
# --------------------------------------------------

actions = []

for row in incidents_df.itertuples(index=False):

    actions.append({
        "action_id": f"ACT-{row.incident_id}-01",
        "incident_id": row.incident_id,
        "action_description": (
            "Inspect machine and verify safety interlock"
        ),
        "assigned_to": "MAINTENANCE_TEAM",
        "created_at": (
            row.created_at + pd.Timedelta(minutes=10)
        ),
        "closed_at": (
            row.created_at + pd.Timedelta(hours=2)
        ),
        "status": "CLOSED",
        "verification_status": "VERIFIED"
    })

actions_df = pd.DataFrame(actions)

actions_df.to_csv(
    DATA / "corrective_actions.csv",
    index=False
)

# --------------------------------------------------
# 5. GENERATION SUMMARY
# --------------------------------------------------

print("\nTRANSACTION DATA GENERATED SUCCESSFULLY!")
print("Operator shifts:", len(shifts_df))
print("Acknowledgements:", len(acks_df))
print("Incidents:", len(incidents_df))
print("Corrective actions:", len(actions_df))

if not acks_df.empty:
    on_time = (acks_df["response_minutes"] <= 5).sum()
    delayed = (acks_df["response_minutes"] > 5).sum()

    print("\nAcknowledgement performance:")
    print("On-time:", on_time)
    print("Delayed:", delayed)
    print(
        "On-time percentage:",
        round(on_time / len(acks_df) * 100, 2),
        "%"
    )
    print(
        "Delayed percentage:",
        round(delayed / len(acks_df) * 100, 2),
        "%"
    )

print("\nAll transaction CSV files saved!")
