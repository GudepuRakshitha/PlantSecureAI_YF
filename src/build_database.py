"""Build a portable SQLite export of the dataset.

    python src/build_database.py

The CSVs in ``data/`` stay authoritative; this module only materialises them
into ``data/industrial_safety.db`` using ``sql/schema.sql``.  It is useful for
ad-hoc SQL, BI tools and for proving that the relational model holds together
under SQLite's foreign-key enforcement.

The build is deliberately fail-loud: a foreign-key violation or a missing
baseline table raises instead of producing a quietly incomplete database.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, data_access, schema

# Baseline tables first (parents before children), then analytical outputs.
EXPORT_SPECS: tuple[schema.TableSpec, ...] = (
    *schema.BASELINE_TABLES,
    schema.SLA_BREACHES,
    schema.ANALYSIS_EXCEPTIONS,
)

# Tables whose absence is allowed (they are analyzer outputs).
OPTIONAL_TABLES = {schema.SLA_BREACHES.name, schema.ANALYSIS_EXCEPTIONS.name}


def _export_frame(spec: schema.TableSpec, data_dir: Path) -> pd.DataFrame | None:
    """Read one CSV and coerce it to the SQLite column contract."""
    path = data_dir / spec.filename
    if not path.exists():
        return None

    frame = data_access.read_table(spec, path)

    for column in spec.datetime_columns:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    for column in spec.boolean_columns:
        if column in frame.columns:
            frame[column] = (
                frame[column].astype("boolean").fillna(False).astype("int64")
            )
    return frame


def _sqlite_path(data_dir: Path, db_path: Path | None) -> Path:
    return Path(db_path) if db_path is not None else data_dir / config.DB_PATH.name


def build_database(
    data_dir: Path = config.DATA_DIR,
    db_path: Path | None = None,
) -> dict[str, int]:
    """Create the SQLite database and return a mapping of table -> row count."""
    data_dir = Path(data_dir)
    db_path = _sqlite_path(data_dir, db_path)
    schema_path = config.SQL_DIR / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(schema_path)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    counts: dict[str, int] = {}
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema_path.read_text(encoding="utf-8"))

        for spec in EXPORT_SPECS:
            frame = _export_frame(spec, data_dir)
            if frame is None:
                if spec.name in OPTIONAL_TABLES:
                    continue
                raise FileNotFoundError(data_dir / spec.filename)
            frame.to_sql(spec.name, connection, if_exists="append", index=False)
            counts[spec.name] = int(len(frame))

        connection.commit()

        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            sample = violations[:5]
            raise RuntimeError(f"foreign-key violations after export: {sample}")

        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    finally:
        connection.close()

    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--db-path", type=Path, default=None)
    args = parser.parse_args(argv)

    db_path = _sqlite_path(Path(args.data_dir), args.db_path)
    counts = build_database(args.data_dir, db_path)

    print("\n========== SQLITE EXPORT COMPLETE ==========")
    print(f"Database: {db_path}")
    for name, rows in counts.items():
        print(f"  {name:<24} {rows:>8,} rows")
    print(f"  {'TOTAL':<24} {sum(counts.values()):>8,} rows")
    print("  Foreign keys: OK")
    print("  Integrity   : OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
