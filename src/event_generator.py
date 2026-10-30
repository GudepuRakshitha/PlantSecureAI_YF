
import pandas as pd
import numpy as np
from pathlib import Path

SEED = 20261022
rng = np.random.default_rng(SEED)

DATA_DIR = Path("data")

# Read previously generated master data
machines = pd.read_csv(DATA_DIR / "machines.csv")
alarms = pd.read_csv(DATA_DIR / "alarm_definitions.csv")

TOTAL_EVENTS = 50000

# Generate alarm timestamps over 30 days
start_date = pd.Timestamp("2026-10-01")
seconds = rng.integers(0, 30 * 24 * 60 * 60, TOTAL_EVENTS)

timestamps = (
    start_date + pd.to_timedelta(seconds, unit="s")
)

events = []

for i in range(TOTAL_EVENTS):

    alarm = alarms.iloc[rng.integers(0, len(alarms))]
    machine_id = alarm["machine_id"]

    event_time = timestamps[i]

    events.append({
        "alarm_event_id": f"ALM-{machine_id}-{i+1:06d}",
        "machine_id": machine_id,
        "alarm_definition_id": alarm["alarm_definition_id"],
        "severity": alarm["severity"],
        "event_timestamp": event_time,
        "machine_state": rng.choice(
            ["RUNNING", "STOPPED", "WARNING"]
        ),
        "alarm_status": "ACTIVE",
        "issue_type": "NONE"
    })

events_df = pd.DataFrame(events)

# Preserve chronological event ordering
events_df = events_df.sort_values(
    "event_timestamp"
).reset_index(drop=True)

events_df.to_csv(
    DATA_DIR / "alarm_events.csv",
    index=False
)

print("ALARM EVENTS GENERATED SUCCESSFULLY!")
print("Total alarm events:", len(events_df))
print("Unique machines:", events_df["machine_id"].nunique())
print("Start date:", events_df["event_timestamp"].min())
print("End date:", events_df["event_timestamp"].max())
print("Output: data/alarm_events.csv")
