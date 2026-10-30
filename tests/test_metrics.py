"""Metric layer tests — the single source of truth for every dashboard KPI."""

from __future__ import annotations

import pandas as pd
import pytest

from src import config, data_access, metrics


def test_ack_compliance_metrics_are_activation_denominated(baseline) -> None:
    compliance = baseline["compliance"]
    ack = metrics.ack_compliance_metrics(compliance)

    assert ack["total_activations"] == 50_000
    assert ack["total_acknowledged"] == 45_031
    assert ack["total_unacknowledged"] == 4_969
    assert ack["on_time_acknowledgements"] == 36_101
    assert ack["late_acknowledgements"] == 8_930

    assert ack["acknowledgement_rate_pct"] == pytest.approx(90.06)
    assert ack["on_time_compliance_pct"] == pytest.approx(72.20)
    assert ack["late_acknowledgement_pct"] == pytest.approx(17.86)
    assert ack["unacknowledged_pct"] == pytest.approx(9.94)
    assert ack["median_response_minutes"] == pytest.approx(4.0)
    assert ack["p95_response_minutes"] == pytest.approx(13.0)


def test_compliance_sums_are_internal_consistent(baseline) -> None:
    compliance = baseline["compliance"]
    ack = metrics.ack_compliance_metrics(compliance)

    assert ack["total_acknowledged"] + ack["total_unacknowledged"] == (
        ack["total_activations"]
    )
    assert ack["on_time_acknowledgements"] + ack["late_acknowledgements"] == (
        ack["total_acknowledged"]
    )


def test_sla_breaches_are_routine_only(baseline) -> None:
    sla = metrics.sla_breaches(baseline["compliance"])
    assert len(sla) == 8_930
    assert sla["is_routine_sla"].all()
    assert (sla["overdue_minutes"] > 0).all()
    assert (sla["response_minutes"] > sla["acknowledgement_limit_minutes"]).all()
    assert list(sla["is_routine_sla"]) == [True] * len(sla)


def test_unacknowledged_alarms_are_separate_from_late(baseline) -> None:
    unacknowledged = metrics.unacknowledged_alarms(baseline["compliance"])
    assert len(unacknowledged) == 4_969
    late = metrics.sla_breaches(baseline["compliance"])
    assert len(unacknowledged) + len(late) > 0


def test_priority_compliance_sums_to_populations(baseline) -> None:
    compliance = baseline["compliance"]
    priority = metrics.priority_compliance(compliance)

    assert set(priority["severity"]) == set(config.SEVERITIES)
    assert int(priority["activations"].sum()) == 50_000
    assert int(priority["on_time"].sum()) == 36_101
    assert int(priority["late"].sum()) == 8_930
    assert int(priority["unacknowledged"].sum()) == 4_969


def test_alarm_counts_and_severity_distribution(baseline) -> None:
    events = baseline["events"]
    counts = metrics.alarm_counts(events)
    assert counts["total_alarm_activations"] == 50_000
    assert counts["critical_alarms"] == 11_366
    assert counts["high_alarms"] == 13_929
    assert counts["distinct_machines"] == 60

    severity = metrics.severity_distribution(events)
    assert int(severity["count"].sum()) == 50_000
    assert severity["percentage"].sum() == pytest.approx(100.0)


def test_daily_trend_covers_the_observation_window(baseline) -> None:
    trend = metrics.daily_alarm_trend(baseline["events"])
    assert list(trend.columns) == ["date", "alarms", "critical", "high"]
    assert int(trend["alarms"].sum()) == 50_000


def test_response_time_trend_uses_acknowledged_subset(baseline) -> None:
    trend = metrics.response_time_trend(baseline["compliance"])
    assert not trend.empty
    assert "median_response_minutes" in trend.columns
    assert "p95_response_minutes" in trend.columns


def test_chattering_and_flood_detection_return_frames(baseline) -> None:
    events = baseline["events"]
    machines = baseline["machines"]
    plants = baseline["plants"]
    definitions = baseline["definitions"]

    chattering = metrics.detect_chattering(
        events, config.THRESHOLDS, definitions=definitions, machines=machines
    )
    assert "machine_id" in chattering.columns
    assert len(chattering) == 200

    floods = metrics.detect_floods(events, config.THRESHOLDS, plants=plants)
    assert "window_start" in floods.columns
    assert len(floods) == 87


def test_incident_and_action_statistics(baseline) -> None:
    incidents = baseline["incidents"]
    actions = baseline["actions"]
    stats = metrics.incident_statistics(incidents, actions)
    assert stats["total_incidents"] == 169
    assert stats["open_incidents"] == 58

    action_stats = metrics.corrective_action_statistics(actions)
    assert action_stats["total_actions"] == 169


def test_exception_kpis_split_routine_and_genuine(baseline) -> None:
    sla = metrics.sla_breaches(baseline["compliance"])
    routine_kpis = metrics.exception_kpis(
        sla.assign(exception_type="LATE_ACKNOWLEDGEMENT")
    )
    assert routine_kpis["routine_sla_breaches"] > 0
    assert routine_kpis["genuine_anomalies"] == 0
    assert routine_kpis["genuine_anomalies"] + routine_kpis["routine_sla_breaches"] > 0
