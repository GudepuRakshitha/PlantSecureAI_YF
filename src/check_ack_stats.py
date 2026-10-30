
import pandas as pd

acks = pd.read_csv("data/acknowledgements.csv")
definitions = pd.read_csv("data/alarm_definitions.csv")

print("\n========== ACKNOWLEDGEMENT STATISTICS ==========")

print("\nResponse time distribution (minutes):")
print(acks["response_minutes"].describe())

print("\nAcknowledgement limits:")
print(definitions["acknowledgement_limit_minutes"].value_counts())

merged = acks.merge(
    pd.read_csv("data/alarm_events.csv")[
        ["alarm_event_id", "alarm_definition_id"]
    ],
    on="alarm_event_id"
).merge(
    definitions[
        ["alarm_definition_id", "acknowledgement_limit_minutes"]
    ],
    on="alarm_definition_id"
)

late = merged[
    merged["response_minutes"] >
    merged["acknowledgement_limit_minutes"]
]

print("\nTotal acknowledgements:", len(acks))
print("Late acknowledgements:", len(late))
print("Late acknowledgement percentage:",
      round(len(late) / len(acks) * 100, 2), "%")

print("\nStatistics completed.")
