"""SAFEGUARD — Industrial Safety Intelligence dashboard.

Run with::

    streamlit run dashboard/app.py

The dashboard is a presentation layer only.  Every KPI and every chart series
comes from ``src.metrics``; every population comes from ``src.data_access``.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Allow ``streamlit run dashboard/app.py`` from a fresh clone.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard import components as ui  # noqa: E402
from dashboard import theme  # noqa: E402
from src import config, data_access, metrics, schema  # noqa: E402

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="SAFEGUARD | Industrial Safety Monitoring",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.inject_css()

PAGES = (
    "Overview",
    "Alarm Monitoring",
    "Acknowledgement Analytics",
    "Incident Management",
    "Corrective Actions",
    "Exception Analysis",
    "Data Explorer",
)

ALL_PLANTS = "All plants"
ALL_MACHINES = "All machines"
ALL_SEVERITIES = "All severities"

MODE_OPTIONS = {
    "Baseline (production)": "baseline",
    "Scenario test": "scenario",
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False, max_entries=4)
def load_population(mode: str, fingerprint: str) -> dict[str, object]:
    """Cache the prepared population, keyed by mode and source-file state."""
    # ``fingerprint`` is part of the cache key; touching a CSV invalidates it.
    _ = fingerprint
    return data_access.prepare_population(mode, config.DATA_DIR)


def latest_data_timestamp(mode: str) -> datetime:
    """Return the newest source-file modification time for the active mode."""
    paths = [config.DATA_DIR / spec.filename for spec in schema.BASELINE_TABLES]
    if mode == "scenario":
        paths += list(config.SCENARIO_DIR.glob("*.csv"))
    stamps = [path.stat().st_mtime for path in paths if path.exists()]
    return datetime.fromtimestamp(max(stamps)) if stamps else datetime.now()


def enrich_exceptions(
    exceptions: pd.DataFrame, frames: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Attach names and the best available record timestamp to a finding."""
    result = exceptions.copy()
    if result.empty:
        result["machine_name"] = pd.Series(dtype="object")
        result["plant_name"] = pd.Series(dtype="object")
        result["record_timestamp"] = pd.Series(dtype="datetime64[ns]")
        return result

    machines = frames["machines"].drop_duplicates("machine_id").set_index("machine_id")
    plants = frames["plants"].drop_duplicates("plant_id").set_index("plant_id")
    result["machine_name"] = result["machine_id"].map(machines["machine_name"])
    result["plant_name"] = result["plant_id"].map(plants["plant_name"])

    ack_times = (
        frames["acknowledgements"]
        .drop_duplicates("acknowledgement_id")
        .set_index("acknowledgement_id")["ack_timestamp"]
    )
    event_times = (
        frames["alarm_events"]
        .drop_duplicates("alarm_event_id")
        .set_index("alarm_event_id")["event_timestamp"]
    )
    incident_times = (
        frames["incidents"]
        .drop_duplicates("incident_id")
        .set_index("incident_id")["created_at"]
    )
    action_times = (
        frames["corrective_actions"]
        .drop_duplicates("action_id")
        .set_index("action_id")["created_at"]
    )

    def timestamp_for(entity: object, record_id: object) -> object:
        entity = str(entity)
        if entity == "Acknowledgement":
            return ack_times.get(record_id, pd.NaT)
        if entity == "AlarmEvent":
            return event_times.get(record_id, pd.NaT)
        if entity == "Incident":
            return incident_times.get(record_id, pd.NaT)
        if entity == "CorrectiveAction":
            return action_times.get(record_id, pd.NaT)
        return pd.NaT

    result["record_timestamp"] = [
        timestamp_for(entity, record_id)
        for entity, record_id in zip(result["entity"], result["record_id"])
    ]
    return result


def attach_sla_context(
    sla: pd.DataFrame, machines: pd.DataFrame
) -> pd.DataFrame:
    """Attach machine and plant names to the routine SLA-breach table."""
    if sla.empty:
        return sla.assign(machine_name=pd.Series(dtype="object"),
                          plant_name=pd.Series(dtype="object"))
    context = machines[["machine_id", "machine_name", "plant_name"]].drop_duplicates(
        "machine_id"
    )
    return sla.merge(context, on="machine_id", how="left", validate="many_to_one")


# ---------------------------------------------------------------------------
# Layout chrome
# ---------------------------------------------------------------------------


def render_sidebar() -> tuple[str, str]:
    """Draw the sidebar and return (page, dataset mode)."""
    with st.sidebar:
        st.markdown(
            """
            <div class="brand">
              <div class="brand-mark">
                <svg width="19" height="19" viewBox="0 0 24 24" fill="none"
                     xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2.5 3.8 6v5.9c0 4.9 3.5 8.5 8.2 9.6 4.7-1.1 8.2-4.7 8.2-9.6V6L12 2.5Z"
                        stroke="#FFFFFF" stroke-width="1.6" stroke-linejoin="round"/>
                  <path d="m8.2 12.1 2.5 2.6 5.1-5.4" stroke="#FFFFFF"
                        stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <div>
                <div class="brand-name">SAFEGUARD</div>
                <div class="brand-sub">Industrial Safety Intelligence</div>
              </div>
            </div>
            <div class="sidebar-divider"></div>
            <div class="sidebar-label">Workspace</div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Navigation",
            PAGES,
            key="navigation",
            label_visibility="collapsed",
        )

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">Data view</div>', unsafe_allow_html=True)
        dataset_label = st.selectbox(
            "Dataset",
            list(MODE_OPTIONS),
            key="dataset_view",
            label_visibility="collapsed",
        )
        mode = MODE_OPTIONS[dataset_label]
        caption = (
            "Clean production-style population."
            if mode == "baseline"
            else "Baseline + injected test cases."
        )
        st.caption(caption)

    return page, mode


def render_header(mode: str) -> None:
    """Draw the page header, dataset indicator and refresh control."""
    dataset_label = config.DATASET_LABELS[mode]
    tone = "info" if mode == "baseline" else "warn"
    refreshed = latest_data_timestamp(mode).strftime("%d %b %Y · %H:%M")

    left, right = st.columns([5.2, 1.45], vertical_alignment="top")
    with left:
        st.markdown(
            """
            <div class="page-title">Industrial Safety Monitoring</div>
            <div class="page-subtitle">Plant operations, alarm intelligence and
            incident oversight.</div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f'<div class="header-meta">{ui.badge(dataset_label, tone)}'
            f'<div class="meta-line">Refreshed {refreshed}</div></div>',
            unsafe_allow_html=True,
        )

    if mode == "scenario":
        ui.notice(
            "<strong>Scenario test view.</strong> The population is baseline data "
            "plus five injected anomalies and three negative controls. KPIs here "
            "exist to inspect detector behaviour and are not production metrics.",
            tone="warn",
        )


def _machine_options(machines: pd.DataFrame, plant_id: str | None) -> dict[str, str]:
    subset = machines if plant_id is None else machines[machines["plant_id"] == plant_id]
    subset = subset.sort_values("machine_id")
    return {
        f"{row.machine_id} · {row.machine_name}": row.machine_id
        for row in subset.itertuples(index=False)
    }


def reset_filters(
    plant_key: str,
    machine_key: str,
    severity_key: str,
    date_key: str,
    default_dates: tuple,
) -> None:
    """Widget callback: restore every filter before the script re-runs."""
    st.session_state[plant_key] = ALL_PLANTS
    st.session_state[machine_key] = ALL_MACHINES
    st.session_state[severity_key] = ALL_SEVERITIES
    st.session_state[date_key] = default_dates


def render_filters(data: dict[str, object], mode: str) -> tuple[metrics.Filters, int]:
    """Draw the global filter bar and return the selected filters."""
    plants = data["plants"]
    machines = data["machines"]
    events = data["events"]

    plant_options = {ALL_PLANTS: None}
    for row in plants.sort_values("plant_id").itertuples(index=False):
        plant_options[f"{row.plant_id} · {row.plant_name}"] = row.plant_id
    severity_options = [ALL_SEVERITIES, *config.SEVERITIES]

    min_date = pd.to_datetime(events["event_timestamp"]).min().date()
    max_date = pd.to_datetime(events["event_timestamp"]).max().date()

    plant_key = f"filter_plant_{mode}"
    machine_key = f"filter_machine_{mode}"
    severity_key = f"filter_severity_{mode}"
    date_key = f"filter_dates_{mode}"

    if plant_key not in st.session_state:
        st.session_state[plant_key] = ALL_PLANTS
    if severity_key not in st.session_state:
        st.session_state[severity_key] = ALL_SEVERITIES
    if date_key not in st.session_state:
        st.session_state[date_key] = (min_date, max_date)

    with st.container(border=True):
        cols = st.columns([1.35, 1.75, 1.15, 1.75, 0.72], vertical_alignment="bottom")
        with cols[0]:
            plant_label = st.selectbox("Plant", list(plant_options), key=plant_key)
        plant_id = plant_options.get(plant_label)

        machine_options = {ALL_MACHINES: None}
        machine_options.update(_machine_options(machines, plant_id))
        if st.session_state.get(machine_key) not in machine_options:
            st.session_state[machine_key] = ALL_MACHINES

        with cols[1]:
            machine_label = st.selectbox(
                "Machine", list(machine_options), key=machine_key
            )
        machine_id = machine_options.get(machine_label)

        with cols[2]:
            severity_label = st.selectbox(
                "Alarm severity", severity_options, key=severity_key
            )
        severity = None if severity_label == ALL_SEVERITIES else severity_label

        with cols[3]:
            dates = st.date_input(
                "Date range",
                min_value=min_date,
                max_value=max_date,
                key=date_key,
                format="DD/MM/YYYY",
            )

        with cols[4]:
            st.button(
                "Reset",
                key=f"reset_filters_{mode}",
                width="stretch",
                on_click=reset_filters,
                args=(
                    plant_key,
                    machine_key,
                    severity_key,
                    date_key,
                    (min_date, max_date),
                ),
            )

    if isinstance(dates, (tuple, list)) and len(dates) == 2:
        start_date, end_date = dates
    elif isinstance(dates, (tuple, list)) and len(dates) == 1:
        start_date = end_date = dates[0]
    elif isinstance(dates, (tuple, list)) and not dates:
        start_date, end_date = min_date, max_date
    else:
        start_date = end_date = dates

    if start_date > end_date:
        start_date, end_date = end_date, start_date
    full_range = start_date <= min_date and end_date >= max_date

    filters = metrics.Filters(
        plant_id=plant_id,
        machine_id=machine_id,
        severity=severity,
        start_date=None if full_range else start_date,
        end_date=None if full_range else end_date,
    )
    return filters, int(len(events))


def build_state(
    data: dict[str, object],
    filters: metrics.Filters,
) -> dict[str, object]:
    """Apply one filter selection consistently to every population."""
    frames = data["frames"]
    events = metrics.apply_filters(
        data["events"], filters, date_column="event_timestamp"
    )
    compliance = metrics.apply_filters(
        data["compliance"], filters, date_column="event_timestamp"
    )
    incidents = metrics.apply_filters(
        data["incidents"], filters, date_column="created_at"
    )
    actions = metrics.apply_filters(
        data["actions"], filters, date_column="created_at"
    )

    exceptions = enrich_exceptions(data["exceptions"], frames)
    # Plant/machine/severity filters use the shared predicate.  The date filter
    # is applied manually so findings without a source timestamp (interlocks)
    # are not silently dropped from the exception view.
    exceptions = metrics.apply_filters(
        exceptions,
        metrics.Filters(
            plant_id=filters.plant_id,
            machine_id=filters.machine_id,
            severity=filters.severity,
        ),
    )
    if filters.start_date or filters.end_date:
        timestamps = exceptions["record_timestamp"]
        in_range = pd.Series(True, index=exceptions.index)
        if filters.start_date:
            in_range &= timestamps >= pd.Timestamp(filters.start_date)
        if filters.end_date:
            in_range &= timestamps < (
                pd.Timestamp(filters.end_date) + pd.Timedelta(days=1)
            )
        exceptions = exceptions[timestamps.isna() | in_range]

    sla = attach_sla_context(metrics.sla_breaches(compliance), data["machines"])

    return {
        "events": events,
        "compliance": compliance,
        "incidents": incidents,
        "actions": actions,
        "exceptions": exceptions,
        "sla": sla,
        "unacknowledged": compliance[compliance["ack_status"] == "UNACKNOWLEDGED"],
    }


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def page_overview(data: dict[str, object], state: dict[str, object]) -> None:
    events = state["events"]
    compliance = state["compliance"]
    incidents = state["incidents"]
    actions = state["actions"]
    exceptions = state["exceptions"]

    ack = metrics.ack_compliance_metrics(compliance)
    incident_stats = metrics.incident_statistics(incidents, actions)

    ui.kpi_grid(
        [
            {
                "label": "Total Alarm Activations",
                "value": ui.fmt_int(ack["total_activations"]),
                "desc": "In the selected scope",
                "status": f"{events['machine_id'].nunique():,} machines reporting",
                "tone": "neutral",
            },
            {
                "label": "Acknowledgement Rate",
                "value": ui.fmt_pct(ack["acknowledgement_rate_pct"]),
                "desc": "Acknowledged ÷ activations",
                "status": f"{ack['total_acknowledged']:,} acknowledged",
                "tone": "neutral",
            },
            {
                "label": "On-time Compliance",
                "value": ui.fmt_pct(ack["on_time_compliance_pct"]),
                "desc": "On time ÷ all activations",
                "status": f"{ack['on_time_acknowledgements']:,} within limit",
                "tone": "neutral",
            },
            {
                "label": "Unacknowledged Alarms",
                "value": ui.fmt_int(ack["total_unacknowledged"]),
                "desc": f"{ack['unacknowledged_pct']:.1f}% of activations",
                "status": "No acknowledgement logged",
                "tone": "bad" if ack["total_unacknowledged"] else "good",
            },
            {
                "label": "Genuine Anomalies",
                "value": ui.fmt_int(len(exceptions)),
                "desc": "Injected / detected findings",
                "status": "None detected" if exceptions.empty else "Requires review",
                "tone": "good" if exceptions.empty else "bad",
            },
            {
                "label": "Open Incidents",
                "value": ui.fmt_int(incident_stats["open_incidents"]),
                "desc": "Currently open",
                "status": f"{incident_stats['investigating_incidents']} investigating",
                "tone": "warn" if incident_stats["open_incidents"] else "good",
            },
        ]
    )

    trend = metrics.daily_alarm_trend(events)
    severity = metrics.severity_distribution(events)
    left, right = st.columns([2.05, 1])

    with left:
        if trend.empty:
            ui.empty_state("No alarm activity", "No activations match the current filters.")
        else:
            ui.plot(
                ui.trend_line(
                    trend,
                    "date",
                    {"Alarm activations": "alarms", "Critical": "critical"},
                    "Daily alarm trend",
                    colors=[theme.COLORS["accent"], theme.SEVERITY_COLORS["CRITICAL"]],
                    height=326,
                    y_title="Activations",
                    fill=False,
                )
            )

    with right:
        if severity["count"].sum() == 0:
            ui.empty_state("No severity data", "No activations match the current filters.")
        else:
            ui.plot(
                ui.donut(
                    severity,
                    "severity",
                    "count",
                    "Severity distribution",
                    theme.SEVERITY_COLORS,
                    order=config.SEVERITIES,
                    height=326,
                    total_label="alarms",
                )
            )

    plant_dist = metrics.alarm_counts_by(events, "plant_name")
    status_counts = (
        events["alarm_status"]
        .value_counts()
        .reindex(list(config.ALARM_STATUSES), fill_value=0)
        .rename_axis("alarm_status")
        .reset_index(name="alarms")
    )
    priority = metrics.priority_compliance(compliance)
    performance = priority.melt(
        id_vars="severity",
        value_vars=["on_time", "late", "unacknowledged"],
        var_name="outcome",
        value_name="alarms",
    )
    performance["outcome"] = performance["outcome"].map(
        {
            "on_time": "ON_TIME",
            "late": "LATE",
            "unacknowledged": "UNACKNOWLEDGED",
        }
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if plant_dist.empty:
            ui.empty_state("No plant data", "No activations match the current filters.")
        else:
            ui.plot(
                ui.ranking_bar(
                    plant_dist,
                    "plant_name",
                    "alarms",
                    "Alarm volume by plant",
                    height=286,
                )
            )
    with col2:
        if status_counts["alarms"].sum() == 0:
            ui.empty_state("No status data", "No activations match the current filters.")
        else:
            ui.plot(
                ui.donut(
                    status_counts,
                    "alarm_status",
                    "alarms",
                    "Alarm lifecycle status",
                    theme.ALARM_STATUS_COLORS,
                    order=config.ALARM_STATUSES,
                    height=286,
                    total_label="alarms",
                )
            )
    with col3:
        if performance["alarms"].sum() == 0:
            ui.empty_state("No acknowledgement data", "No activations in scope.")
        else:
            ui.plot(
                ui.stacked_bar(
                    performance,
                    "severity",
                    "alarms",
                    "outcome",
                    "Acknowledgement outcome by severity",
                    theme.ACK_COLORS,
                    height=286,
                    y_title="Share of activations",
                    percent=True,
                )
            )

    # Data-derived insights only; nothing here is hard-coded.
    insight_items: list[dict[str, str]] = []
    if not plant_dist.empty:
        top_plant = plant_dist.iloc[0]
        insight_items.append(
            {
                "label": "Highest alarm volume",
                "text": f"{top_plant['plant_name']} · {int(top_plant['alarms']):,} activations",
                "tone": "neutral",
            }
        )
    if severity["count"].sum() > 0:
        top_severity = severity.sort_values("count", ascending=False).iloc[0]
        insight_items.append(
            {
                "label": "Most frequent severity",
                "text": f"{top_severity['severity']} · {int(top_severity['count']):,} alarms "
                f"({top_severity['percentage']:.1f}%)",
                "tone": "neutral",
            }
        )
    machine_dist = metrics.machine_alarm_distribution(events, data["machines"])
    if not machine_dist.empty:
        top_machine = machine_dist.iloc[0]
        insight_items.append(
            {
                "label": "Busiest machine",
                "text": f"{top_machine['machine_id']} · {top_machine['machine_name']} · "
                f"{int(top_machine['alarm_count']):,} alarms",
                "tone": "neutral",
            }
        )
    acknowledged = compliance.dropna(subset=["response_minutes"])
    if not acknowledged.empty:
        slowest = acknowledged.loc[acknowledged["response_minutes"].idxmax()]
        insight_items.append(
            {
                "label": "Slowest acknowledgement",
                "text": f"{slowest['machine_name']} · {slowest['response_minutes']:.1f} minutes "
                f"(limit {slowest['acknowledgement_limit_minutes']:.0f} min)",
                "tone": "warn",
            }
        )
    insight_items.append(
        {
            "label": "Unresolved anomalies",
            "text": (
                "None — the selected population is clean"
                if exceptions.empty
                else f"{len(exceptions)} genuine finding(s) require review"
            ),
            "tone": "good" if exceptions.empty else "bad",
        }
    )

    ui.section("Operational insights", "Calculated from the filtered population")
    ui.insight_list(insight_items)


# ---------------------------------------------------------------------------
# Alarm monitoring
# ---------------------------------------------------------------------------


def page_alarms(data: dict[str, object], state: dict[str, object]) -> None:
    events = state["events"]
    definitions = data["definitions"]
    machines = data["machines"]
    plants = data["plants"]

    counts = metrics.alarm_counts(events)
    chattering = metrics.detect_chattering(
        events, config.THRESHOLDS, definitions=definitions, machines=machines
    )
    floods = metrics.detect_floods(events, config.THRESHOLDS, plants=plants)

    ui.kpi_grid(
        [
            {
                "label": "Alarm Activations",
                "value": ui.fmt_int(counts["total_alarm_activations"]),
                "desc": f"{counts['distinct_definitions']:,} alarm definitions",
                "status": f"{counts['distinct_machines']:,} machines",
                "tone": "neutral",
            },
            {
                "label": "Critical Alarms",
                "value": ui.fmt_int(counts["critical_alarms"]),
                "desc": "Severity CRITICAL",
                "status": f"{counts['high_alarms']:,} HIGH",
                "tone": "bad" if counts["critical_alarms"] else "neutral",
            },
            {
                "label": "Chattering Pairs",
                "value": ui.fmt_int(len(chattering)),
                "desc": f"{config.THRESHOLDS.chatter_n}+ alarms in "
                f"{config.THRESHOLDS.chatter_window_minutes} min",
                "status": "Machine + definition combinations",
                "tone": "warn" if len(chattering) else "good",
            },
            {
                "label": "Alarm Floods",
                "value": ui.fmt_int(len(floods)),
                "desc": f"{config.THRESHOLDS.flood_alarm_count}+ alarms in "
                f"{config.THRESHOLDS.flood_window_minutes} min",
                "status": "Plant-level episodes",
                "tone": "warn" if len(floods) else "good",
            },
        ]
    )

    trend = metrics.daily_alarm_trend(events)
    severity = metrics.severity_distribution(events)
    left, right = st.columns([2.05, 1])
    with left:
        if trend.empty:
            ui.empty_state("No alarm activity", "No activations match the current filters.")
        else:
            ui.plot(
                ui.trend_line(
                    trend,
                    "date",
                    {"Alarm activations": "alarms"},
                    "Alarm trend over time",
                    colors=[theme.COLORS["accent"]],
                    height=320,
                    y_title="Activations",
                    fill=True,
                )
            )
    with right:
        if severity["count"].sum() == 0:
            ui.empty_state("No severity data", "No activations match the current filters.")
        else:
            ui.plot(
                ui.ranking_bar(
                    severity,
                    "severity",
                    "count",
                    "Alarm volume by severity",
                    height=320,
                )
            )

    plant_dist = metrics.alarm_counts_by(events, "plant_name")
    machine_dist = metrics.machine_alarm_distribution(events, machines)
    col1, col2 = st.columns(2)
    with col1:
        if plant_dist.empty:
            ui.empty_state("No plant data", "No activations match the current filters.")
        else:
            ui.plot(
                ui.ranking_bar(
                    plant_dist,
                    "plant_name",
                    "alarms",
                    "Plant-wise alarm volume",
                    height=330,
                )
            )
    with col2:
        if machine_dist.empty:
            ui.empty_state("No machine data", "No activations match the current filters.")
        else:
            ui.plot(
                ui.ranking_bar(
                    machine_dist,
                    "machine_name",
                    "alarm_count",
                    "Top machines by alarm volume",
                    color=theme.COLORS["teal"],
                    height=330,
                    top=12,
                )
            )

    ui.section(
        "Chattering detection",
        "Repeated alarms for the same machine and definition inside the configured window",
    )
    if chattering.empty:
        ui.empty_state(
            "No chattering detected",
            "No machine/definition pair exceeds the configured N-in-T threshold.",
        )
    else:
        query = st.text_input(
            "Search chattering pairs",
            key="chatter_search",
            placeholder="Machine, alarm name or severity",
        )
        filtered = ui.search_frame(
            chattering,
            query,
            ["machine_id", "machine_name", "alarm_name", "severity"],
        )
        ui.show_table(
            filtered,
            columns=[
                "machine_id",
                "machine_name",
                "alarm_name",
                "severity",
                "max_alarms_in_window",
                "episodes",
                "last_episode",
            ],
            labels={
                "machine_id": "Machine ID",
                "machine_name": "Machine",
                "alarm_name": "Alarm",
                "max_alarms_in_window": "Max in window",
                "last_episode": "Last episode",
            },
            height=320,
            key="chatter_table",
        )

    ui.section(
        "Alarm flood detection",
        "Plant-level episodes above the configured alarms-per-window threshold",
    )
    if floods.empty:
        ui.empty_state(
            "No alarm floods detected",
            "No plant exceeds the configured flood threshold in the selected scope.",
        )
    else:
        ui.plot(
            ui.event_scatter(
                floods,
                "window_end",
                "plant_name",
                "alarm_count",
                "plant_name",
                "Largest flood episodes",
                height=300,
                top=40,
            )
        )
        ui.show_table(
            floods,
            columns=[
                "plant_name",
                "window_start",
                "window_end",
                "alarm_count",
                "critical_count",
            ],
            labels={
                "plant_name": "Plant",
                "window_start": "Window start",
                "window_end": "Window end",
                "alarm_count": "Alarms",
                "critical_count": "Critical",
            },
            height=280,
            key="flood_table",
        )

    ui.section("Alarm activation log", "Most recent activations in the filtered population")
    query = st.text_input(
        "Search activations",
        key="alarm_search",
        placeholder="Alarm event ID, machine, severity or status",
    )
    activations = ui.search_frame(
        events.sort_values("event_timestamp", ascending=False),
        query,
        ["alarm_event_id", "machine_id", "machine_name", "severity", "alarm_status"],
    )
    activations = activations[
        [
            "alarm_event_id",
            "event_timestamp",
            "machine_id",
            "machine_name",
            "plant_name",
            "alarm_definition_id",
            "severity",
            "alarm_status",
            "state_transition",
        ]
    ]
    ui.show_table(
        activations.head(300),
        labels={
            "alarm_event_id": "Alarm event",
            "event_timestamp": "Activated",
            "machine_id": "Machine ID",
            "machine_name": "Machine",
            "plant_name": "Plant",
            "alarm_definition_id": "Definition",
            "alarm_status": "Status",
            "state_transition": "State transition",
        },
        height=380,
        key="activation_table",
    )
    st.caption(
        f"Showing the latest {min(len(activations), 300):,} of {len(activations):,} "
        "matching activations. Download the full table below."
    )
    ui.download_button(
        activations,
        "alarm_activations.csv",
        "Download activations",
        key="download_activations",
    )


# ---------------------------------------------------------------------------
# Acknowledgement analytics
# ---------------------------------------------------------------------------


def page_acknowledgements(data: dict[str, object], state: dict[str, object]) -> None:
    compliance = state["compliance"]
    ack = metrics.ack_compliance_metrics(compliance)

    ui.kpi_grid(
        [
            {
                "label": "Alarm Activations",
                "value": ui.fmt_int(ack["total_activations"]),
                "desc": "Denominator for every rate",
                "status": "Activation-based",
                "tone": "neutral",
            },
            {
                "label": "Acknowledged",
                "value": ui.fmt_int(ack["total_acknowledged"]),
                "desc": f"{ack['acknowledgement_rate_pct']:.1f}% of activations",
                "status": "Acknowledgement logged",
                "tone": "neutral",
            },
            {
                "label": "Unacknowledged",
                "value": ui.fmt_int(ack["total_unacknowledged"]),
                "desc": f"{ack['unacknowledged_pct']:.1f}% of activations",
                "status": "Counted as non-compliant",
                "tone": "bad" if ack["total_unacknowledged"] else "good",
            },
            {
                "label": "On-time",
                "value": ui.fmt_int(ack["on_time_acknowledgements"]),
                "desc": f"{ack['on_time_compliance_pct']:.1f}% of activations",
                "status": "Within definition limit",
                "tone": "neutral",
            },
            {
                "label": "Late",
                "value": ui.fmt_int(ack["late_acknowledgements"]),
                "desc": f"{ack['late_acknowledgement_pct']:.1f}% of activations",
                "status": "Routine SLA breach",
                "tone": "warn" if ack["late_acknowledgements"] else "good",
            },
            {
                "label": "Median Response",
                "value": ui.fmt_minutes(ack["median_response_minutes"]),
                "desc": "Across acknowledged alarms",
                "status": "MTTA",
                "tone": "neutral",
            },
            {
                "label": "95th Percentile",
                "value": ui.fmt_minutes(ack["p95_response_minutes"]),
                "desc": "Across acknowledged alarms",
                "status": "Tail response time",
                "tone": "neutral",
            },
        ]
    )

    funnel_frame = pd.DataFrame(
        {
            "stage": ["Alarm activations", "Acknowledged", "Acknowledged on time"],
            "count": [
                ack["total_activations"],
                ack["total_acknowledged"],
                ack["on_time_acknowledgements"],
            ],
        }
    )
    response = metrics.response_time_trend(compliance)
    priority = metrics.priority_compliance(compliance)
    performance = priority.melt(
        id_vars="severity",
        value_vars=["on_time", "late", "unacknowledged"],
        var_name="outcome",
        value_name="alarms",
    )
    performance["outcome"] = performance["outcome"].map(
        {"on_time": "ON_TIME", "late": "LATE", "unacknowledged": "UNACKNOWLEDGED"}
    )

    col1, col2 = st.columns([1, 1.35])
    with col1:
        fig = px.funnel(
            funnel_frame,
            x="count",
            y="stage",
            color_discrete_sequence=[theme.COLORS["accent"]],
        )
        fig.update_traces(
            textinfo="value+percent initial",
            marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>%{x:,} alarms<extra></extra>",
        )
        fig.update_layout(yaxis_title=None)
        ui.plot(theme.style_figure(fig, "Acknowledgement funnel", height=318))
    with col2:
        histogram_frame = compliance[
            compliance["ack_status"].isin(["ON_TIME", "LATE"])
        ]
        if histogram_frame.empty:
            ui.empty_state(
                "No response times",
                "No acknowledged alarms match the current filters.",
            )
        else:
            ui.plot(
                ui.histogram(
                    histogram_frame,
                    "response_minutes",
                    "Response-time distribution",
                    color=theme.COLORS["accent"],
                    nbins=15,
                    x_title="Response time (minutes)",
                    y_title="Acknowledgements",
                    height=318,
                )
            )

    col1, col2 = st.columns(2)
    with col1:
        if performance["alarms"].sum() == 0:
            ui.empty_state("No compliance data", "No activations in scope.")
        else:
            ui.plot(
                ui.stacked_bar(
                    performance,
                    "severity",
                    "alarms",
                    "outcome",
                    "Priority-wise acknowledgement compliance",
                    theme.ACK_COLORS,
                    height=320,
                    y_title="Share of activations",
                    percent=True,
                )
            )
    with col2:
        if response.empty:
            ui.empty_state(
                "No response trend", "No acknowledged alarms match the current filters."
            )
        else:
            ui.plot(
                ui.trend_line(
                    response,
                    "date",
                    {
                        "Median response": "median_response_minutes",
                        "P95 response": "p95_response_minutes",
                    },
                    "Daily response-time trend",
                    colors=[theme.COLORS["accent"], theme.SEVERITY_COLORS["HIGH"]],
                    height=320,
                    y_title="Minutes",
                )
            )

    ui.section(
        "Unacknowledged alarms",
        "Activations without an acknowledgement record — included in every compliance rate",
    )
    unacknowledged = state["unacknowledged"]
    if unacknowledged.empty:
        ui.empty_state(
            "No unacknowledged alarms",
            "Every activation in scope has an acknowledgement.",
        )
    else:
        ui.show_table(
            unacknowledged.sort_values("event_timestamp", ascending=False).head(200),
            columns=[
                "alarm_event_id",
                "event_timestamp",
                "plant_name",
                "machine_name",
                "severity",
                "alarm_status",
                "acknowledgement_limit_minutes",
            ],
            labels={
                "alarm_event_id": "Alarm event",
                "event_timestamp": "Activated",
                "plant_name": "Plant",
                "machine_name": "Machine",
                "alarm_status": "Status",
                "acknowledgement_limit_minutes": "Limit (min)",
            },
            height=300,
            key="unack_table",
        )
        ui.download_button(
            unacknowledged,
            "unacknowledged_alarms.csv",
            "Download unacknowledged alarms",
            key="download_unack",
        )

    ui.section(
        "Late acknowledgements",
        "Routine SLA breaches — kept separate from genuine anomalies",
    )
    sla = state["sla"]
    if sla.empty:
        ui.empty_state(
            "No SLA breaches",
            "No acknowledgement exceeds its alarm-definition limit in this scope.",
        )
    else:
        ui.show_table(
            sla.sort_values("overdue_minutes", ascending=False).head(200),
            columns=[
                "record_id",
                "event_timestamp",
                "plant_name",
                "machine_name",
                "severity",
                "response_minutes",
                "acknowledgement_limit_minutes",
                "overdue_minutes",
            ],
            labels={
                "record_id": "Alarm event",
                "event_timestamp": "Activated",
                "plant_name": "Plant",
                "machine_name": "Machine",
                "response_minutes": "Response (min)",
                "acknowledgement_limit_minutes": "Limit (min)",
                "overdue_minutes": "Overdue (min)",
            },
            formats={"response_minutes": "%.1f", "overdue_minutes": "%.1f"},
            height=300,
            key="sla_table_ack",
        )
        ui.download_button(
            sla,
            "sla_breaches.csv",
            "Download SLA breaches",
            key="download_sla_ack",
        )


# ---------------------------------------------------------------------------
# Incident management
# ---------------------------------------------------------------------------


def page_incidents(data: dict[str, object], state: dict[str, object]) -> None:
    incidents = state["incidents"]
    actions = state["actions"]
    stats = metrics.incident_statistics(incidents, actions)

    ui.kpi_grid(
        [
            {
                "label": "Total Incidents",
                "value": ui.fmt_int(stats["total_incidents"]),
                "desc": "Raised from qualifying alarms",
                "status": "Full history in scope",
                "tone": "neutral",
            },
            {
                "label": "Open",
                "value": ui.fmt_int(stats["open_incidents"]),
                "desc": "Awaiting investigation",
                "status": "No closure recorded",
                "tone": "bad" if stats["open_incidents"] else "good",
            },
            {
                "label": "Investigating",
                "value": ui.fmt_int(stats["investigating_incidents"]),
                "desc": "Active investigation",
                "status": "In progress",
                "tone": "warn" if stats["investigating_incidents"] else "neutral",
            },
            {
                "label": "Closed",
                "value": ui.fmt_int(stats["closed_incidents"]),
                "desc": f"{stats['closed_pct']:.1f}% of incidents",
                "status": f"{stats['closed_without_verified_action']} missing verification",
                "tone": "good" if stats["closed_without_verified_action"] == 0 else "bad",
            },
            {
                "label": "Mean Resolution",
                "value": ui.fmt_hours(stats["mean_resolution_hours"]),
                "desc": "Closed incidents only",
                "status": f"Median {stats['median_resolution_hours']:.1f} h",
                "tone": "neutral",
            },
        ]
    )

    severity = metrics.severity_distribution(incidents)
    if len(severity):
        severity = severity.rename(columns={"count": "incidents", "percentage": "share"})
    status_by_severity = (
        incidents.groupby(["severity", "status"])
        .size()
        .reset_index(name="incidents")
    )
    plant_dist = incidents.groupby("plant_name", dropna=False).size().reset_index(
        name="incidents"
    )
    machine_dist = (
        incidents.groupby(["machine_id", "machine_name"], dropna=False)
        .size()
        .reset_index(name="incidents")
    )
    trend = metrics.incident_trends(incidents)

    col1, col2 = st.columns([1, 1.05])
    with col1:
        if incidents.empty:
            ui.empty_state("No incidents", "No incidents match the current filters.")
        else:
            ui.plot(
                ui.donut(
                    severity,
                    "severity",
                    "incidents",
                    "Incident severity distribution",
                    theme.SEVERITY_COLORS,
                    order=config.SEVERITIES,
                    height=320,
                    total_label="incidents",
                )
            )
    with col2:
        if status_by_severity.empty:
            ui.empty_state("No lifecycle data", "No incidents match the current filters.")
        else:
            ui.plot(
                ui.stacked_bar(
                    status_by_severity,
                    "severity",
                    "incidents",
                    "status",
                    "Incident lifecycle by severity",
                    theme.INCIDENT_COLORS,
                    height=320,
                    y_title="Incidents",
                )
            )

    col1, col2, col3 = st.columns([1, 1.2, 1.4])
    with col1:
        if plant_dist.empty:
            ui.empty_state("No plant data", "No incidents match the current filters.")
        else:
            ui.plot(
                ui.ranking_bar(
                    plant_dist,
                    "plant_name",
                    "incidents",
                    "Incidents by plant",
                    height=300,
                )
            )
    with col2:
        if machine_dist.empty:
            ui.empty_state("No machine data", "No incidents match the current filters.")
        else:
            ui.plot(
                ui.ranking_bar(
                    machine_dist,
                    "machine_name",
                    "incidents",
                    "Top machines by incidents",
                    color=theme.COLORS["teal"],
                    height=300,
                    top=10,
                )
            )
    with col3:
        if trend.empty:
            ui.empty_state("No incident trend", "No incidents match the current filters.")
        else:
            ui.plot(
                ui.trend_line(
                    trend,
                    "date",
                    {"Opened": "opened", "Closed": "closed"},
                    "Incident trend",
                    colors=[theme.SEVERITY_COLORS["HIGH"], theme.COLORS["teal"]],
                    height=300,
                    y_title="Incidents",
                )
            )

    ui.section(
        "Incident history",
        "Every record is traceable to its originating alarm event",
    )
    if incidents.empty:
        ui.empty_state("No incidents", "No incidents match the current filters.")
        return

    history = incidents.copy()
    history["resolution_hours"] = (
        (history["closed_at"] - history["created_at"]).dt.total_seconds() / 3600
    ).round(2)
    history = history.sort_values("created_at", ascending=False)

    query = st.text_input(
        "Search incidents",
        key="incident_search",
        placeholder="Incident ID, machine, status or alarm event",
    )
    history = ui.search_frame(
        history,
        query,
        ["incident_id", "alarm_event_id", "machine_id", "machine_name", "status"],
    )
    ui.show_table(
        history,
        columns=[
            "incident_id",
            "created_at",
            "closed_at",
            "status",
            "severity",
            "plant_name",
            "machine_name",
            "alarm_event_id",
            "resolution_hours",
        ],
        labels={
            "incident_id": "Incident",
            "created_at": "Created",
            "closed_at": "Closed",
            "plant_name": "Plant",
            "machine_name": "Machine",
            "alarm_event_id": "Originating alarm",
            "resolution_hours": "Resolution (h)",
        },
        formats={"resolution_hours": "%.2f"},
        height=360,
        key="incident_table",
    )
    ui.download_button(
        history, "incidents.csv", "Download incidents", key="download_incidents"
    )
    st.caption(
        "Lifecycle rule: CLOSED incidents carry a closed_at timestamp and at least "
        "one verified corrective action. Open and investigating incidents never do."
    )


# ---------------------------------------------------------------------------
# Corrective actions
# ---------------------------------------------------------------------------


def page_actions(data: dict[str, object], state: dict[str, object]) -> None:
    actions = state["actions"]
    stats = metrics.corrective_action_statistics(actions)

    ui.kpi_grid(
        [
            {
                "label": "Total Actions",
                "value": ui.fmt_int(stats["total_actions"]),
                "desc": "Linked to incidents",
                "status": "One or more per incident",
                "tone": "neutral",
            },
            {
                "label": "Open",
                "value": ui.fmt_int(stats["open_actions"]),
                "desc": "Not yet started",
                "status": "Action required",
                "tone": "bad" if stats["open_actions"] else "good",
            },
            {
                "label": "In Progress",
                "value": ui.fmt_int(stats["in_progress_actions"]),
                "desc": "Work underway",
                "status": "Being executed",
                "tone": "warn" if stats["in_progress_actions"] else "neutral",
            },
            {
                "label": "Pending Verification",
                "value": ui.fmt_int(stats["pending_verification_actions"]),
                "desc": "Awaiting effectiveness check",
                "status": "Verification backlog",
                "tone": "warn" if stats["pending_verification_actions"] else "good",
            },
            {
                "label": "Closed",
                "value": ui.fmt_int(stats["closed_actions"]),
                "desc": "Completed actions",
                "status": f"{stats['verified_actions']:,} verified",
                "tone": "good" if stats["closed_actions"] else "neutral",
            },
            {
                "label": "Verified",
                "value": ui.fmt_int(stats["verified_actions"]),
                "desc": "Verification successful",
                "status": f"{stats['pending_verification']:,} pending",
                "tone": "good" if stats["verified_actions"] else "neutral",
            },
        ]
    )

    status_counts = (
        actions["status"]
        .value_counts()
        .reindex(list(config.ACTION_STATUSES), fill_value=0)
        .rename_axis("status")
        .reset_index(name="actions")
    )
    verification = (
        actions["verification_status"]
        .value_counts()
        .reindex(list(config.VERIFICATION_STATUSES), fill_value=0)
        .rename_axis("verification_status")
        .reset_index(name="actions")
    )
    effectiveness = (
        actions["effectiveness_status"]
        .value_counts()
        .reindex(list(config.EFFECTIVENESS_STATUSES), fill_value=0)
        .rename_axis("effectiveness_status")
        .reset_index(name="actions")
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        if actions.empty:
            ui.empty_state("No corrective actions", "No actions match the current filters.")
        else:
            ui.plot(
                ui.donut(
                    status_counts,
                    "status",
                    "actions",
                    "Action status",
                    theme.ACTION_COLORS,
                    order=config.ACTION_STATUSES,
                    height=308,
                    total_label="actions",
                )
            )
    with col2:
        if actions.empty:
            ui.empty_state("No verification data", "No actions match the current filters.")
        else:
            ui.plot(
                ui.ranking_bar(
                    verification,
                    "verification_status",
                    "actions",
                    "Verification status",
                    height=308,
                )
            )
    with col3:
        if actions.empty:
            ui.empty_state("No effectiveness data", "No actions match the current filters.")
        else:
            ui.plot(
                ui.ranking_bar(
                    effectiveness,
                    "effectiveness_status",
                    "actions",
                    "Effectiveness outcome",
                    color=theme.COLORS["teal"],
                    height=308,
                )
            )

    ui.section(
        "Corrective action register",
        "Lifecycle-consistent with the parent incident",
    )
    if actions.empty:
        ui.empty_state("No corrective actions", "No actions match the current filters.")
        return

    register = actions.sort_values("created_at", ascending=False)
    query = st.text_input(
        "Search corrective actions",
        key="action_search",
        placeholder="Action ID, incident, assignee or status",
    )
    register = ui.search_frame(
        register,
        query,
        ["action_id", "incident_id", "assigned_to", "status", "verification_status"],
    )
    ui.show_table(
        register,
        columns=[
            "action_id",
            "incident_id",
            "action_description",
            "assigned_to",
            "status",
            "verification_status",
            "effectiveness_status",
            "created_at",
            "closed_at",
            "verified_at",
        ],
        labels={
            "action_id": "Action",
            "incident_id": "Incident",
            "action_description": "Description",
            "assigned_to": "Assigned to",
            "verification_status": "Verification",
            "effectiveness_status": "Effectiveness",
            "created_at": "Created",
            "closed_at": "Closed",
            "verified_at": "Verified",
        },
        height=380,
        key="action_table",
    )
    ui.download_button(
        register,
        "corrective_actions.csv",
        "Download corrective actions",
        key="download_actions",
    )


# ---------------------------------------------------------------------------
# Exception analysis
# ---------------------------------------------------------------------------


def page_exceptions(data: dict[str, object], state: dict[str, object]) -> None:
    exceptions = state["exceptions"]
    sla = state["sla"]
    unacknowledged = state["unacknowledged"]
    report = data.get("detection_report")
    mode = data["mode"]

    ui.kpi_grid(
        [
            {
                "label": "SLA Breaches",
                "value": ui.fmt_int(len(sla)),
                "desc": "Routine late acknowledgements",
                "status": "Operational follow-up",
                "tone": "warn" if len(sla) else "good",
            },
            {
                "label": "Unacknowledged Alarms",
                "value": ui.fmt_int(len(unacknowledged)),
                "desc": "No acknowledgement logged",
                "status": "Tracked as a KPI",
                "tone": "bad" if len(unacknowledged) else "good",
            },
            {
                "label": "Genuine Anomalies",
                "value": ui.fmt_int(len(exceptions)),
                "desc": "Data-quality / safety findings",
                "status": "None detected" if exceptions.empty else "Requires review",
                "tone": "good" if exceptions.empty else "bad",
            },
            {
                "label": "Anomaly Types",
                "value": ui.fmt_int(exceptions["exception_type"].nunique() if not exceptions.empty else 0),
                "desc": "Distinct rule violations",
                "status": "Separated from SLA noise",
                "tone": "neutral",
            },
        ]
    )

    if mode == "baseline":
        ui.notice(
            "<strong>Clean baseline.</strong> The production-style population is "
            "validated to contain zero genuine anomalies. Switch the data view to "
            "<em>Scenario test</em> to inspect detector behaviour against the five "
            "injected cases.",
            tone="info",
        )
    elif report:
        status = (
            "All cases detected"
            if not report["missing_cases"] and report["false_positives"] == 0
            else "Detector needs review"
        )
        ui.notice(
            f"<strong>Detector score:</strong> {report['true_positives']} true positives, "
            f"{report['false_positives']} false positives, {report['false_negatives']} false "
            f"negatives · precision {report['precision']:.2f} / recall {report['recall']:.2f} "
            f"· {status}.",
            tone="warn" if status == "Detector needs review" else "info",
        )

    ui.section(
        "A. Routine SLA breaches",
        "Late acknowledgements are operational performance issues, not data anomalies",
    )
    if sla.empty:
        ui.empty_state(
            "No SLA breaches",
            "No acknowledgement exceeds its definition limit in the current scope.",
        )
    else:
        col1, col2 = st.columns([1, 2.1])
        with col1:
            ui.plot(
                ui.histogram(
                    sla,
                    "overdue_minutes",
                    "Overdue distribution",
                    color=theme.ACK_COLORS["LATE"],
                    nbins=12,
                    x_title="Minutes past the limit",
                    y_title="Breaches",
                    height=300,
                )
            )
        with col2:
            ui.show_table(
                sla.sort_values("overdue_minutes", ascending=False).head(200),
                columns=[
                    "record_id",
                    "event_timestamp",
                    "plant_name",
                    "machine_name",
                    "severity",
                    "response_minutes",
                    "acknowledgement_limit_minutes",
                    "overdue_minutes",
                ],
                labels={
                    "record_id": "Alarm event",
                    "event_timestamp": "Activated",
                    "plant_name": "Plant",
                    "machine_name": "Machine",
                    "response_minutes": "Response (min)",
                    "acknowledgement_limit_minutes": "Limit (min)",
                    "overdue_minutes": "Overdue (min)",
                },
                formats={"response_minutes": "%.1f", "overdue_minutes": "%.1f"},
                height=300,
                key="sla_table_exceptions",
            )
        ui.download_button(
            sla, "sla_breaches.csv", "Download SLA breaches", key="download_sla"
        )

    if not unacknowledged.empty:
        st.caption(
            f"{len(unacknowledged):,} unacknowledged alarms are tracked separately as a "
            "compliance KPI and are not classified as anomalies."
        )

    ui.section(
        "B. Genuine anomalies",
        "Injected data-quality and safety violations, separated from routine SLA noise",
    )
    if exceptions.empty:
        ui.empty_state(
            "No genuine anomalies",
            "The detector found no rule violations in the selected scope.",
        )
        return

    type_counts = (
        exceptions["exception_type"]
        .value_counts()
        .rename_axis("exception_type")
        .reset_index(name="findings")
    )
    ui.plot(
        ui.ranking_bar(
            type_counts,
            "exception_type",
            "findings",
            "Anomalies by type",
            color=theme.SEVERITY_COLORS["CRITICAL"],
            height=300,
        )
    )

    ui.show_table(
        exceptions.sort_values(["severity", "exception_type"]),
        columns=[
            "exception_type",
            "severity",
            "plant_name",
            "machine_name",
            "record_id",
            "case_id",
            "record_timestamp",
            "entity",
            "description",
        ],
        labels={
            "exception_type": "Exception type",
            "plant_name": "Plant",
            "machine_name": "Machine",
            "record_id": "Record ID",
            "case_id": "Case",
            "record_timestamp": "Source timestamp",
            "entity": "Entity",
        },
        height=340,
        key="exception_table",
    )
    ui.download_button(
        exceptions,
        "analysis_exceptions.csv",
        "Download genuine anomalies",
        key="download_exceptions",
    )


# ---------------------------------------------------------------------------
# Data explorer
# ---------------------------------------------------------------------------


def explorer_tables(
    data: dict[str, object], state: dict[str, object]
) -> dict[str, pd.DataFrame]:
    """Tables available to the explorer, already filtered where applicable."""
    machines = data["machines"]
    filtered_machines = metrics.apply_filters(
        machines, data["_filters"]
    ) if data.get("_filters") else machines

    return {
        "Alarm activations": state["events"],
        "Acknowledgements": state["compliance"],
        "Incidents": state["incidents"],
        "Corrective actions": state["actions"],
        "SLA breaches": state["sla"],
        "Genuine anomalies": state["exceptions"],
        "Machines": filtered_machines,
        "Plants": data["plants"],
        "Safety zones": data["zones"],
        "Interlocks": data["interlocks"],
        "Alarm definitions": data["definitions"],
        "Operator shifts": metrics.apply_filters(
            data["shifts"], data["_filters"]
        ) if data.get("_filters") else data["shifts"],
    }


def page_explorer(data: dict[str, object], state: dict[str, object]) -> None:
    tables = explorer_tables(data, state)
    ui.section(
        "Data explorer",
        "Inspect, search, paginate and export the underlying records",
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        table_name = st.selectbox("Table", list(tables), key="explorer_table")
    frame = tables[table_name].copy().drop(columns=["dataset"], errors="ignore")
    with col2:
        page_size = st.selectbox(
            "Rows per page", [25, 50, 100, 250], index=1, key="explorer_page_size"
        )

    query = st.text_input(
        "Search records",
        key="explorer_search",
        placeholder="Search any text column in this table",
    )
    frame = ui.search_frame(frame, query)

    total = len(frame)
    st.caption(f"{total:,} matching rows · {len(frame.columns)} columns")
    if total == 0:
        ui.empty_state(
            "No matching rows",
            "Adjust the global filters or clear the search to see records.",
        )
        return

    pages = max(1, (total + page_size - 1) // page_size)
    if pages > 1:
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=pages,
            value=1,
            step=1,
            key=f"explorer_page_{table_name}",
        )
    else:
        page = 1
    start = (int(page) - 1) * page_size
    page_frame = frame.iloc[start : start + page_size]

    ui.show_table(page_frame, height=430, key=f"explorer_grid_{table_name}")

    left, right = st.columns([1, 3])
    with left:
        ui.download_button(
            frame,
            f"{table_name.lower().replace(' ', '_')}.csv",
            "Download filtered table",
            key=f"download_explorer_{table_name}",
        )
    with right:
        st.caption(
            f"Page {int(page)} of {pages} · CSV export contains all {total:,} filtered rows."
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    page, mode = render_sidebar()

    fingerprint = data_access.fingerprint(mode)
    try:
        data = load_population(mode, fingerprint)
    except Exception as error:  # noqa: BLE001 - friendly UI, no traceback
        st.error(
            "The dataset could not be loaded. Regenerate it with "
            "`python src/pipeline.py` and try again."
        )
        st.caption(f"{type(error).__name__}: {error}")
        st.stop()
        return

    render_header(mode)
    filters, _ = render_filters(data, mode)
    data["_filters"] = filters
    state = build_state(data, filters)

    if state["events"].empty and page in ("Overview", "Alarm Monitoring"):
        ui.notice(
            "No alarm activations match the current filters. Widen the plant, machine, "
            "severity or date selection.",
            tone="info",
        )
    elif len(state["events"]) < len(data["events"]):
        st.caption(
            f"Filtered view: {len(state['events']):,} of "
            f"{len(data['events']):,} alarm activations."
        )

    try:
        if page == "Overview":
            page_overview(data, state)
        elif page == "Alarm Monitoring":
            page_alarms(data, state)
        elif page == "Acknowledgement Analytics":
            page_acknowledgements(data, state)
        elif page == "Incident Management":
            page_incidents(data, state)
        elif page == "Corrective Actions":
            page_actions(data, state)
        elif page == "Exception Analysis":
            page_exceptions(data, state)
        elif page == "Data Explorer":
            page_explorer(data, state)
    except Exception as error:  # noqa: BLE001 - never show a raw traceback
        st.error("This view could not be rendered for the current selection.")
        with st.expander("Technical details"):
            st.code(f"{type(error).__name__}: {error}")
        return

    with st.sidebar:
        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">System status</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="sidebar-footer"><span class="status-dot"></span>'
            "Data pipeline online</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            f"{config.DATASET_LABELS[mode]}  \n"
            f"Seed {config.SEED}  \n"
            f"{len(state['events']):,} activations in view"
        )


if __name__ == "__main__":
    main()
