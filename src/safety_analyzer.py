
import pandas as pd
import json
from pathlib import Path

DATA = Path("data")
SCENARIOS = DATA / "scenarios"

# Load baseline datasets
events = pd.read_csv(DATA / "alarm_events.csv")
definitions = pd.read_csv(DATA / "alarm_definitions.csv")
acks = pd.read_csv(DATA / "acknowledgements.csv")
incidents = pd.read_csv(DATA / "incidents.csv")
actions = pd.read_csv(DATA / "corrective_actions.csv")
interlocks = pd.read_csv(DATA / "interlocks.csv")

# Load injected scenario datasets
extra_events = pd.read_csv(SCENARIOS / "injected_alarm_events.csv")
extra_acks = pd.read_csv(SCENARIOS / "injected_acknowledgements.csv")
extra_interlocks = pd.read_csv(SCENARIOS / "injected_interlocks.csv")
extra_incidents = pd.read_csv(SCENARIOS / "injected_incidents.csv")
extra_actions = pd.read_csv(SCENARIOS / "injected_corrective_actions.csv")

# Combine baseline and scenario records for analysis
all_events = pd.concat([events, extra_events], ignore_index=True)
all_acks = pd.concat([acks, extra_acks], ignore_index=True)
all_interlocks = pd.concat(
    [interlocks, extra_interlocks], ignore_index=True
)
all_incidents = pd.concat(
    [incidents, extra_incidents], ignore_index=True
)
all_actions = pd.concat(
    [actions, extra_actions], ignore_index=True
)

exceptions = []


def add_exception(category, entity, record_id, severity, description):
    exceptions.append({
        "exception_type": category,
        "entity": entity,
        "record_id": str(record_id),
        "severity": severity,
        "description": description
    })


# --------------------------------------------------
# 1. ACKNOWLEDGEMENT VALIDATION
# --------------------------------------------------

event_times = events[["alarm_event_id", "event_timestamp"]].copy()

ack_check = all_acks.merge(
    event_times,
    on="alarm_event_id",
    how="left"
)

ack_check["ack_timestamp"] = pd.to_datetime(
    ack_check["ack_timestamp"]
)
ack_check["event_timestamp"] = pd.to_datetime(
    ack_check["event_timestamp"]
)

for _, row in ack_check.iterrows():
    if pd.isna(row["event_timestamp"]):
        add_exception(
            "ACK_WITHOUT_ALARM",
            "Acknowledgement",
            row["acknowledgement_id"],
            "HIGH",
            "Acknowledgement references an unknown alarm event."
        )
    elif row["ack_timestamp"] < row["event_timestamp"]:
        add_exception(
            "ACK_BEFORE_ALARM",
            "Acknowledgement",
            row["acknowledgement_id"],
            "CRITICAL",
            "Acknowledgement occurred before the alarm."
        )

# Check acknowledgement response-time limits
event_definition = events[
    ["alarm_event_id", "alarm_definition_id"]
]

ack_sla = all_acks.merge(
    event_definition,
    on="alarm_event_id",
    how="left"
).merge(
    definitions[
        [
            "alarm_definition_id",
            "acknowledgement_required",
            "acknowledgement_limit_minutes"
        ]
    ],
    on="alarm_definition_id",
    how="left"
)

for _, row in ack_sla.iterrows():
    if (
        row["acknowledgement_required"] == True
        and pd.notna(row["response_minutes"])
        and row["response_minutes"] >
        row["acknowledgement_limit_minutes"]
    ):
        add_exception(
            "LATE_ACKNOWLEDGEMENT",
            "Acknowledgement",
            row["acknowledgement_id"],
            "MEDIUM",
            "Acknowledgement exceeded the allowed response time."
        )


# --------------------------------------------------
# 2. INTERLOCK VALIDATION
# --------------------------------------------------

for _, row in all_interlocks.iterrows():
    if row["current_state"] != row["required_state"]:
        add_exception(
            "INTERLOCK_STATE_MISMATCH",
            "Interlock",
            row["interlock_id"],
            "CRITICAL",
            "Current interlock state does not match required safe state."
        )


# --------------------------------------------------
# 3. INCIDENT TRIGGER VALIDATION
# --------------------------------------------------

incident_check = all_incidents.merge(
    all_events[
        [
            "alarm_event_id",
            "severity",
            "machine_state"
        ]
    ].drop_duplicates("alarm_event_id"),
    on="alarm_event_id",
    how="left",
    suffixes=("_incident", "_event")
)

for _, row in incident_check.iterrows():
    valid_trigger = (
        row["severity_event"] in ["HIGH", "CRITICAL"]
        and row["machine_state"] == "RUNNING"
    ) if pd.notna(row["severity_event"]) else False

    if not valid_trigger:
        add_exception(
            "INCIDENT_WITHOUT_VALID_TRIGGER",
            "Incident",
            row["incident_id"],
            "HIGH",
            "Incident has no qualifying HIGH/CRITICAL alarm while machine is RUNNING."
        )


# --------------------------------------------------
# 4. DUPLICATE ALARM / FLOOD DETECTION
# --------------------------------------------------

duplicate_counts = all_events.groupby(
    "alarm_event_id"
).size()

for event_id, count in duplicate_counts.items():
    if count > 1:
        add_exception(
            "DUPLICATE_ALARM_REPLAY",
            "AlarmEvent",
            event_id,
            "HIGH",
            f"Alarm event appears {count} times."
        )


# --------------------------------------------------
# 5. CORRECTIVE ACTION VERIFICATION
# --------------------------------------------------

for _, row in all_actions.iterrows():
    if (
        row["status"] == "CLOSED"
        and row["verification_status"] != "VERIFIED"
    ):
        add_exception(
            "CLOSED_WITHOUT_VERIFICATION",
            "CorrectiveAction",
            row["action_id"],
            "HIGH",
            "Action is closed without successful verification."
        )


# --------------------------------------------------
# EXPORT RESULTS
# --------------------------------------------------

results = pd.DataFrame(exceptions)

if results.empty:
    results = pd.DataFrame(columns=[
        "exception_type",
        "entity",
        "record_id",
        "severity",
        "description"
    ])

results.to_csv(DATA / "analysis_exceptions.csv", index=False)

summary = {
    "baseline_alarm_events": int(len(events)),
    "scenario_alarm_event_rows": int(len(extra_events)),
    "total_alarm_event_rows_analyzed": int(len(all_events)),
    "total_exceptions": int(len(results)),
    "exceptions_by_type": {
        str(key): int(value)
        for key, value in results["exception_type"].value_counts().items()
    },
    "exceptions_by_severity": {
        str(key): int(value)
        for key, value in results["severity"].value_counts().items()
    }
}

with open(DATA / "analysis_summary.json", "w") as file:
    json.dump(summary, file, indent=4)

print("\n========== SAFETY ANALYSIS COMPLETE ==========")
print("Alarm event rows analyzed:", len(all_events))
print("Exceptions detected:", len(results))
print("\nExceptions by type:")
print(results["exception_type"].value_counts().to_string())
print("\nSaved: data/analysis_exceptions.csv")
print("Saved: data/analysis_summary.json")
