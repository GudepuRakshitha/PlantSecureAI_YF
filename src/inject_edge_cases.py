
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DATA = Path("data")
OUT = DATA / "scenarios"
OUT.mkdir(parents=True, exist_ok=True)

# Load baseline datasets
events = pd.read_csv(DATA / "alarm_events.csv")
machines = pd.read_csv(DATA / "machines.csv")
interlocks = pd.read_csv(DATA / "interlocks.csv")
acknowledgements = pd.read_csv(DATA / "acknowledgements.csv")
incidents = pd.read_csv(DATA / "incidents.csv")
actions = pd.read_csv(DATA / "corrective_actions.csv")

events["event_timestamp"] = pd.to_datetime(events["event_timestamp"])
acknowledgements["ack_timestamp"] = pd.to_datetime(
    acknowledgements["ack_timestamp"]
)

# Store injected records separately
injected_events = []
injected_acks = []
injected_interlocks = []
injected_incidents = []
injected_actions = []
ground_truth = []


def record_truth(case_id, scenario, entity, record_id, description):
    ground_truth.append({
        "case_id": case_id,
        "scenario_type": scenario,
        "entity": entity,
        "record_id": record_id,
        "description": description
    })


# --------------------------------------------------
# CASE 1: ACKNOWLEDGEMENT BEFORE ALARM
# --------------------------------------------------

base_event = events.iloc[0]
event_id = base_event["alarm_event_id"]

ack_id = f"ACK-{event_id}-EDGE01"
ack_time = base_event["event_timestamp"] - pd.Timedelta(minutes=2)

injected_acks.append({
    "acknowledgement_id": ack_id,
    "alarm_event_id": event_id,
    "operator_id": "OP-EDGE-01",
    "shift_id": "SHIFT-EDGE-01",
    "ack_timestamp": ack_time,
    "response_minutes": -2,
    "status": "INVALID_EARLY_ACK"
})

record_truth(
    "EDGE-001",
    "ACK_BEFORE_ALARM",
    "Acknowledgement",
    ack_id,
    "Acknowledgement occurs two minutes before the alarm event."
)


# --------------------------------------------------
# CASE 2: IMPOSSIBLE INTERLOCK STATE
# --------------------------------------------------

base_interlock = interlocks.iloc[0]
interlock_id = base_interlock["interlock_id"]

bad_interlock = base_interlock.copy()

if base_interlock["required_state"] == "CLOSED":
    bad_interlock["current_state"] = "OPEN"
else:
    bad_interlock["current_state"] = "CLOSED"

injected_interlocks.append(bad_interlock)

record_truth(
    "EDGE-002",
    "IMPOSSIBLE_INTERLOCK_STATE",
    "Interlock",
    interlock_id,
    "Current interlock state conflicts with the required safe state."
)


# --------------------------------------------------
# CASE 3: INCIDENT WITHOUT TRIGGERING CONTEXT
# --------------------------------------------------

low_events = events[
    (events["severity"] == "LOW") &
    (events["machine_state"] == "STOPPED")
]

if low_events.empty:
    raise ValueError("No LOW severity STOPPED event found.")

context_event = low_events.iloc[0]

# Find the correct plant for this machine
plant_id = machines.loc[
    machines["machine_id"] == context_event["machine_id"],
    "plant_id"
].iloc[0]

next_incident_number = len(incidents) + 1
incident_id = f"INC-2026-{next_incident_number:06d}"

injected_incidents.append({
    "incident_id": incident_id,
    "alarm_event_id": context_event["alarm_event_id"],
    "machine_id": context_event["machine_id"],
    "plant_id": plant_id,
    "incident_type": "UNSAFE_MACHINE_RUNNING",
    "severity": "LOW",
    "created_at": context_event["event_timestamp"],
    "status": "OPEN"
})

record_truth(
    "EDGE-003",
    "INCIDENT_WITHOUT_TRIGGER",
    "Incident",
    incident_id,
    "Incident is linked to a LOW severity STOPPED event, which does not meet the unsafe-running rule."
)


# --------------------------------------------------
# CASE 4: ALARM FLOOD / DUPLICATE REPLAY
# --------------------------------------------------

flood_event = events.iloc[1]

# Replay the exact same alarm event three times.
for _ in range(3):
    injected_events.append(flood_event.copy())

record_truth(
    "EDGE-004",
    "ALARM_FLOOD_DUPLICATE_REPLAY",
    "AlarmEvent",
    flood_event["alarm_event_id"],
    "The same alarm event is replayed three additional times with the same event ID."
)


# --------------------------------------------------
# CASE 5: ACTION CLOSED WITHOUT VERIFICATION
# --------------------------------------------------

if actions.empty:
    raise ValueError("No baseline corrective action found.")

base_action = actions.iloc[0]
action_id = f"ACT-{base_action['incident_id']}-EDGE01"

bad_action = base_action.copy()
bad_action["action_id"] = action_id
bad_action["status"] = "CLOSED"
bad_action["verification_status"] = "NOT_VERIFIED"

injected_actions.append(bad_action)

record_truth(
    "EDGE-005",
    "CLOSED_WITHOUT_VERIFICATION",
    "CorrectiveAction",
    action_id,
    "Corrective action is marked CLOSED without verification."
)


# --------------------------------------------------
# SAVE SCENARIO FILES
# --------------------------------------------------

pd.DataFrame(injected_events).to_csv(
    OUT / "injected_alarm_events.csv", index=False
)

pd.DataFrame(injected_acks).to_csv(
    OUT / "injected_acknowledgements.csv", index=False
)

pd.DataFrame(injected_interlocks).to_csv(
    OUT / "injected_interlocks.csv", index=False
)

pd.DataFrame(injected_incidents).to_csv(
    OUT / "injected_incidents.csv", index=False
)

pd.DataFrame(injected_actions).to_csv(
    OUT / "injected_corrective_actions.csv", index=False
)

pd.DataFrame(ground_truth).to_csv(
    OUT / "ground_truth.csv", index=False
)


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

print("\nEDGE CASES CREATED SUCCESSFULLY!")
print("Injected alarm events:", len(injected_events))
print("Injected acknowledgements:", len(injected_acks))
print("Injected interlocks:", len(injected_interlocks))
print("Injected incidents:", len(injected_incidents))
print("Injected corrective actions:", len(injected_actions))
print("Ground truth labels:", len(ground_truth))
print("Output folder:", OUT)
