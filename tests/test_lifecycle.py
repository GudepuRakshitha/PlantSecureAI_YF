"""Alarm lifecycle and transaction-consistency tests."""

from __future__ import annotations

import pandas as pd
import pytest

from src import config, data_access, metrics


def test_alarm_status_counts(baseline) -> None:
    events = baseline["events"]
    counts = events["alarm_status"].value_counts().to_dict()
    assert counts.get("ACKNOWLEDGED") == 3_832
    assert counts.get("CLEARED") == 41_199
    assert counts.get("UNACKNOWLEDGED") == 4_969
    assert "ACTIVE" not in counts


def test_acknowledgement_lifecycle_is_coherent(baseline) -> None:
    events = baseline["events"]
    acknowledged = events["acknowledged_at"].notna()
    unacknowledged = ~acknowledged

    assert int(unacknowledged.sum()) == 4_969
    assert events.loc[acknowledged, "alarm_status"].isin(
        ["ACKNOWLEDGED", "CLEARED"]
    ).all()
    assert events.loc[unacknowledged, "alarm_status"].eq("UNACKNOWLEDGED").all()
    assert events.loc[unacknowledged, "cleared_at"].isna().all()

    both = events["acknowledged_at"].notna() & events["cleared_at"].notna()
    assert (events.loc[both, "cleared_at"] >= events.loc[both, "acknowledged_at"]).all()


def test_acknowledged_at_cannot_precede_the_alarm(baseline) -> None:
    events = baseline["events"]
    acked = events[events["acknowledged_at"].notna()]
    assert (acked["acknowledged_at"] >= acked["event_timestamp"]).all()


def test_incident_lifecycle_is_consistent(baseline) -> None:
    incidents = baseline["incidents"]
    actions = baseline["actions"]

    assert len(incidents) == 169
    open_rows = incidents[incidents["status"].isin(["OPEN", "INVESTIGATING"])]
    closed_rows = incidents[incidents["status"] == "CLOSED"]
    assert (open_rows["closed_at"].isna()).all()
    assert closed_rows["closed_at"].notna().all()

    verified_by_incident = (
        actions[actions["status"] == "CLOSED"]
        .groupby("incident_id")["verification_status"]
        .agg(lambda values: bool((values == "VERIFIED").any()))
        .to_dict()
    )
    for incident_id, verified in verified_by_incident.items():
        if incident_id in set(closed_rows["incident_id"]):
            assert verified


def test_actions_lifecycle_consistency(baseline) -> None:
    actions = baseline["actions"]
    closed = actions[actions["status"] == "CLOSED"]
    assert (closed["verified_at"].notna()).all()
    assert (closed["effectiveness_status"] != "PENDING").all()
    open_rows = actions[actions["status"].isin(["OPEN", "IN_PROGRESS", "PENDING_VERIFICATION"])]
    assert (open_rows["verified_at"].isna()).all()


def test_incidents_reference_real_alarms_and_keep_trigger_context(baseline) -> None:
    incidents = baseline["incidents"]
    events = baseline["events"]
    known = set(events["alarm_event_id"])

    assert incidents["alarm_event_id"].isin(known).all()

    created = pd.to_datetime(incidents["created_at"]).to_numpy()
    triggered = pd.to_datetime(
        events.set_index("alarm_event_id")["event_timestamp"]
    )
    matched = triggered.loc[incidents["alarm_event_id"]].to_numpy()
    assert (created == matched).all()
