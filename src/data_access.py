"""Dataset access and population definitions.

Populations
-----------
``baseline``
    The clean synthetic production-style dataset in ``data/*.csv``.  Used for
    every operational KPI and for the compliance numbers reported in the
    README.

``scenario``
    Baseline rows plus the records in ``data/scenarios/injected_*.csv``.  It
    exists only to test the detector and is always labelled as a test
    population in the dashboard.  Scenario rows carry a ``case_id``; baseline
    rows have ``case_id = None``.

Nothing here imports Streamlit, so the same preparation code is reused by the
analyzer, the validators and the tests.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src import config, detection, metrics, schema

# Tables present in the scenario population, mapped to their file names.
_SCENARIO_SPECS = {
    spec.name: schema.SCENARIO_FILENAMES[spec.name] for spec in schema.SCENARIO_TABLES
}


def fingerprint(mode: str, data_dir: Path = config.DATA_DIR) -> str:
    """Cheap cache key that changes whenever a source file changes."""
    data_dir = Path(data_dir)
    paths = [data_dir / spec.filename for spec in schema.BASELINE_TABLES]
    paths.append(data_dir / "scenarios" / "ground_truth.csv")
    if mode == "scenario":
        paths.extend(
            data_dir / "scenarios" / filename
            for filename in _SCENARIO_SPECS.values()
        )
    parts = []
    for path in paths:
        if path.exists():
            stat = path.stat()
            parts.append(f"{path.name}:{stat.st_mtime_ns}:{stat.st_size}")
        else:
            parts.append(f"{path.name}:missing")
    return "|".join(parts)


def read_table(
    spec: schema.TableSpec,
    path: Path,
    *,
    parse_dates: bool = True,
) -> pd.DataFrame:
    """Read one CSV using the shared schema contract."""
    frame = pd.read_csv(path)
    if parse_dates:
        for column in spec.datetime_columns:
            if column in frame.columns:
                frame[column] = pd.to_datetime(
                    frame[column], format="%Y-%m-%d %H:%M:%S", errors="coerce"
                )
    for column in spec.boolean_columns:
        if column in frame.columns:
            frame[column] = frame[column].astype("boolean")
    return frame


def load_population(
    mode: str = "baseline", data_dir: Path = config.DATA_DIR
) -> dict[str, pd.DataFrame]:
    """Load the baseline or scenario population as plain frames."""
    if mode not in ("baseline", "scenario"):
        raise ValueError(f"unknown population: {mode}")
    data_dir = Path(data_dir)

    frames: dict[str, pd.DataFrame] = {}
    for spec in schema.BASELINE_TABLES:
        path = data_dir / spec.filename
        if not path.exists():
            raise FileNotFoundError(path)
        frames[spec.name] = read_table(spec, path)

    if mode == "baseline":
        return frames

    scenario_dir = data_dir / "scenarios"
    for name, filename in _SCENARIO_SPECS.items():
        path = scenario_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)
        spec = schema.TABLES_BY_NAME[name]
        extra = read_table(spec, path)
        extra["case_id"] = extra["case_id"].astype("string")
        extra["dataset"] = "scenario"
        base = frames[name].copy()
        base["case_id"] = pd.NA
        base["dataset"] = "baseline"
        frames[name] = pd.concat([base, extra], ignore_index=True)

    truth_path = scenario_dir / "ground_truth.csv"
    frames["ground_truth"] = pd.read_csv(truth_path)

    # Non-scenario tables still get a dataset marker for consistency.
    for name, frame in frames.items():
        if "dataset" not in frame.columns:
            frame["dataset"] = "baseline"
    return frames


def enrich_machines(
    machines: pd.DataFrame,
    plants: pd.DataFrame,
    zones: pd.DataFrame,
) -> pd.DataFrame:
    """Attach plant, plant name, zone name and zone risk to machines."""
    enriched = machines.merge(
        plants[["plant_id", "plant_name", "location"]],
        on="plant_id",
        how="left",
        validate="many_to_one",
    )
    zone_columns = ["zone_id", "zone_name", "risk_level"]
    enriched = enriched.merge(
        zones[zone_columns],
        on="zone_id",
        how="left",
        validate="many_to_one",
    )
    return enriched


def prepare_population(
    mode: str = "baseline", data_dir: Path = config.DATA_DIR
) -> dict[str, object]:
    """Return every enriched frame and metric-ready table for one population."""
    frames = load_population(mode, data_dir)

    machines = enrich_machines(
        frames["machines"], frames["plants"], frames["safety_zones"]
    )
    definitions = frames["alarm_definitions"]

    machine_context = machines[
        ["machine_id", "machine_name", "plant_id", "plant_name", "zone_id"]
    ]
    events = frames["alarm_events"].merge(
        machine_context, on="machine_id", how="left", validate="many_to_one"
    )
    events["event_date"] = pd.to_datetime(events["event_timestamp"]).dt.date
    events["event_hour"] = pd.to_datetime(events["event_timestamp"]).dt.hour

    compliance = metrics.build_compliance(
        frames["alarm_events"],
        frames["acknowledgements"],
        definitions,
        machines,
    )
    compliance["plant_name"] = compliance["plant_id"].map(
        machines.drop_duplicates("plant_id").set_index("plant_id")["plant_name"]
    )

    incidents = frames["incidents"].merge(
        machine_context[["machine_id", "machine_name", "plant_id", "plant_name"]],
        on="machine_id",
        how="left",
        suffixes=("", "_machine"),
        validate="many_to_one",
    )

    action_context = frames["incidents"][
        ["incident_id", "severity", "plant_id", "machine_id", "status"]
    ].rename(columns={"status": "incident_status"})
    actions = frames["corrective_actions"].merge(
        action_context, on="incident_id", how="left", validate="many_to_one"
    )
    actions = actions.merge(
        machine_context[["machine_id", "machine_name", "plant_id", "plant_name"]],
        on="machine_id",
        how="left",
        suffixes=("", "_machine"),
        validate="many_to_one",
    )

    exceptions = detection.detect_anomalies(
        events,
        frames["acknowledgements"],
        frames["interlocks"],
        frames["incidents"],
        frames["corrective_actions"],
        machines,
    )

    breaches = metrics.sla_breaches(compliance)

    result: dict[str, object] = {
        "mode": mode,
        "label": config.DATASET_LABELS[mode],
        "description": config.DATASET_DESCRIPTIONS[mode],
        "frames": frames,
        "plants": frames["plants"],
        "zones": frames["safety_zones"],
        "machines": machines,
        "definitions": definitions,
        "shifts": frames["operator_shifts"],
        "events": events,
        "compliance": compliance,
        "incidents": incidents,
        "actions": actions,
        "interlocks": frames["interlocks"],
        "exceptions": exceptions,
        "sla_breaches": breaches,
        "unacknowledged": metrics.unacknowledged_alarms(compliance),
        "ack_metrics": metrics.ack_compliance_metrics(compliance),
        "incident_metrics": metrics.incident_statistics(
            frames["incidents"],
            frames["corrective_actions"],
        ),
        "action_metrics": metrics.corrective_action_statistics(
            frames["corrective_actions"]
        ),
        "exception_metrics": metrics.exception_kpis(
            pd.concat(
                [
                    exceptions,
                    breaches.assign(exception_type="LATE_ACKNOWLEDGEMENT"),
                ],
                ignore_index=True,
            )
            if not breaches.empty
            else exceptions
        ),
        "row_counts": {
            spec.name: int(len(frames[spec.name]))
            for spec in schema.BASELINE_TABLES
            if spec.name in frames
        },
    }

    if mode == "scenario" and "ground_truth" in frames:
        result["ground_truth"] = frames["ground_truth"]
        result["detection_report"] = detection.evaluate_detection(
            exceptions, frames["ground_truth"]
        )
    else:
        result["ground_truth"] = pd.DataFrame(
            columns=list(schema.GROUND_TRUTH.columns)
        )
        result["detection_report"] = None

    return result
