"""Determinism and shape tests for the data generators."""

from __future__ import annotations

import pandas as pd

from src import config, event_generator, generator, schema, transaction_generator


def test_master_generator_is_deterministic() -> None:
    first = generator.build_master(config.SEED)
    second = generator.build_master(config.SEED)
    for name in first:
        pd.testing.assert_frame_equal(first[name], second[name], check_dtype=False)


def test_master_generator_matches_committed_files() -> None:
    generated = generator.build_master(config.SEED)
    for name, frame in generated.items():
        spec = schema.TABLES_BY_NAME[name]
        committed = pd.read_csv(config.DATA_DIR / spec.filename)
        pd.testing.assert_frame_equal(
            frame.reset_index(drop=True),
            committed.reset_index(drop=True),
            check_dtype=False,
        )


def test_event_generator_is_deterministic_and_bounded() -> None:
    definitions = generator.build_master(config.SEED)["alarm_definitions"]
    first = event_generator.build_events(
        definitions, seed=config.SEED, total_events=250
    )
    second = event_generator.build_events(
        definitions, seed=config.SEED, total_events=250
    )
    pd.testing.assert_frame_equal(first, second)

    assert len(first) == 250
    assert first["alarm_event_id"].is_unique
    assert set(first["severity"]) <= set(config.SEVERITIES)
    assert first["event_timestamp"].min() >= pd.Timestamp(config.DATASET_START)
    assert first["event_timestamp"].max() < pd.Timestamp(config.DATASET_END)


def test_transaction_generator_produces_consistent_lifecycles() -> None:
    master = generator.build_master(config.SEED)
    events = event_generator.build_events(
        master["alarm_definitions"], seed=config.SEED, total_events=400
    )
    transactions = transaction_generator.build_transactions(
        master["plants"], master["machines"], events, seed=config.SEED
    )

    assert set(transactions) == {
        "operator_shifts",
        "acknowledgements",
        "incidents",
        "corrective_actions",
        "alarm_events",
    }
    assert len(transactions["alarm_events"]) == len(events)
    assert len(transactions["acknowledgements"]) <= len(events)
    assert len(transactions["incidents"]) <= len(events)

    acknowledgements = transactions["acknowledgements"]
    assert acknowledgements["acknowledgement_id"].is_unique
    assert acknowledgements["alarm_event_id"].is_unique
    assert acknowledgements["ack_timestamp"].min() >= events["event_timestamp"].min()


def test_scenario_ground_truth_has_five_cases_and_three_controls() -> None:
    truth = pd.read_csv(config.SCENARIO_DIR / "ground_truth.csv")
    anomaly_cases = set(config.EXPECTED_CASE_IDS)
    control_cases = set(config.NEGATIVE_CONTROL_CASE_IDS)
    assert set(truth["case_id"]) == anomaly_cases | control_cases
    assert int((truth["is_anomaly"] == True).sum()) == 5  # noqa: E712
    assert set(truth.loc[truth["is_anomaly"], "case_id"]) == anomaly_cases
    assert set(truth.loc[truth["is_anomaly"] == False, "case_id"]) == control_cases


def test_scenario_injection_uses_case_ids() -> None:
    for filename in schema.SCENARIO_FILENAMES.values():
        frame = pd.read_csv(config.SCENARIO_DIR / filename)
        assert frame["case_id"].notna().all(), filename
        assert set(frame["case_id"]) <= {
            *config.EXPECTED_CASE_IDS,
            *config.NEGATIVE_CONTROL_CASE_IDS,
        }, filename
