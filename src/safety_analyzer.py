"""Analyze the safety dataset and export the analytical outputs.

The analyzer consumes two clearly separated populations:

* **baseline** -- clean data, used for operational KPIs and SLA breaches;
* **scenario test** -- baseline plus injected anomalies and negative controls,
  used only to score the detector against ``ground_truth.csv``.

Outputs
-------
``data/sla_breaches.csv``       routine late acknowledgements (baseline only)
``data/analysis_exceptions.csv`` genuine anomalies found in the scenario run
``data/analysis_summary.json``  both populations' metrics + detection score
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, data_access, detection, metrics, schema


def _serialisable(value: object) -> object:
    """Convert numpy/pandas scalars to JSON-friendly values."""
    if isinstance(value, dict):
        return {str(key): _serialisable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialisable(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def analyze(data_dir: Path = config.DATA_DIR, write: bool = True) -> dict[str, object]:
    """Run baseline analysis and scenario detection."""
    data_dir = Path(data_dir)

    baseline = data_access.prepare_population("baseline", data_dir)
    scenario = data_access.prepare_population("scenario", data_dir)

    baseline_events = baseline["events"]
    baseline_ack = baseline["ack_metrics"]
    baseline_incidents = baseline["incident_metrics"]
    baseline_actions = baseline["action_metrics"]
    breaches = baseline["sla_breaches"]
    baseline_exceptions = baseline["exceptions"]

    if baseline_exceptions is not None and not baseline_exceptions.empty:
        raise RuntimeError(
            "Baseline data produced anomalies; the baseline must be clean. "
            f"Found {len(baseline_exceptions)}. Run the validators for details."
        )

    scenario_exceptions = scenario["exceptions"]
    report = scenario["detection_report"]

    summary = {
        "seed": config.SEED,
        "populations": {
            "baseline": config.DATASET_DESCRIPTIONS["baseline"],
            "scenario": config.DATASET_DESCRIPTIONS["scenario"],
        },
        "timezone_policy": (
            "All timestamps are naive local plant time (Asia/Kolkata, UTC+05:30)."
        ),
        "thresholds": asdict(config.THRESHOLDS),
        "baseline": {
            "row_counts": baseline["row_counts"],
            "alarm_counts": metrics.alarm_counts(baseline_events),
            "acknowledgement": baseline_ack,
            "priority_compliance": metrics.priority_compliance(
                baseline["compliance"]
            ).to_dict(orient="records"),
            "severity_distribution": metrics.severity_distribution(
                baseline_events
            ).to_dict(orient="records"),
            "sla_breaches": int(len(breaches)),
            "genuine_anomalies": 0,
            "incidents": baseline_incidents,
            "corrective_actions": baseline_actions,
            "alarm_status_counts": {
                str(key): int(value)
                for key, value in baseline_events["alarm_status"]
                .value_counts()
                .items()
            },
            "chattering_pairs": int(
                len(
                    metrics.detect_chattering(
                        baseline_events,
                        definitions=baseline["definitions"],
                        machines=baseline["machines"],
                    )
                )
            ),
            "flood_episodes": int(
                len(
                    metrics.detect_floods(
                        baseline_events, plants=baseline["plants"]
                    )
                )
            ),
        },
        "scenario_test": {
            "row_counts": scenario["row_counts"],
            "genuine_anomalies": int(len(scenario_exceptions)),
            "exceptions_by_type": (
                {
                    str(key): int(value)
                    for key, value in scenario_exceptions["exception_type"]
                    .value_counts()
                    .items()
                }
                if not scenario_exceptions.empty
                else {}
            ),
            "detection_report": report,
        },
    }
    summary = _serialisable(summary)

    if write:
        data_dir.mkdir(parents=True, exist_ok=True)
        breaches.to_csv(
            data_dir / schema.SLA_BREACHES.filename,
            index=False,
            date_format="%Y-%m-%d %H:%M:%S",
        )
        scenario_exceptions.to_csv(
            data_dir / schema.ANALYSIS_EXCEPTIONS.filename,
            index=False,
        )
        with open(data_dir / "analysis_summary.json", "w", encoding="utf-8") as file:
            json.dump(summary, file, indent=4)

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument(
        "--no-write", action="store_true", help="compute metrics without writing files"
    )
    args = parser.parse_args(argv)

    summary = analyze(args.data_dir, write=not args.no_write)
    baseline = summary["baseline"]
    ack = baseline["acknowledgement"]
    scenario = summary["scenario_test"]

    print("\n========== SAFETY ANALYSIS COMPLETE ==========")
    print(f"Seed: {config.SEED}")
    print("\nBASELINE POPULATION")
    print(f"  Alarm activations      : {ack['total_activations']:,}")
    print(f"  Acknowledged           : {ack['total_acknowledged']:,}")
    print(f"  Unacknowledged         : {ack['total_unacknowledged']:,}")
    print(f"  On time                : {ack['on_time_acknowledgements']:,}")
    print(f"  Late                   : {ack['late_acknowledgements']:,}")
    print(f"  Acknowledgement rate   : {ack['acknowledgement_rate_pct']:.2f}%")
    print(f"  On-time compliance     : {ack['on_time_compliance_pct']:.2f}%")
    print(f"  Late                   : {ack['late_acknowledgement_pct']:.2f}%")
    print(f"  Unacknowledged         : {ack['unacknowledged_pct']:.2f}%")
    print(f"  Median response        : {ack['median_response_minutes']:.2f} min")
    print(f"  P95 response           : {ack['p95_response_minutes']:.2f} min")
    print(f"  Routine SLA breaches   : {baseline['sla_breaches']:,}")
    print(f"  Genuine anomalies      : {baseline['genuine_anomalies']}")

    print("\nSCENARIO TEST POPULATION")
    print(f"  Genuine anomalies      : {scenario['genuine_anomalies']}")
    if scenario["detection_report"]:
        report = scenario["detection_report"]
        print(f"  True positives         : {report['true_positives']}")
        print(f"  False positives        : {report['false_positives']}")
        print(f"  False negatives        : {report['false_negatives']}")
        print(f"  Precision / recall     : {report['precision']:.2f} / {report['recall']:.2f}")
        print(f"  Cases detected         : {', '.join(report['detected_cases']) or 'none'}")
        print(f"  Negative controls hit  : {len(report['negative_controls_flagged'])}")

    if not args.no_write:
        print(f"\nSaved: {args.data_dir / schema.SLA_BREACHES.filename}")
        print(f"Saved: {args.data_dir / schema.ANALYSIS_EXCEPTIONS.filename}")
        print(f"Saved: {args.data_dir / 'analysis_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
