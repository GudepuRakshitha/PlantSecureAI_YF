"""Regenerate every dataset in the documented order.

    python src/pipeline.py                 # generate data
    python src/pipeline.py --force         # regenerate, then analyze + export

Baseline tables are written to ``data/`` and the scenario population to
``data/scenarios/``.  The two populations are never written to the same file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, event_generator, generator, inject_edge_cases
from src import schema, transaction_generator


def generate(
    data_dir: Path = config.DATA_DIR,
    seed: int = config.SEED,
) -> dict[str, dict[str, pd.DataFrame]]:
    """Generate baseline + scenario data and write all CSVs."""
    data_dir = Path(data_dir)
    scenario_dir = data_dir / "scenarios"

    master = generator.build_master(seed)
    generator.write_master(master, data_dir)

    events = event_generator.build_events(master["alarm_definitions"], seed)
    event_generator.write_events(events, data_dir)

    transactions = transaction_generator.build_transactions(
        master["plants"], master["machines"], events, seed
    )
    transaction_generator.write_transactions(transactions, data_dir)

    baseline = {**master, **transactions}
    scenario = inject_edge_cases.build_scenarios(
        {
            name: frame.copy()
            for name, frame in baseline.items()
        }
    )
    inject_edge_cases.write_scenarios(scenario, scenario_dir)

    return {"baseline": baseline, "scenario": scenario}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--seed", type=int, default=config.SEED)
    parser.add_argument(
        "--with-analysis",
        action="store_true",
        help="also run the analyzer and the SQLite/JSON exports",
    )
    args = parser.parse_args(argv)

    datasets = generate(args.data_dir, args.seed)
    print("\nPIPELINE COMPLETE")
    for population, tables in datasets.items():
        print(f"  {population}: " + ", ".join(f"{k}={len(v)}" for k, v in tables.items()))

    if args.with_analysis:
        from src import build_database, safety_analyzer, validate_data, validate_edge_cases

        validate_data.main(["--data-dir", str(args.data_dir)])
        safety_analyzer.main(["--data-dir", str(args.data_dir)])
        validate_edge_cases.main(["--data-dir", str(args.data_dir)])
        build_database.main(["--data-dir", str(args.data_dir)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
