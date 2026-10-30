"""Generate alarm events.

The lifecycle columns are finalised later by ``transaction_generator`` once
acknowledgements exist; running this module alone produces a schema-valid but
all-unacknowledged snapshot.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, schema


def build_events(
    alarm_definitions: pd.DataFrame,
    seed: int = config.SEED,
    total_events: int = config.TOTAL_EVENTS,
) -> pd.DataFrame:
    """Build the 50,000 alarm activations.

    The RNG draw order matches the original implementation so the same seed
    produces the same events, machines, definitions and timestamps.
    """
    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp(config.DATASET_START)

    # One draw covering the whole 30-day window.
    offsets = rng.integers(0, config.EVENT_DAYS * 24 * 60 * 60, total_events)
    timestamps = start_date + pd.to_timedelta(offsets, unit="s")

    events: list[dict[str, object]] = []
    for i in range(total_events):
        alarm = alarm_definitions.iloc[rng.integers(0, len(alarm_definitions))]
        events.append(
            {
                "alarm_event_id": f"ALM-{alarm['machine_id']}-{i + 1:06d}",
                "machine_id": alarm["machine_id"],
                "alarm_definition_id": alarm["alarm_definition_id"],
                "severity": alarm["severity"],
                "event_timestamp": timestamps[i],
                "machine_state": rng.choice(list(config.MACHINE_STATES)),
                # Placeholder lifecycle; transaction_generator rewrites it.
                "alarm_status": "UNACKNOWLEDGED",
                "acknowledged": False,
                "acknowledged_at": pd.NaT,
                "cleared_at": pd.NaT,
                "state_transition": "ACTIVE>UNACKNOWLEDGED",
                "issue_type": "NONE",
            }
        )

    events_df = pd.DataFrame(events)
    return (
        events_df.sort_values("event_timestamp")
        .reset_index(drop=True)[list(schema.ALARM_EVENTS.columns)]
    )


def write_events(events: pd.DataFrame, data_dir: Path = config.DATA_DIR) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    events.to_csv(
        data_dir / schema.ALARM_EVENTS.filename,
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--seed", type=int, default=config.SEED)
    args = parser.parse_args(argv)

    definitions = pd.read_csv(args.data_dir / schema.ALARM_DEFINITIONS.filename)
    events = build_events(definitions, args.seed)
    write_events(events, args.data_dir)

    print("ALARM EVENTS GENERATED SUCCESSFULLY!")
    print("Total alarm events:", len(events))
    print("Unique machines:", events["machine_id"].nunique())
    print("Start:", events["event_timestamp"].min())
    print("End:", events["event_timestamp"].max())
    print(f"Output: {args.data_dir / schema.ALARM_EVENTS.filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
