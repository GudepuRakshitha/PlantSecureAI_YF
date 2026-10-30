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

def test_developer_profile_renders_content_and_links() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    at.run()
    at.sidebar.radio[0].set_value("Developer Profile")
    at.run()
    assert not at.exception
    assert not at.error

    all_markdown = " ".join(block.value for block in at.markdown)
    assert "GUDEPU RAKSHITHA REDDY" in all_markdown
    assert "Computer Science Engineer | AI/ML Enthusiast" in all_markdown
    assert "About Me" in all_markdown
    assert "Alliance University, Bengaluru" in all_markdown
    assert "8.9/10" in all_markdown
    assert "7 research papers" in all_markdown
    assert "100+ technical certifications" in all_markdown
    assert "Technical Expertise" in all_markdown
    assert "linkedin.com/in/gudepu-rakshitha-reddy-516aa72a9" in all_markdown
    assert "github.com/GudepuRakshitha" in all_markdown
    assert "researchgate.net/profile/Rakshitha-Reddy-Gudepu" in all_markdown
    assert "blogger.com/profile/08555579845123121571" in all_markdown


def test_about_developer_button_and_back_navigation() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    at.run()

    # Click 'About the Developer' button
    about_btn = next(b for b in at.button if b.label == "About the Developer")
    about_btn.click()
    at.run()
    assert not at.exception
    assert at.sidebar.radio[0].value == "Developer Profile"

    # Click 'Back to Dashboard' button
    back_btn = next(b for b in at.button if "Back to Dashboard" in b.label)
    back_btn.click()
    at.run()
    assert not at.exception
    assert at.sidebar.radio[0].value == "Overview"


def test_attribution_button_navigation() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    at.run()

    # Click attribution button
    attr_btn = next(b for b in at.button if "Developed by Gudepu Rakshitha Reddy" in b.label)
    attr_btn.click()
    at.run()
    assert not at.exception
    assert at.sidebar.radio[0].value == "Developer Profile"

def test_header_and_sidebar_alignment() -> None:
    at = AppTest.from_file(APP_PATH, default_timeout=180)
    at.run()
    assert not at.exception
    assert not at.error

    all_markdown = " ".join(block.value for block in at.markdown)
    # 1. Main heading and subtitle are fully present
    assert "Industrial Safety Monitoring" in all_markdown
    assert "Plant operations, alarm intelligence and incident oversight." in all_markdown

    # 2. No Deploy or Refresh data buttons
    button_labels = [b.label for b in at.button]
    assert "Refresh data" not in button_labels
    assert "Deploy" not in button_labels

    # 3. Sidebar branding intact
    assert "SAFEGUARD" in all_markdown
    assert "Industrial Safety Intelligence" in all_markdown

