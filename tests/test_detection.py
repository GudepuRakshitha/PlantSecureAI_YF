"""Scenario detector and validation gate tests."""

from __future__ import annotations

import pytest

from src import config, detection, safety_analyzer, validate_data, validate_edge_cases


def test_baseline_population_has_no_genuine_anomalies(baseline) -> None:
    assert len(baseline["exceptions"]) == 0


def test_scenario_detector_finds_all_injected_cases(scenario) -> None:
    report = scenario["detection_report"]
    assert report is not None
    assert report["expected_anomalies"] == 5
    assert report["true_positives"] == 5
    assert report["false_positives"] == 0
    assert report["false_negatives"] == 0
    assert report["precision"] == pytest.approx(1.0)
    assert report["recall"] == pytest.approx(1.0)
    assert report["missing_cases"] == []
    assert report["negative_controls_flagged"] == []


def test_scenario_anomalies_are_genuine_only(scenario) -> None:
    exceptions = scenario["exceptions"]
    assert exceptions["is_routine_sla"].eq(False).all()
    assert len(exceptions) == 5


def test_scenario_genuine_anomalies_cover_every_injected_case(scenario) -> None:
    exceptions = scenario["exceptions"]
    detected = set(exceptions["case_id"])
    assert detected == set(config.EXPECTED_CASE_IDS)


def test_normalise_label_resolves_aliases() -> None:
    assert detection.normalize_label("ACK_BEFORE_EVENT") == "ACK_BEFORE_ALARM"
    assert detection.normalize_label("INTERLOCK_STATE_MISMATCH") == (
        "INTERLOCK_STATE_MISMATCH"
    )


def test_detector_reports_missing_cases(scenario) -> None:
    empty = scenario["exceptions"].iloc[0:0]
    report = detection.evaluate_detection(empty, scenario["ground_truth"])
    assert report["expected_anomalies"] == 5
    assert report["true_positives"] == 0
    assert report["false_negatives"] == 5
    assert len(report["missing_cases"]) == 5


def test_baseline_validator_passes() -> None:
    result = validate_data.validate_baseline()
    assert result.passed
    assert len(result.checks) >= 90
    assert result.failures == []


def test_baseline_validator_fails_loudly_on_missing_data(tmp_path) -> None:
    result = validate_data.validate_baseline(tmp_path)
    assert not result.passed
    assert len(result.failures) >= 1


def test_scenario_validator_passes() -> None:
    result, report = validate_edge_cases.validate_scenarios()
    assert result.passed
    assert report is not None
    assert report["true_positives"] == 5
    assert report["false_negatives"] == 0
    assert report["negative_controls_flagged"] == []


def test_analyzer_reports_clean_baseline_and_scenario_metrics() -> None:
    summary = safety_analyzer.analyze(write=False)
    baseline = summary["baseline"]
    scenario_test = summary["scenario_test"]

    assert baseline["genuine_anomalies"] == 0
    assert baseline["acknowledgement"]["total_activations"] == 50_000
    assert baseline["sla_breaches"] == 8_930

    assert scenario_test["genuine_anomalies"] == 5
    report = scenario_test["detection_report"]
    assert report["true_positives"] == 5
    assert report["false_positives"] == 0
    assert report["false_negatives"] == 0
