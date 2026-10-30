"""Streamlit dashboard smoke tests (AppTest) and filter behaviour tests."""

from __future__ import annotations

import re

from streamlit.testing.v1 import AppTest

from src import config, metrics

APP_PATH = str(config.PROJECT_ROOT / "dashboard" / "app.py")
PAGES = (
    "Overview",
    "Alarm Monitoring",
    "Acknowledgement Analytics",
    "Incident Management",
    "Corrective Actions",
    "Exception Analysis",
    "Data Explorer",
)


def _kpi_values(at) -> dict[str, str]:
    pattern = re.compile(
        r'class="kpi-label">([^<]+)</div>.*?class="kpi-value">([^<]+)</div>',
        re.S,
    )
    values: dict[str, str] = {}
    for block in at.markdown:
        for label, value in pattern.findall(block.value):
            values[label.strip()] = value.strip()
    return values


def _selectbox(at, label: str):
    return next(element for element in at.selectbox if element.label == label)


def test_dashboard_renders_every_page_without_exceptions() -> None:
    for page in PAGES:
        at = AppTest.from_file(APP_PATH, default_timeout=180)
        at.run()
        at.sidebar.radio[0].set_value(page)
        at.run()
        assert not at.exception, f"{page} raised {at.exception}"
        assert not at.error, f"{page} rendered an error: {[e.value for e in at.error]}"


def test_overview_kpis_match_the_shared_metric_layer(baseline) -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    at.run()
    values = _kpi_values(at)
    ack = metrics.ack_compliance_metrics(baseline["compliance"])

    assert values["Total Alarm Activations"] == f"{ack['total_activations']:,}"
    assert values["Acknowledgement Rate"] == f"{ack['acknowledgement_rate_pct']:.1f}%"
    assert values["On-time Compliance"] == f"{ack['on_time_compliance_pct']:.1f}%"
    assert values["Unacknowledged Alarms"] == f"{ack['total_unacknowledged']:,}"
    assert values["Genuine Anomalies"] == "0"
    assert values["Open Incidents"] != ""


def test_global_filters_change_kpis_and_reset_restores(baseline) -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    at.run()

    plant_box = _selectbox(at, "Plant")
    plant_label = next(
        option for option in plant_box.options if option.startswith("PLT-002")
    )
    plant_box.set_value(plant_label)
    at.run()
    assert _kpi_values(at)["Total Alarm Activations"] == "12,565"

    machine_box = _selectbox(at, "Machine")
    machine_labels = [label for label in machine_box.options if label.startswith("MCH-020")]
    machine_box.set_value(machine_labels[0])
    at.run()
    assert _kpi_values(at)["Total Alarm Activations"] == "1,008"

    reset_button = next(b for b in at.button if b.label == "Reset")
    reset_button.click()
    at.run()
    assert _kpi_values(at)["Total Alarm Activations"] == "50,000"


def test_scenario_view_reports_detector_results(scenario) -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    at.run()
    at.sidebar.selectbox[0].set_value("Scenario test")
    at.run()
    at.sidebar.radio[0].set_value("Exception Analysis")
    at.run()

    values = _kpi_values(at)
    assert values["Genuine Anomalies"] == "5"
    assert not at.exception
    assert not at.error


def test_data_explorer_paginates_and_searches() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    at.run()
    at.sidebar.radio[0].set_value("Data Explorer")
    at.run()

    table_box = _selectbox(at, "Table")
    assert len(table_box.options) == 12
    table_box.set_value("Incidents")
    at.run()

    page_size = _selectbox(at, "Rows per page")
    page_size.set_value(25)
    at.run()

    assert len(at.dataframe) >= 1
    assert len(at.dataframe[0].value) == 25
    assert not at.exception
