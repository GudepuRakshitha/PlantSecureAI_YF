"""Export and database-build tests."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pandas as pd

from src import build_database, config, safety_analyzer


def test_build_database_produces_valid_export(tmp_path) -> None:
    db_path = tmp_path / "industrial_safety.db"
    counts = build_database.build_database(config.DATA_DIR, db_path)

    assert counts["plants"] == 4
    assert counts["alarm_events"] == 50_000
    assert counts["acknowledgements"] == 45_031
    assert counts["sla_breaches"] == 8_930
    assert counts["analysis_exceptions"] == 5

    with sqlite3.connect(db_path) as connection:
        totals = connection.execute(
            "SELECT COUNT(*), SUM(is_on_time), SUM(is_late), SUM(is_unacknowledged) "
            "FROM vw_ack_compliance"
        ).fetchone()
        assert totals[0] == 50_000
        assert totals[1] == 36_101
        assert totals[2] == 8_930
        assert totals[3] == 4_969

        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_analyzer_write_outputs_to_target_directory(tmp_path) -> None:
    data_dir = tmp_path / "data"
    shutil.copytree(
        config.DATA_DIR,
        data_dir,
        ignore=shutil.ignore_patterns("*.db", "cache", "exports"),
    )

    summary = safety_analyzer.analyze(data_dir, write=True)

    assert (data_dir / "sla_breaches.csv").exists()
    assert (data_dir / "analysis_exceptions.csv").exists()
    assert (data_dir / "analysis_summary.json").exists()

    sla = pd.read_csv(data_dir / "sla_breaches.csv")
    exceptions = pd.read_csv(data_dir / "analysis_exceptions.csv")
    assert len(sla) == 8_930
    assert len(exceptions) == 5
