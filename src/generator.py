
import pandas as pd
import random
from pathlib import Path

SEED = 20261022
random.seed(SEED)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# 1. Generate 4 plants
plants = []

for i in range(1, 5):
    plants.append({
        "plant_id": f"PLT-{i:03d}",
        "plant_name": f"Factory Plant {i}",
        "location": ["Hyderabad", "Bangalore", "Chennai", "Pune"][i - 1],
        "status": "ACTIVE"
    })

pd.DataFrame(plants).to_csv(DATA_DIR / "plants.csv", index=False)

# 2. Generate 60 machines
machines = []

for i in range(1, 61):
    plant_number = ((i - 1) // 15) + 1

    machines.append({
        "machine_id": f"MCH-{i:03d}",
        "plant_id": f"PLT-{plant_number:03d}",
        "machine_name": f"Machine {i}",
        "machine_type": random.choice(
            ["CONVEYOR", "ROBOT", "PRESS", "MOTOR", "PUMP"]
        ),
        "status": "ACTIVE"
    })

machines_df = pd.DataFrame(machines)
machines_df.to_csv(DATA_DIR / "machines.csv", index=False)

# 3. Generate safety zones
zones = []

for i in range(1, 5):
    for j in range(1, 4):
        zones.append({
            "zone_id": f"SAFE-PLT-{i:03d}-{j:03d}",
            "plant_id": f"PLT-{i:03d}",
            "zone_name": f"Safety Zone {j}",
            "risk_level": random.choice(["LOW", "MEDIUM", "HIGH"])
        })

pd.DataFrame(zones).to_csv(DATA_DIR / "safety_zones.csv", index=False)

# 4. Generate interlocks
interlocks = []

for i in range(1, 61):
    for j in range(1, 3):
        interlocks.append({
            "interlock_id": f"INT-{i:03d}-{j:02d}",
            "machine_id": f"MCH-{i:03d}",
            "interlock_name": f"Interlock {j}",
            "required_state": "CLOSED",
            "current_state": "CLOSED"
        })

pd.DataFrame(interlocks).to_csv(DATA_DIR / "interlocks.csv", index=False)

# 5. Generate 200 alarm definitions
alarm_definitions = []

for i in range(1, 201):
    machine_number = ((i - 1) % 60) + 1

    alarm_definitions.append({
        "alarm_definition_id": f"ALMDEF-{i:04d}",
        "machine_id": f"MCH-{machine_number:03d}",
        "alarm_name": f"Safety Alarm {i}",
        "severity": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
        "acknowledgement_required": True,
        "acknowledgement_limit_minutes": 5
    })

pd.DataFrame(alarm_definitions).to_csv(
    DATA_DIR / "alarm_definitions.csv", index=False
)

print("MASTER DATA GENERATED SUCCESSFULLY!")
print("Plants:", len(plants))
print("Machines:", len(machines_df))
print("Safety Zones:", len(zones))
print("Interlocks:", len(interlocks))
print("Alarm Definitions:", len(alarm_definitions))
print("Files saved inside the data folder.")
