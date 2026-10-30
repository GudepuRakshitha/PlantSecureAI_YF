"""Inspect the CSV schema, dtypes, null counts and a small preview.

    python src/inspect_schema.py
    python src/inspect_schema.py --table alarm_events

The table list and column contract come from ``src/schema.py`` so this tool can
never drift from the rest of the project.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, data_access, schema


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument(
        "--table",
        default=None,
        choices=[spec.name for spec in schema.BASELINE_TABLES],
        help="inspect a single table instead of all of them",
    )
    parser.add_argument("--rows", type=int, default=2, help="preview rows")
    args = parser.parse_args(argv)

    specs = [
        spec
        for spec in schema.BASELINE_TABLES
        if args.table is None or spec.name == args.table
    ]

    for spec in specs:
        path = Path(args.data_dir) / spec.filename
        if not path.exists():
            print(f"\n--- {spec.filename} --- MISSING ({path})")
            continue

        frame = data_access.read_table(spec, path)
        print(f"\n--- {spec.filename} ---")
        print(f"Rows: {len(frame):,}  Columns: {len(frame.columns)}")
        print("Columns :", ", ".join(frame.columns))
        print("Contract:", ", ".join(spec.columns))
        missing = [column for column in spec.columns if column not in frame.columns]
        if missing:
            print("MISSING CONTRACT COLUMNS:", ", ".join(missing))
        nulls = frame.isna().sum()
        nulls = nulls[nulls > 0]
        print(
            "Nulls   :",
            ", ".join(f"{column}={int(count):,}" for column, count in nulls.items())
            or "none",
        )
        if args.rows > 0:
            print(frame.head(args.rows).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
