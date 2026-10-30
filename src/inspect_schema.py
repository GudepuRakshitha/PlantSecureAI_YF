
import pandas as pd
from pathlib import Path

DATA = Path("data")

files = [
    "machines.csv",
    "interlocks.csv",
    "alarm_definitions.csv",
    "alarm_events.csv",
    "operator_shifts.csv",
    "acknowledgements.csv",
    "incidents.csv",
    "corrective_actions.csv",
]

for filename in files:
    df = pd.read_csv(DATA / filename)
    print(f"\n--- {filename} ---")
    print("Columns:", list(df.columns))
    print(df.head(2).to_string(index=False))
