
import pandas as pd
from pathlib import Path

DATA = Path("data")

files = [
    "plants.csv",
    "machines.csv",
    "safety_zones.csv",
    "interlocks.csv",
    "alarm_definitions.csv",
    "alarm_events.csv",
    "operator_shifts.csv",
    "acknowledgements.csv",
    "incidents.csv",
    "corrective_actions.csv",
]

print("\n========== DATA VALIDATION ==========\n")

for filename in files:
    path = DATA / filename

    if not path.exists():
        print(f"MISSING FILE: {filename}")
        continue

    df = pd.read_csv(path)

    print(f"\n{filename}")
    print("Rows:", len(df))
    print("Duplicate rows:", df.duplicated().sum())
    print("Missing values:", df.isnull().sum().sum())

print("\n========== VALIDATION COMPLETE ==========")
