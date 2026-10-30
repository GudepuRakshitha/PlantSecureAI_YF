
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Industrial Safety Monitoring",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DATA = Path(__file__).resolve().parent.parent / "data"

# ============================================================
# 2. PROFESSIONAL THEME
# ============================================================

st.markdown("""
<style>
.stApp {
    background: #eef7fa;
    color: #173b50;
}

.block-container {
    max-width: 100%;
    padding: 2.5rem 1.5rem 2rem 1.5rem;
}

header[data-testid="stHeader"] {
    background: #eef7fa;
}

h1 {
    background: linear-gradient(90deg, #087b9b, #03445f);
    color: white !important;
    padding: 24px !important;
    border-radius: 12px;
    text-align: center;
    font-size: 30px !important;
    font-weight: 800 !important;
    line-height: 1.5 !important;
    margin-top: 12px !important;
}

h2, h3 {
    color: #075a78 !important;
    font-weight: 800 !important;
}

p, label, li {
    color: #173b50 !important;
    font-size: 15px !important;
    line-height: 1.6 !important;
}

[data-testid="stCaptionContainer"] {
    color: #557586 !important;
    font-size: 14px !important;
}

.section-heading {
    background: #d8eef5;
    color: #075a78;
    padding: 13px 16px;
    border-left: 5px solid #087b9b;
    border-radius: 6px;
    font-size: 18px;
    font-weight: 800;
    margin: 18px 0 13px 0;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #8bc8dc;
    border-radius: 12px;
    padding: 18px;
    min-height: 115px;
    box-shadow: 0 2px 7px rgba(30,100,125,.10);
}

[data-testid="stMetricLabel"] {
    color: #244b60 !important;
    font-size: 15px !important;
    font-weight: 700 !important;
}

[data-testid="stMetricValue"] {
    color: #0875ae !important;
    font-size: 29px !important;
    font-weight: 800 !important;
}

div[data-baseweb="select"] > div {
    background: white;
    border: 1px solid #55a9c5;
    border-radius: 8px;
    min-height: 42px;
}

.stButton > button {
    background: linear-gradient(90deg, #087b9b, #045574);
    color: white !important;
    border: none;
    border-radius: 8px;
    min-height: 42px;
    font-size: 14px !important;
    font-weight: 700 !important;
}

.stButton > button:hover {
    background: #0b91b4;
}

[data-testid="stTabs"] button {
    color: #075a78 !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    padding: 12px 15px !important;
}

[data-testid="stTabs"] button[aria-selected="true"] {
    color: #087b9b !important;
    border-bottom: 3px solid #087b9b !important;
}

[data-testid="stDataFrame"] {
    background: white;
    border: 1px solid #8bc8dc;
    border-radius: 10px;
}

hr {
    border-color: #a8d3e0;
    margin: 22px 0;
}

.footer {
    background: linear-gradient(90deg, #087b9b, #03445f);
    color: white;
    padding: 16px;
    border-radius: 10px;
    text-align: center;
    font-size: 14px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 3. LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    filenames = {
        "plants": "plants.csv",
        "machines": "machines.csv",
        "events": "alarm_events.csv",
        "acks": "acknowledgements.csv",
        "incidents": "incidents.csv",
        "exceptions": "analysis_exceptions.csv",
        "actions": "corrective_actions.csv",
        "definitions": "alarm_definitions.csv"
    }

    result = {}

    for key, filename in filenames.items():

        path = DATA / filename

        if not path.exists():
            raise FileNotFoundError(path)

        result[key] = pd.read_csv(path)

    return result


try:
    data = load_data()

except FileNotFoundError as error:
    st.error(f"Missing required data file: {error}")
    st.stop()


plants = data["plants"]
machines = data["machines"]
events = data["events"]
acks = data["acks"]
incidents = data["incidents"]
exceptions = data["exceptions"]
actions = data["actions"]
definitions = data["definitions"]


# ============================================================
# 4. PREPARE DATA RELATIONSHIPS
# ============================================================

machine_columns = [
    col for col in ["machine_id", "plant_id", "machine_name"]
    if col in machines.columns
]

machine_lookup = machines[machine_columns].drop_duplicates(
    subset=["machine_id"]
)

events = events.merge(
    machine_lookup,
    on="machine_id",
    how="left",
    validate="many_to_one"
)

# Acknowledgement relationship
event_lookup = events[
    ["alarm_event_id", "machine_id", "plant_id"]
].drop_duplicates("alarm_event_id")

acks = acks.merge(
    event_lookup,
    on="alarm_event_id",
    how="left",
    validate="many_to_one"
)

# Incident relationship
incident_lookup = incidents[
    ["incident_id", "machine_id", "plant_id"]
].drop_duplicates("incident_id")

# Add machine name to incidents
if "machine_id" in incidents.columns:
    incidents = incidents.merge(
        machine_lookup[
            ["machine_id"] +
            (["machine_name"] if "machine_name" in machine_lookup.columns else [])
        ],
        on="machine_id",
        how="left",
        validate="many_to_one"
    )

# Add location to corrective actions
actions = actions.merge(
    incident_lookup,
    on="incident_id",
    how="left",
    validate="many_to_one"
)


# ============================================================
# 5. MAP EXCEPTIONS TO PLANT AND MACHINE
# ============================================================

lookup_parts = []

for frame, id_column in [
    (events, "alarm_event_id"),
    (acks, "acknowledgement_id"),
    (incidents, "incident_id"),
    (actions, "action_id")
]:

    if all(
        col in frame.columns
        for col in [id_column, "machine_id", "plant_id"]
    ):

        part = frame[
            [id_column, "machine_id", "plant_id"]
        ].copy()

        part.columns = [
            "entity_id",
            "machine_id",
            "plant_id"
        ]

        lookup_parts.append(part)


if lookup_parts and "entity_id" in exceptions.columns:

    entity_lookup = pd.concat(
        lookup_parts,
        ignore_index=True
    ).drop_duplicates("entity_id")

    exceptions = exceptions.drop(
        columns=["machine_id", "plant_id"],
        errors="ignore"
    )

    exceptions = exceptions.merge(
        entity_lookup,
        on="entity_id",
        how="left",
        validate="many_to_one"
    )


# ============================================================
# 6. HEADER
# ============================================================

st.markdown(
    '<h1>🏭 INDUSTRIAL SAFETY MONITORING DASHBOARD</h1>',
    unsafe_allow_html=True
)

st.markdown(
    '<p style="text-align:center;color:#557586;">'
    'Industrial Safety Intelligence | Alarm Monitoring | '
    'Incident Management | Corrective Action Tracking'
    '</p>',
    unsafe_allow_html=True
)


# ============================================================
# 7. FILTER CALLBACKS
# ============================================================

def reset_filters():
    st.session_state["selected_plant"] = "All Plants"
    st.session_state["selected_machine"] = "All Machines"
    st.session_state["selected_severity"] = "All Severities"


def reset_machine():
    st.session_state["selected_machine"] = "All Machines"


# Initialize state before widgets
if "selected_plant" not in st.session_state:
    st.session_state["selected_plant"] = "All Plants"

if "selected_machine" not in st.session_state:
    st.session_state["selected_machine"] = "All Machines"

if "selected_severity" not in st.session_state:
    st.session_state["selected_severity"] = "All Severities"


# ============================================================
# 8. DASHBOARD FILTERS
# ============================================================

st.markdown(
    '<div class="section-heading">Dashboard Filters</div>',
    unsafe_allow_html=True
)

filter1, filter2, filter3, filter4 = st.columns([2, 2, 2, 1])

plant_options = ["All Plants"] + sorted(
    machines["plant_id"].dropna().astype(str).unique().tolist()
)

with filter1:
    selected_plant = st.selectbox(
        "Select Plant",
        plant_options,
        key="selected_plant",
        on_change=reset_machine
    )

if selected_plant == "All Plants":
    machine_source = machines.copy()
else:
    machine_source = machines[
        machines["plant_id"].astype(str) == selected_plant
    ]

machine_options = ["All Machines"] + sorted(
    machine_source["machine_id"].dropna().astype(str).unique().tolist()
)

if st.session_state["selected_machine"] not in machine_options:
    st.session_state["selected_machine"] = "All Machines"

with filter2:
    selected_machine = st.selectbox(
        "Select Machine",
        machine_options,
        key="selected_machine"
    )

severity_options = ["All Severities"] + sorted(
    events["severity"].dropna().astype(str).unique().tolist()
)

with filter3:
    selected_severity = st.selectbox(
        "Select Alarm Severity",
        severity_options,
        key="selected_severity"
    )

with filter4:
    st.write("")
    st.write("")
    st.button(
        "↻ Reset Filters",
        use_container_width=True,
        on_click=reset_filters
    )


# ============================================================
# 9. APPLY FILTERS
# ============================================================

def apply_filters(frame):

    result = frame.copy()

    if (
        selected_plant != "All Plants"
        and "plant_id" in result.columns
    ):
        result = result[
            result["plant_id"].astype(str) == selected_plant
        ]

    if (
        selected_machine != "All Machines"
        and "machine_id" in result.columns
    ):
        result = result[
            result["machine_id"].astype(str) == selected_machine
        ]

    return result


filtered_events = apply_filters(events)
filtered_acks = apply_filters(acks)
filtered_incidents = apply_filters(incidents)
filtered_actions = apply_filters(actions)
filtered_exceptions = apply_filters(exceptions)

if selected_severity != "All Severities":

    filtered_events = filtered_events[
        filtered_events["severity"].astype(str) == selected_severity
    ]

    if "severity" in filtered_exceptions.columns:
        filtered_exceptions = filtered_exceptions[
            filtered_exceptions["severity"].astype(str)
            == selected_severity
        ]


# ============================================================
# 10. ANALYTICAL METRICS
# ============================================================

total_events = len(filtered_events)
total_incidents = len(filtered_incidents)
total_exceptions = len(filtered_exceptions)

response_times = pd.to_numeric(
    filtered_acks["response_minutes"],
    errors="coerce"
)

valid_responses = response_times.dropna()

average_response = (
    valid_responses.mean()
    if not valid_responses.empty else 0
)

on_time_rate = (
    (valid_responses <= 5).mean() * 100
    if not valid_responses.empty else 0
)

unverified_actions = int(
    (
        filtered_actions["verification_status"].astype(str)
        != "VERIFIED"
    ).sum()
)

# Most affected machine
if not filtered_events.empty:
    machine_alarm_counts = (
        filtered_events.groupby("machine_id")
        .size()
        .sort_values(ascending=False)
    )

    most_affected_machine = machine_alarm_counts.index[0]
    most_affected_count = int(machine_alarm_counts.iloc[0])
else:
    most_affected_machine = "N/A"
    most_affected_count = 0

# Most frequent severity
if not filtered_events.empty:
    most_frequent_severity = (
        filtered_events["severity"].mode().iloc[0]
    )
else:
    most_frequent_severity = "N/A"

# Repeated alarm IDs
if "alarm_definition_id" in filtered_events.columns:
    repeated_alarms = (
        filtered_events.groupby("alarm_definition_id")
        .size()
        .reset_index(name="Alarm Count")
        .query("`Alarm Count` > 1")
        .sort_values("Alarm Count", ascending=False)
    )
else:
    repeated_alarms = pd.DataFrame()


# ============================================================
# 11. CHART STYLE
# ============================================================

def style_chart(fig, height=360):

    fig.update_layout(
        height=height,
        template="plotly_white",
        font=dict(
            family="Arial",
            size=13,
            color="#173b50"
        ),
        title_font=dict(
            size=19,
            color="#075a78"
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(t=55, b=55, l=65, r=40)
    )

    fig.update_xaxes(
        tickfont=dict(size=12, color="#173b50"),
        title_font=dict(size=13, color="#173b50"),
        gridcolor="#e5eef2"
    )

    fig.update_yaxes(
        tickfont=dict(size=12, color="#173b50"),
        title_font=dict(size=13, color="#173b50"),
        gridcolor="#e5eef2"
    )

    return fig


# ============================================================
# 12. NAVIGATION
# ============================================================

overview_tab, alarm_tab, incident_tab, action_tab, data_tab = st.tabs([
    "Overview",
    "Alarm Analysis",
    "Incident Analysis",
    "Corrective Actions",
    "Data Explorer"
])


# ============================================================
# 13. OVERVIEW
# ============================================================

with overview_tab:

    st.markdown(
        '<div class="section-heading">Key Safety Indicators</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Alarm Events", f"{total_events:,}")
    c2.metric("Total Incidents", f"{total_incidents:,}")
    c3.metric("On-time Acknowledgements", f"{on_time_rate:.2f}%")
    c4.metric("Safety Exceptions", f"{total_exceptions:,}")

    st.divider()

    # Additional insights
    st.markdown("**Operational Insights**")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Average Acknowledgement",
        f"{average_response:.2f} min"
    )

    m2.metric(
        "Unverified Actions",
        f"{unverified_actions:,}"
    )

    m3.metric(
        "Most Affected Machine",
        str(most_affected_machine)
    )

    m4.metric(
        "Most Frequent Severity",
        str(most_frequent_severity)
    )

    st.divider()

    # Main charts
    chart1, chart2, chart3 = st.columns(3)

    with chart1:

        st.markdown("**Alarm Severity Distribution**")

        severity_data = (
            filtered_events["severity"]
            .value_counts()
            .rename_axis("Severity")
            .reset_index(name="Count")
        )

        if not severity_data.empty:

            fig = px.pie(
                severity_data,
                names="Severity",
                values="Count",
                hole=0.45,
                color_discrete_sequence=[
                    "#087b9b",
                    "#12a6a6",
                    "#f0b429",
                    "#e45b55"
                ]
            )

            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                textfont_size=13
            )

            st.plotly_chart(
                style_chart(fig),
                use_container_width=True
            )
        else:
            st.info("No alarm data available.")

    with chart2:

        st.markdown("**Exceptions by Type**")

        if (
            not filtered_exceptions.empty
            and "exception_type" in filtered_exceptions.columns
        ):

            exception_counts = (
                filtered_exceptions["exception_type"]
                .value_counts()
                .rename_axis("Exception Type")
                .reset_index(name="Count")
                .sort_values("Count", ascending=True)
            )

            fig = px.bar(
                exception_counts,
                x="Count",
                y="Exception Type",
                orientation="h",
                text="Count",
                color_discrete_sequence=["#087b9b"]
            )

            fig.update_traces(
                textposition="outside",
                textfont_size=12
            )

            st.plotly_chart(
                style_chart(fig),
                use_container_width=True
            )
        else:
            st.info("No exceptions available.")

    with chart3:

        st.markdown("**Incidents by Severity**")

        if (
            not filtered_incidents.empty
            and "severity" in filtered_incidents.columns
        ):

            incident_counts = (
                filtered_incidents["severity"]
                .value_counts()
                .rename_axis("Severity")
                .reset_index(name="Count")
            )

            fig = px.bar(
                incident_counts,
                x="Severity",
                y="Count",
                text="Count",
                color_discrete_sequence=["#12a6a6"]
            )

            fig.update_traces(textposition="outside")

            st.plotly_chart(
                style_chart(fig),
                use_container_width=True
            )
        else:
            st.info("No incidents available.")

    st.divider()

    # Plant-wise volume
    st.markdown("**Plant-wise Alarm Volume**")

    plant_data = (
        filtered_events.groupby("plant_id")
        .size()
        .reset_index(name="Alarm Events")
        .sort_values("Alarm Events", ascending=False)
    )

    if not plant_data.empty:

        fig = px.bar(
            plant_data,
            x="plant_id",
            y="Alarm Events",
            text="Alarm Events",
            color_discrete_sequence=["#087b9b"]
        )

        fig.update_traces(
            textposition="outside",
            textfont_size=13
        )

        st.plotly_chart(
            style_chart(fig, 380),
            use_container_width=True
        )
    else:
        st.info("No plant data available.")


# ============================================================
# 14. ALARM ANALYSIS
# ============================================================

with alarm_tab:

    st.subheader("Alarm Event Analysis")

    a1, a2 = st.columns(2)

    with a1:

        st.markdown("**Alarms by Severity**")

        alarm_counts = (
            filtered_events["severity"]
            .value_counts()
            .rename_axis("Severity")
            .reset_index(name="Count")
        )

        if not alarm_counts.empty:

            fig = px.bar(
                alarm_counts,
                x="Severity",
                y="Count",
                color="Severity",
                text="Count"
            )

            fig.update_traces(textposition="outside")

            st.plotly_chart(
                style_chart(fig, 380),
                use_container_width=True
            )

    with a2:

        st.markdown("**Top 10 Machines by Alarm Volume**")

        machine_counts = (
            filtered_events.groupby("machine_id")
            .size()
            .reset_index(name="Alarm Count")
            .sort_values("Alarm Count", ascending=False)
            .head(10)
        )

        if not machine_counts.empty:

            fig = px.bar(
                machine_counts,
                x="machine_id",
                y="Alarm Count",
                text="Alarm Count",
                color_discrete_sequence=["#12a6a6"]
            )

            fig.update_traces(textposition="outside")

            st.plotly_chart(
                style_chart(fig, 380),
                use_container_width=True
            )

    st.divider()

    st.markdown("**Repeated Alarm Definitions**")

    if not repeated_alarms.empty:

        st.dataframe(
            repeated_alarms.head(20),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No repeated alarm definitions found.")

    st.divider()

    st.markdown("**Alarm Event Records**")

    st.dataframe(
        filtered_events,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 15. INCIDENT ANALYSIS
# ============================================================

with incident_tab:

    st.subheader("Incident Management")

    i1, i2, i3 = st.columns(3)

    i1.metric("Total Incidents", len(filtered_incidents))

    i2.metric(
        "Open Incidents",
        int((filtered_incidents["status"] == "OPEN").sum())
    )

    i3.metric(
        "Closed Incidents",
        int((filtered_incidents["status"] == "CLOSED").sum())
    )

    st.divider()

    st.markdown("**Incident Severity Distribution**")

    if (
        not filtered_incidents.empty
        and "severity" in filtered_incidents.columns
    ):

        fig = px.histogram(
            filtered_incidents,
            x="severity",
            color="severity",
            text_auto=True,
            color_discrete_sequence=[
                "#087b9b",
                "#12a6a6",
                "#f0b429",
                "#e45b55"
            ]
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    st.markdown("**Incident Records**")

    st.dataframe(
        filtered_incidents,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 16. CORRECTIVE ACTIONS
# ============================================================

with action_tab:

    st.subheader("Corrective Action Tracking")

    ac1, ac2, ac3 = st.columns(3)

    ac1.metric(
        "Total Actions",
        len(filtered_actions)
    )

    ac2.metric(
        "Closed Actions",
        int((filtered_actions["status"] == "CLOSED").sum())
    )

    ac3.metric(
        "Unverified Actions",
        unverified_actions
    )

    st.divider()

    st.markdown("**Verification Status**")

    if not filtered_actions.empty:

        verification_counts = (
            filtered_actions["verification_status"]
            .value_counts()
            .rename_axis("Verification Status")
            .reset_index(name="Count")
        )

        fig = px.bar(
            verification_counts,
            x="Verification Status",
            y="Count",
            color_discrete_sequence=["#087b9b"],
            text="Count"
        )

        fig.update_traces(textposition="outside")

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    st.markdown("**Corrective Action Records**")

    st.dataframe(
        filtered_actions,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 17. DATA EXPLORER
# ============================================================

with data_tab:

    st.subheader("Safety Exception Explorer")

    st.metric(
        "Exceptions in Current Selection",
        total_exceptions
    )

    if not filtered_exceptions.empty:

        # Separate routine SLA exceptions from other issues.
        if "exception_type" in filtered_exceptions.columns:

            routine = filtered_exceptions[
                filtered_exceptions["exception_type"]
                == "LATE_ACKNOWLEDGEMENT"
            ]

            other = filtered_exceptions[
                filtered_exceptions["exception_type"]
                != "LATE_ACKNOWLEDGEMENT"
            ]

            routine_tab, other_tab = st.tabs([
                "Acknowledgement Delays",
                "Other Safety Exceptions"
            ])

            with routine_tab:

                st.caption(
                    "Acknowledgement delays are shown separately "
                    "because they can dominate the exception count."
                )

                st.dataframe(
                    routine,
                    use_container_width=True,
                    hide_index=True
                )

            with other_tab:

                st.dataframe(
                    other,
                    use_container_width=True,
                    hide_index=True
                )

        else:

            st.dataframe(
                filtered_exceptions,
                use_container_width=True,
                hide_index=True
            )

    else:

        st.success("No exceptions found for the current filters.")

    st.divider()

    st.subheader("Dataset Information")

    d1, d2, d3, d4 = st.columns(4)

    d1.metric("Plants", machines["plant_id"].nunique())
    d2.metric("Machines", machines["machine_id"].nunique())
    d3.metric("Alarm Definitions", len(definitions))
    d4.metric("Alarm Records", len(events))


# ============================================================
# 18. FOOTER
# ============================================================

st.divider()

st.markdown("""
<div class="footer">
    Industrial Safety Monitoring Dashboard |
    Synthetic Industrial Dataset |
    Fixed Random Seed: 20261022
</div>
""", unsafe_allow_html=True)
