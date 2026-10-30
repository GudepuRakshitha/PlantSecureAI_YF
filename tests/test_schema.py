"""Schema contract tests.

Every CSV, foreign key and enum is declared once in ``src/schema.py``; these
tests prove that the committed files still satisfy that contract.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import config, schema


def test_table_specs_have_unique_columns() -> None:
    for spec in (*schema.BASELINE_TABLES, schema.SLA_BREACHES, schema.ANALYSIS_EXCEPTIONS):
        assert len(spec.columns) == len(set(spec.columns)), spec.name


def test_primary_keys_are_part_of_the_contract() -> None:
    for spec in schema.BASELINE_TABLES:
        assert set(spec.primary_key) <= set(spec.columns)


def test_foreign_keys_reference_known_tables_and_columns() -> None:
    known = {spec.name: spec for spec in schema.BASELINE_TABLES}
    for spec in schema.BASELINE_TABLES:
        for foreign_key in spec.foreign_keys:
            assert foreign_key.ref_table in known
            target = known[foreign_key.ref_table]
            assert set(foreign_key.ref_columns) <= set(target.columns)
            assert set(foreign_key.columns) <= set(spec.columns)


def test_enum_columns_are_declared() -> None:
    for spec in schema.BASELINE_TABLES:
        for column, values in spec.enums.items():
            assert column in spec.columns
            assert values, f"{spec.name}.{column} has no enum values"


def test_baseline_csv_headers_match_the_contract() -> None:
    for spec in schema.BASELINE_TABLES:
        path = config.DATA_DIR / spec.filename
        header = pd.read_csv(path, nrows=0).columns.tolist()
        assert header == list(spec.columns), spec.filename


def test_analytical_output_headers_match_the_contract() -> None:
    for spec in (schema.SLA_BREACHES, schema.ANALYSIS_EXCEPTIONS):
        path = config.DATA_DIR / spec.filename
        header = pd.read_csv(path, nrows=0).columns.tolist()
        assert header == list(spec.columns), spec.filename


def test_scenario_files_exist_and_are_mapped() -> None:
    assert set(schema.SCENARIO_FILENAMES) == {
        spec.name for spec in schema.SCENARIO_TABLES
    }
    for filename in schema.SCENARIO_FILENAMES.values():
        assert (config.SCENARIO_DIR / filename).exists(), filename
    assert (config.SCENARIO_DIR / "ground_truth.csv").exists()


def test_scenario_tables_carry_case_id() -> None:
    for name in schema.SCENARIO_FILENAMES:
        filename = schema.SCENARIO_FILENAMES[name]
        header = pd.read_csv(config.SCENARIO_DIR / filename, nrows=0).columns
        assert schema.CASE_ID_COLUMN in header, filename


def test_seed_and_dataset_shape_are_frozen() -> None:
    assert config.SEED == 20261022
    assert config.TOTAL_EVENTS == 50_000
    assert config.DATASET_START.startswith("2026-10-01")


@pytest.mark.parametrize("spec", [schema.SLA_BREACHES, schema.ANALYSIS_EXCEPTIONS])
def test_outputs_are_marked_non_operational(spec: schema.TableSpec) -> None:
    # Routine SLA rows must be distinguishable from genuine anomalies.
    assert "is_routine_sla" in spec.columns
