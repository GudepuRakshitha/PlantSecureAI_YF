"""Validate the injected-scenario detector against ``ground_truth.csv``.

    python src/validate_edge_cases.py
    python src/validate_edge_cases.py --report docs/validation_report_edge.md

The validator compares *detector output* with ground truth, normalises label
names, computes TP/FP/FN, precision and recall, and verifies that none of the
negative controls is flagged.  Baseline data is re-checked as an independent
population (it must stay clean).  Any failure exits with status 1.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, data_access, detection, schema
from src.validate_data import ValidationResult


def validate_scenarios(
    data_dir: Path = config.DATA_DIR,
) -> tuple[ValidationResult, dict[str, object] | None]:
    """Validate detector behaviour and scenario data integrity."""
    result = ValidationResult()
    data_dir = Path(data_dir)
    scenario_dir = data_dir / "scenarios"

    required_files = list(schema.SCENARIO_FILENAMES.values()) + ["ground_truth.csv"]
    missing = [name for name in required_files if not (scenario_dir / name).exists()]
    result.record(
        "scenario: files present",
        not missing,
        "missing: " + ", ".join(missing) if missing else f"{len(required_files)} files",
    )
    if missing:
        return result, None

    try:
        scenario = data_access.prepare_population("scenario", data_dir)
    except Exception as error:  # noqa: BLE001 - surfaced as a failed check
        result.record("scenario: load population", False, str(error))
        return result, None
    result.record("scenario: load population", True, "loaded")

    frames = scenario["frames"]
    truth = frames["ground_truth"]

    # ------------------------------------------------------------------
    # Ground truth contract
    # ------------------------------------------------------------------
    expected_columns = set(schema.GROUND_TRUTH.columns)
    result.record(
        "ground_truth: required columns",
        expected_columns.issubset(truth.columns),
        "missing: " + ", ".join(sorted(expected_columns - set(truth.columns)))
        if not expected_columns.issubset(truth.columns)
        else "ok",
    )
    anomaly_truth = truth[truth["is_anomaly"].astype(bool)]
    anomaly_case_ids = set(anomaly_truth["case_id"].astype(str))
    result.record(
        "ground_truth: five anomaly cases",
        anomaly_case_ids == set(config.EXPECTED_CASE_IDS),
        f"found {sorted(anomaly_case_ids)}",
    )
    negative_cases = set(
        truth.loc[~truth["is_anomaly"].astype(bool), "case_id"].astype(str)
    )
    result.record(
        "ground_truth: three negative controls",
        negative_cases == set(config.NEGATIVE_CONTROL_CASE_IDS),
        f"found {sorted(negative_cases)}",
    )

    # ------------------------------------------------------------------
    # Scenario referential integrity and enumerations
    # ------------------------------------------------------------------
    baseline_machines = set(frames["machines"]["machine_id"])
    scenario_frames = {
        name: frames[name]
        for name in schema.SCENARIO_FILENAMES
        if name in frames
    }
    for name, frame in scenario_frames.items():
        spec = schema.TABLES_BY_NAME[name]
        missing_columns = [c for c in spec.columns if c not in frame.columns]
        result.record(
            f"scenario {name}: required columns",
            not missing_columns,
            "missing: " + ", ".join(missing_columns) if missing_columns else "ok",
        )
        for column, allowed in spec.enums.items():
            if column not in frame.columns:
                continue
            invalid = frame[column].dropna()[~frame[column].dropna().isin(allowed)]
            result.record(
                f"scenario {name}.{column}: allowed values",
                invalid.empty,
                f"{len(invalid)} invalid",
            )
        missing_case = frame.loc[
            frame["dataset"] == "scenario", "case_id"
        ].isna().sum()
        result.record(
            f"scenario {name}: case_id populated on injected rows",
            int(missing_case) == 0,
            f"{int(missing_case)} missing",
        )

    unknown_machines = set()
    for name in ("acknowledgements", "interlocks", "incidents", "alarm_events"):
        frame = scenario_frames[name]
        if "machine_id" in frame.columns:
            unknown_machines |= set(frame["machine_id"].dropna()) - baseline_machines
    result.record(
        "scenario: machine foreign keys valid",
        not unknown_machines,
        f"unknown: {sorted(unknown_machines)[:5]}",
    )
    known_events = set(frames["alarm_events"]["alarm_event_id"])
    unknown_ack_events = set(
        scenario_frames["acknowledgements"]["alarm_event_id"].dropna()
    ) - known_events
    result.record(
        "scenario: acknowledgement alarm foreign keys valid",
        not unknown_ack_events,
        f"unknown: {sorted(unknown_ack_events)[:5]}",
    )
    known_incidents = set(frames["incidents"]["incident_id"])
    unknown_actions = set(
        scenario_frames["corrective_actions"]["incident_id"].dropna()
    ) - known_incidents
    result.record(
        "scenario: action incident foreign keys valid",
        not unknown_actions,
        f"unknown: {sorted(unknown_actions)[:5]}",
    )

    # ------------------------------------------------------------------
    # Detector against baseline (independent population)
    # ------------------------------------------------------------------
    def baseline_only(name: str) -> pd.DataFrame:
        """Return the baseline slice of a scenario-population table."""
        frame = frames[name]
        if "dataset" in frame.columns:
            frame = frame[frame["dataset"] == "baseline"]
        return frame.drop(columns=["dataset", "case_id"], errors="ignore")

    baseline_anomalies = detection.detect_anomalies(
        baseline_only("alarm_events"),
        baseline_only("acknowledgements"),
        baseline_only("interlocks"),
        baseline_only("incidents"),
        baseline_only("corrective_actions"),
        frames["machines"],
    )
    result.record(
        "baseline: zero anomalies (no false positives)",
        baseline_anomalies.empty,
        f"{len(baseline_anomalies)} findings",
    )

    # ------------------------------------------------------------------
    # Detector against ground truth
    # ------------------------------------------------------------------
    detections = scenario["exceptions"]
    report = detection.evaluate_detection(detections, truth)
    result.record(
        "detector: all five cases detected",
        not report["missing_cases"],
        f"missing: {report['missing_cases']}",
    )
    result.record(
        "detector: no false positives",
        report["false_positives"] == 0,
        f"{report['false_positives']} unexpected: {report['false_positive_details']}",
    )
    result.record(
        "detector: no false negatives",
        report["false_negatives"] == 0,
        f"{report['false_negatives']} missing: {report['false_negative_details']}",
    )
    result.record(
        "detector: negative controls not flagged",
        not report["negative_controls_flagged"],
        f"flagged: {report['negative_controls_flagged']}",
    )
    result.record(
        "detector: precision and recall are 1.0",
        report["precision"] == 1.0 and report["recall"] == 1.0,
        f"precision={report['precision']}, recall={report['recall']}",
    )

    # ------------------------------------------------------------------
    # Persisted analyzer output must match the live detector
    # ------------------------------------------------------------------
    persisted_path = data_dir / schema.ANALYSIS_EXCEPTIONS.filename
    if persisted_path.exists():
        persisted = pd.read_csv(persisted_path)
        persisted_pairs = set(
            zip(
                persisted["exception_type"].map(detection.normalize_label),
                persisted["record_id"].astype(str),
            )
        )
        expected_pairs = set(
            zip(
                detections["exception_type"].map(detection.normalize_label),
                detections["record_id"].astype(str),
            )
        )
        result.record(
            "outputs: analysis_exceptions.csv matches live detector",
            persisted_pairs == expected_pairs,
            f"persisted={len(persisted_pairs)}, live={len(expected_pairs)}",
        )
        result.record(
            "outputs: analysis_exceptions has no routine SLA rows",
            not persisted["is_routine_sla"].astype(bool).any(),
            "is_routine_sla must be False for anomalies",
        )
        result.record(
            "outputs: analysis_exceptions has plant/machine/case context",
            bool(
                persisted["plant_id"].notna().all()
                and persisted["machine_id"].notna().all()
                and persisted["case_id"].notna().all()
            ),
            f"{int(persisted[['plant_id', 'machine_id', 'case_id']].isna().any(axis=1).sum())} unmapped rows",
        )
    else:
        result.record(
            "outputs: analysis_exceptions.csv exists",
            False,
            "run src/safety_analyzer.py first",
        )

    return result, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    result, report = validate_scenarios(args.data_dir)

    print("\n========== EDGE-CASE DETECTION VALIDATION ==========\n")
    for check in result.checks:
        if not check.passed:
            print(f"FAIL: {check.name} -> {check.detail}")
    passed = len(result.checks) - len(result.failures)
    print(f"\n{passed}/{len(result.checks)} checks passed")

    if report:
        print("\nDetection score")
        print(f"  Expected anomalies : {report['expected_anomalies']}")
        print(f"  True positives     : {report['true_positives']}")
        print(f"  False positives    : {report['false_positives']}")
        print(f"  False negatives    : {report['false_negatives']}")
        print(f"  Precision          : {report['precision']:.2f}")
        print(f"  Recall             : {report['recall']:.2f}")
        print(f"  Cases detected     : {', '.join(report['detected_cases'])}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(result.as_markdown(args.data_dir), encoding="utf-8")
        print(f"Report written to {args.report}")

    if not result.passed:
        print("\nEDGE-CASE VALIDATION FAILED")
        return 1
    print("\nALL EDGE-CASE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
