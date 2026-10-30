"""Global filter predicate tests — one predicate, reused everywhere."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src import config, data_access, metrics


def _filters(**kwargs) -> metrics.Filters:
    return metrics.Filters(**kwargs)


def test_empty_filter_covers_the_whole_population(baseline) -> None:
    compliance = baseline["compliance"]
    assert metrics.Filters().is_empty()
    assert len(metrics.apply_filters(compliance, metrics.Filters())) == len(
        compliance
    )


def test_plant_filter_narrows_compliance_and_events(baseline) -> None:
    events = baseline["events"]
    compliance = baseline["compliance"]
    filtered = metrics.apply_filters(
        compliance, _filters(plant_id="PLT-002")
    )
    assert len(filtered) > 0
    assert len(filtered) < len(compliance)
    assert len(
        metrics.apply_filters(events, _filters(plant_id="PLT-002"))
    ) == len(filtered)


def test_plant_with_most_alarm_volume(baseline) -> None:
    events = baseline["events"]
    plant_dist = metrics.alarm_counts_by(events, "plant_id")
    top = plant_dist.iloc[0]
    assert top["plant_id"] == "PLT-001"
    assert int(top["alarms"]) == 14_872


def test_machine_filter_is_subset_of_plant_filter(baseline) -> None:
    events = baseline["events"]
    by_plant = metrics.apply_filters(events, _filters(plant_id="PLT-002"))
    by_machine = metrics.apply_filters(
        events, _filters(plant_id="PLT-002", machine_id="MCH-020")
    )
    all_machines_plant = metrics.apply_filters(events, _filters(machine_id="MCH-020"))
    assert len(all_machines_plant) == len(by_machine)
    assert len(by_machine) < len(by_plant)


def test_machine_with_most_alarm_volume(baseline) -> None:
    events = baseline["events"]
    machines = baseline["machines"]
    dist = metrics.machine_alarm_distribution(events, machines)
    top = dist.iloc[0]
    assert top["machine_id"] == "MCH-014"
    assert int(top["alarm_count"]) == 1_034


def test_severity_filter_keeps_one_priority(baseline) -> None:
    compliance = baseline["compliance"]
    critical = metrics.apply_filters(compliance, _filters(severity="CRITICAL"))
    assert len(critical) > 0
    assert (critical["severity"] == "CRITICAL").all()
    assert len(critical) == 11_366


def test_date_filter_is_inclusive_on_start_and_exclusive_on_end(baseline) -> None:
    compliance = baseline["compliance"]
    window = metrics.apply_filters(
        compliance,
        _filters(start_date=date(2026, 10, 5), end_date=date(2026, 10, 10)),
        date_column="event_timestamp",
    )
    assert len(window) == 10_093
    lower = metrics.apply_filters(
        compliance, _filters(start_date=date(2026, 10, 1))
    )
    upper = metrics.apply_filters(
        compliance, _filters(end_date=date(2026, 10, 30))
    )
    assert len(lower) == 50_000
    assert len(upper) == 50_000


def test_date_filter_drops_out_of_window_rows(baseline) -> None:
    compliance = baseline["compliance"]
    window = metrics.apply_filters(
        compliance, _filters(start_date=date(2026, 10, 5), end_date=date(2026, 10, 10))
    )
    assert window["event_timestamp"].min().date() >= date(2026, 10, 5)
    assert window["event_timestamp"].max().date() < date(2026, 10, 11)


def test_filters_on_frames_without_optional_columns(baseline) -> None:
    events = baseline["events"]
    narrow = events[["machine_id", "severity"]]
    filtered = metrics.apply_filters(narrow, _filters(severity="CRITICAL"))
    assert set(filtered["severity"]) == {"CRITICAL"}


def test_apply_filters_ignores_unknown_filter_values(baseline) -> None:
    compliance = baseline["compliance"]
    empty = metrics.apply_filters(
        compliance, _filters(plant_id="PLT-999", machine_id="MCH-999")
    )
    assert len(empty) == 0


def test_filter_is_empty_only_when_all_dimensions_are_blank() -> None:
    assert metrics.Filters().is_empty()
    assert not metrics.Filters(plant_id="PLT-001").is_empty()
    assert not metrics.Filters(severity="HIGH").is_empty()
    assert not metrics.Filters(start_date=date(2026, 10, 1)).is_empty()
