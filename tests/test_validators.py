"""Validator gate tests — fail-loud behaviour and clean-baseline expectations."""

from __future__ import annotations

from src import validate_data, validate_edge_cases


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
