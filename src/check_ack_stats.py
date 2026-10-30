"""Print activation-denominated acknowledgement statistics.

    python src/check_ack_stats.py

This replaces the old acknowledged-only view.  Every rate is divided by alarm
activations, so alarms that were never acknowledged are visible instead of
being silently dropped from the denominator.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, data_access, metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    args = parser.parse_args(argv)

    population = data_access.prepare_population("baseline", args.data_dir)
    compliance = population["compliance"]
    ack = metrics.ack_compliance_metrics(compliance)

    print("\n========== ACKNOWLEDGEMENT STATISTICS ==========")
    print("Population: baseline (activation-denominated)\n")

    rows = [
        ("Alarm activations", ack["total_activations"]),
        ("Acknowledged", ack["total_acknowledged"]),
        ("Unacknowledged", ack["total_unacknowledged"]),
        ("Acknowledged on time", ack["on_time_acknowledgements"]),
        ("Acknowledged late", ack["late_acknowledgements"]),
    ]
    for label, value in rows:
        print(f"  {label:<22} {int(value):>8,}")

    print()
    print(f"  Acknowledgement rate   {ack['acknowledgement_rate_pct']:>7.2f}%")
    print(f"  On-time compliance     {ack['on_time_compliance_pct']:>7.2f}%")
    print(f"  Late (of activations)  {ack['late_acknowledgement_pct']:>7.2f}%")
    print(f"  Unacknowledged         {ack['unacknowledged_pct']:>7.2f}%")
    print(f"  Median response        {ack['median_response_minutes']:>7.2f} min")
    print(f"  P95 response           {ack['p95_response_minutes']:>7.2f} min")

    acknowledged = compliance.dropna(subset=["response_minutes"])
    if len(acknowledged):
        acknowledged_only = (
            acknowledged["response_minutes"]
            <= acknowledged["acknowledgement_limit_minutes"]
        ).mean() * 100
        print(
            "\n  Acknowledged-only on-time rate "
            f"{acknowledged_only:>7.2f}%  (not used for KPIs)"
        )

    print("\nBy priority (denominator = activations):")
    priority = metrics.priority_compliance(compliance)
    display = priority.rename(
        columns={
            "acknowledgement_rate_pct": "ack_rate_%",
            "on_time_compliance_pct": "on_time_%",
            "unacknowledged_pct": "unacked_%",
        }
    )
    columns = [
        "severity",
        "activations",
        "acknowledged",
        "on_time",
        "late",
        "unacknowledged",
        "ack_rate_%",
        "on_time_%",
        "unacked_%",
    ]
    print(display[columns].to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    print("\nResponse-time distribution (acknowledged alarms, minutes):")
    print(acknowledged["response_minutes"].describe().to_string(float_format=lambda v: f"{v:.2f}"))

    print(f"\nRoutine SLA breaches: {len(population['sla_breaches']):,}")
    print(f"Genuine anomalies   : {len(population['exceptions']):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
