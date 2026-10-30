"""Generate the synthetic master data (plants, machines, zones, interlocks,
alarm definitions).

Run directly::

    python src/generator.py

The random draw order is intentionally preserved from the original project so
that the generated master data stays stable for seed 20261022.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, schema

LOCATIONS = ("Hyderabad", "Bangalore", "Chennai", "Pune")


def build_plants() -> pd.DataFrame:
    """Return the four synthetic plants."""
    return pd.DataFrame(
        [
            {
                "plant_id": f"PLT-{i:03d}",
                "plant_name": f"Factory Plant {i}",
                "location": LOCATIONS[i - 1],
                "status": "ACTIVE",
            }
            for i in range(1, config.N_PLANTS + 1)
        ]
    )


def build_zones(rng: random.Random) -> pd.DataFrame:
    """Return three safety zones per plant (12 in total)."""
    zones = []
    for plant_number in range(1, config.N_PLANTS + 1):
        for zone_number in range(1, config.N_ZONES_PER_PLANT + 1):
            zones.append(
                {
                    "zone_id": f"SAFE-PLT-{plant_number:03d}-{zone_number:03d}",
                    "plant_id": f"PLT-{plant_number:03d}",
                    "zone_name": f"Safety Zone {zone_number}",
                    "risk_level": rng.choice(["LOW", "MEDIUM", "HIGH"]),
                }
            )
    return pd.DataFrame(zones)


def build_machines(machine_rng: random.Random) -> pd.DataFrame:
    """Return 60 machines, each linked to a plant and a zone of that plant.

    Zone assignment is deterministic round-robin inside the plant so the
    machine -> zone foreign key is always valid and balanced.
    """
    machines = []
    for i in range(1, config.N_MACHINES + 1):
        plant_number = ((i - 1) // 15) + 1
        zone_number = ((i - 1) % config.N_ZONES_PER_PLANT) + 1
        machines.append(
            {
                "machine_id": f"MCH-{i:03d}",
                "plant_id": f"PLT-{plant_number:03d}",
                "zone_id": f"SAFE-PLT-{plant_number:03d}-{zone_number:03d}",
                "machine_name": f"Machine {i}",
                "machine_type": machine_rng.choice(list(config.MACHINE_TYPES)),
                "status": "ACTIVE",
            }
        )
    return pd.DataFrame(machines)


def build_interlocks() -> pd.DataFrame:
    """Return two interlocks per machine (120 in total)."""
    interlocks = []
    for i in range(1, config.N_MACHINES + 1):
        for j in range(1, config.N_INTERLOCKS_PER_MACHINE + 1):
            interlocks.append(
                {
                    "interlock_id": f"INT-{i:03d}-{j:02d}",
                    "machine_id": f"MCH-{i:03d}",
                    "interlock_name": f"Interlock {j}",
                    "required_state": "CLOSED",
                    "current_state": "CLOSED",
                }
            )
    return pd.DataFrame(interlocks)


def build_alarm_definitions(definition_rng: random.Random) -> pd.DataFrame:
    """Return 200 alarm definitions spread over the machines."""
    definitions = []
    for i in range(1, config.N_ALARM_DEFINITIONS + 1):
        machine_number = ((i - 1) % config.N_MACHINES) + 1
        definitions.append(
            {
                "alarm_definition_id": f"ALMDEF-{i:04d}",
                "machine_id": f"MCH-{machine_number:03d}",
                "alarm_name": f"Safety Alarm {i}",
                "severity": definition_rng.choice(list(config.SEVERITIES)),
                "acknowledgement_required": True,
                "acknowledgement_limit_minutes": config.ACK_LIMIT_MINUTES,
            }
        )
    return pd.DataFrame(definitions)


def build_master(seed: int = config.SEED) -> dict[str, pd.DataFrame]:
    """Build every master table without touching the filesystem.

    The original project used one global ``random`` stream in the order
    machines -> zones -> alarm definitions.  Replaying those draws on private
    generators keeps the historical machine types, zone risks and severities
    while still letting each table be built independently.
    """
    machine_rng = random.Random(seed)
    machines = build_machines(machine_rng)

    zone_rng = random.Random(seed)
    for _ in range(config.N_MACHINES):
        zone_rng.choice(list(config.MACHINE_TYPES))
    zones = build_zones(zone_rng)

    definition_rng = random.Random(seed)
    for _ in range(config.N_MACHINES):
        definition_rng.choice(list(config.MACHINE_TYPES))
    for _ in range(config.N_PLANTS * config.N_ZONES_PER_PLANT):
        definition_rng.choice(["LOW", "MEDIUM", "HIGH"])

    return {
        "plants": build_plants(),
        "safety_zones": zones,
        "machines": machines,
        "interlocks": build_interlocks(),
        "alarm_definitions": build_alarm_definitions(definition_rng),
    }


def write_master(
    master: dict[str, pd.DataFrame], data_dir: Path = config.DATA_DIR
) -> None:
    """Write master tables as CSV."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for spec in (
        schema.PLANTS,
        schema.MACHINES,
        schema.SAFETY_ZONES,
        schema.INTERLOCKS,
        schema.ALARM_DEFINITIONS,
    ):
        master[spec.name].to_csv(data_dir / spec.filename, index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--seed", type=int, default=config.SEED)
    args = parser.parse_args(argv)

    master = build_master(args.seed)
    write_master(master, args.data_dir)

    print("MASTER DATA GENERATED SUCCESSFULLY!")
    for name, frame in master.items():
        print(f"  {name}: {len(frame)} rows")
    print(f"Files saved inside {args.data_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
