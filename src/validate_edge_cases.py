
import pandas as pd
from pathlib import Path

DATA = Path("data")
SCENARIOS = DATA / "scenarios"

truth = pd.read_csv(SCENARIOS / "ground_truth.csv")
events = pd.read_csv(DATA / "alarm_events.csv")
interlocks = pd.read_csv(SCENARIOS / "injected_interlocks.csv")
acks = pd.read_csv(SCENARIOS / "injected_acknowledgements.csv")
incidents = pd.read_csv(SCENARIOS / "injected_incidents.csv")
actions = pd.read_csv(SCENARIOS / "injected_corrective_actions.csv")
replays = pd.read_csv(SCENARIOS / "injected_alarm_events.csv")

checks = []

# 1. Acknowledgement before alarm
event_times = events.set_index("alarm_event_id")["event_timestamp"]
ack = acks.iloc[0]
alarm_time = pd.to_datetime(event_times[ack["alarm_event_id"]])
ack_time = pd.to_datetime(ack["ack_timestamp"])

checks.append((
    "Acknowledgement before alarm",
    ack_time < alarm_time
))

# 2. Interlock state mismatch
interlock = interlocks.iloc[0]
checks.append((
    "Impossible interlock state",
    interlock["current_state"] != interlock["required_state"]
))

# 3. Incident without qualifying context
incident = incidents.iloc[0]
source_event = events[
    events["alarm_event_id"] == incident["alarm_event_id"]
].iloc[0]

checks.append((
    "Incident without triggering context",
    source_event["severity"] == "LOW"
    and source_event["machine_state"] == "STOPPED"
))

# 4. Duplicate replay
checks.append((
    "Alarm flood / duplicate replay",
    replays["alarm_event_id"].nunique() == 1
    and len(replays) == 3
))

# 5. Closed action without verification
action = actions.iloc[0]
checks.append((
    "Closed without verification",
    action["status"] == "CLOSED"
    and action["verification_status"] != "VERIFIED"
))

# Compare scenario count with ground-truth labels
checks.append((
    "Five ground-truth labels",
    len(truth) == 5
))

print("\n========== EDGE CASE VALIDATION ==========\n")

passed = 0

for name, result in checks:
    status = "PASS" if result else "FAIL"
    print(f"{status}: {name}")
    if result:
        passed += 1

print(f"\nResult: {passed}/{len(checks)} checks passed")

if passed == len(checks):
    print("All injected edge cases were detected successfully!")
else:
    print("Some checks failed. Review the scenario data.")
