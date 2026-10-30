"""Reusable presentation components for the SAFEGUARD dashboard.

Only rendering lives here.  Every number is calculated by ``src.metrics`` and
passed in, so the UI can never drift from the analytical layer.
"""

from __future__ import annotations

import html
from typing import Iterable, Mapping

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard import theme

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def fmt_int(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def fmt_minutes(value: object) -> str:
    try:
        return f"{float(value):.1f} min"
    except (TypeError, ValueError):
        return "—"


def fmt_hours(value: object) -> str:
    try:
        return f"{float(value):.1f} h"
    except (TypeError, ValueError):
        return "—"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


# ---------------------------------------------------------------------------
# Page elements
# ---------------------------------------------------------------------------


def section(title: str, subtitle: str | None = None) -> None:
    """Render a compact section heading."""
    subtitle_html = f'<div class="section-sub">{esc(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div class="section-head"><div class="section-title">{esc(title)}</div>'
        f"{subtitle_html}</div>",
        unsafe_allow_html=True,
    )


def badge(text: str, tone: str = "info") -> str:
    """Return a pill badge as HTML (tone: info, warn, good, bad, neutral)."""
    return f'<span class="badge badge-{tone}">{esc(text)}</span>'


def notice(text: str, *, tone: str = "warn") -> None:
    """Render a compact inline notice."""
    st.markdown(
        f'<div class="notice"><span class="status-dot" '
        f'style="background: {"#C99400" if tone == "warn" else "#2878B5"}"></span>'
        f"<div>{text}</div></div>",
        unsafe_allow_html=True,
    )


def empty_state(title: str, message: str) -> None:
    """Render a friendly empty state instead of a blank area."""
    st.markdown(
        f'<div class="empty-state"><div class="empty-title">{esc(title)}</div>'
        f"{esc(message)}</div>",
        unsafe_allow_html=True,
    )


def kpi_grid(cards: Iterable[Mapping[str, str]]) -> None:
    """Render a responsive grid of KPI cards.

    Each card accepts ``label``, ``value``, ``desc`` and optionally ``tone``
    (good/warn/bad/neutral) plus ``status`` for the small footer line.
    """
    blocks = []
    for card in cards:
        tone = card.get("tone", "neutral")
        status = card.get("status")
        footer = (
            f'<div class="kpi-foot tone-{tone}"><span class="status-dot"></span>'
            f"{esc(status)}</div>"
            if status
            else ""
        )
        blocks.append(
            '<div class="kpi-card">'
            f'<div class="kpi-label">{esc(card["label"])}</div>'
            f'<div class="kpi-value">{esc(card["value"])}</div>'
            f'<div class="kpi-desc">{esc(card.get("desc", ""))}</div>'
            f"{footer}</div>"
        )
    st.markdown(f'<div class="kpi-grid">{"".join(blocks)}</div>', unsafe_allow_html=True)


def insight_list(items: Iterable[Mapping[str, str]]) -> None:
    """Render compact, data-derived operational insights."""
    rows = []
    for item in items:
        tone = item.get("tone", "neutral")
        rows.append(
            '<div class="insight-row">'
            f'<span class="status-dot" style="background:'
            f'{ {"good": "#2F8F6B", "warn": "#C99400", "bad": "#C0392B"}.get(tone, "#98A2B3") }"></span>'
            "<div>"
            f'<div class="insight-label">{esc(item["label"])}</div>'
            f'<div class="insight-text">{esc(item["text"])}</div>'
            "</div></div>"
        )
    st.markdown(f'<div class="insight-card">{"".join(rows)}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def plot(fig: go.Figure) -> None:
    """Render a Plotly figure using the shared responsive settings."""
    st.plotly_chart(
        fig,
        theme=None,
        config={"displayModeBar": False, "responsive": True},
    )


def ranking_bar(
    frame: pd.DataFrame,
    label_column: str,
    value_column: str,
    title: str,
    *,
    color: str = theme.COLORS["accent"],
    height: int = 300,
    top: int | None = None,
    value_suffix: str = "",
    label_title: str | None = None,
) -> go.Figure:
    """Horizontal ranking bar with the largest value at the top."""
    data = frame[[label_column, value_column]].dropna()
    if top is not None:
        data = data.sort_values(value_column, ascending=False).head(top)
    data = data.sort_values(value_column, ascending=True)
    fig = px.bar(
        data,
        x=value_column,
        y=label_column,
        orientation="h",
        color_discrete_sequence=[color],
    )
    fig.update_traces(
        text=[
            f"{value:,.0f}{value_suffix}" for value in data[value_column]
        ],
        textposition="outside",
        cliponaxis=False,
        marker_line_width=0,
        hovertemplate=f"<b>%{{y}}</b><br>{esc(label_column)}: %{{x:,.0f}}{value_suffix}<extra></extra>",
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=10.5))
    return theme.style_figure(
        fig,
        title,
        height=height,
        x_title=label_title,
    )


def donut(
    frame: pd.DataFrame,
    names_column: str,
    values_column: str,
    title: str,
    color_map: Mapping[str, str] | None = None,
    *,
    order: Iterable[str] | None = None,
    height: int = 300,
    total_label: str = "total",
) -> go.Figure:
    """Donut chart with a centred total and a horizontal legend."""
    data = frame[[names_column, values_column]].dropna()
    data = data[pd.to_numeric(data[values_column], errors="coerce").fillna(0) > 0]
    total = float(pd.to_numeric(data[values_column], errors="coerce").fillna(0).sum())
    fig = px.pie(
        data,
        names=names_column,
        values=values_column,
        hole=0.68,
        color=names_column,
        color_discrete_map=dict(color_map or {}),
        category_orders={names_column: list(order)} if order else None,
    )
    fig.update_traces(
        textinfo="none",
        marker_line_width=2,
        marker_line_color="#FFFFFF",
        hovertemplate="<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>",
    )
    fig.add_annotation(
        text=(
            f"<b style='font-size:18px;color:{theme.COLORS['text']}'>{total:,.0f}</b>"
            f"<br><span style='font-size:10.5px;color:{theme.COLORS['muted']}'>{esc(total_label)}</span>"
        ),
        x=0.5,
        y=0.5,
        showarrow=False,
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.02,
            xanchor="center",
            x=0.5,
            font=dict(size=10.5),
        ),
    )
    return theme.style_figure(fig, title, height=height, showlegend=True)


def trend_line(
    frame: pd.DataFrame,
    x_column: str,
    series: Mapping[str, str],
    title: str,
    colors: Iterable[str] = (),
    *,
    height: int = 320,
    y_title: str | None = None,
    x_title: str | None = None,
    fill: bool = False,
) -> go.Figure:
    """Line chart with one line per ``series`` mapping (label -> column)."""
    if frame.empty:
        return theme.style_figure(go.Figure(), title, height=height)
    data = frame[[x_column, *series.values()]].melt(
        id_vars=x_column, var_name="series", value_name="value"
    )
    lookup = {column: label for label, column in series.items()}
    data["series"] = data["series"].map(lookup)
    fig = px.line(
        data,
        x=x_column,
        y="value",
        color="series",
        color_discrete_sequence=list(colors) or theme.CHART_COLORWAY,
        markers=True,
    )
    if fill and len(series) == 1:
        fig.update_traces(fill="tozeroy", fillcolor="rgba(40,120,181,0.07)")
    fig.update_traces(line=dict(width=2.2), marker=dict(size=4.5))
    fig.update_layout(hovermode="x unified")
    return theme.style_figure(
        fig,
        title,
        height=height,
        showlegend=len(series) > 1,
        y_title=y_title,
        x_title=x_title,
    )


def stacked_bar(
    frame: pd.DataFrame,
    x_column: str,
    y_column: str,
    color_column: str,
    title: str,
    color_map: Mapping[str, str],
    *,
    height: int = 320,
    x_title: str | None = None,
    y_title: str | None = None,
    percent: bool = False,
) -> go.Figure:
    """Stacked comparison bar, optionally normalised to 100%."""
    fig = px.bar(
        frame,
        x=x_column,
        y=y_column,
        color=color_column,
        barmode="stack",
        color_discrete_map=dict(color_map),
        category_orders={color_column: list(color_map)},
    )
    fig.update_traces(marker_line_width=0)
    fig.update_layout(barnorm="percent" if percent else None)
    return theme.style_figure(
        fig,
        title,
        height=height,
        showlegend=True,
        x_title=x_title,
        y_title=y_title,
    )


def histogram(
    frame: pd.DataFrame,
    column: str,
    title: str,
    *,
    color: str = theme.COLORS["accent"],
    nbins: int = 15,
    x_title: str | None = None,
    y_title: str = "Alarms",
    height: int = 300,
) -> go.Figure:
    """Distribution histogram for a single numeric column."""
    data = frame[[column]].dropna()
    fig = px.histogram(
        data,
        x=column,
        nbins=nbins,
        color_discrete_sequence=[color],
    )
    fig.update_traces(marker_line_width=0)
    fig.update_layout(bargap=0.08, xaxis_title=None)
    return theme.style_figure(
        fig,
        title,
        height=height,
        x_title=x_title,
        y_title=y_title,
    )


def event_scatter(
    frame: pd.DataFrame,
    x_column: str,
    y_column: str,
    size_column: str,
    color_column: str,
    title: str,
    color_map: Mapping[str, str] | None = None,
    *,
    height: int = 300,
    top: int | None = 40,
) -> go.Figure:
    """Timeline scatter used for alarm-flood episodes."""
    data = frame.dropna(subset=[x_column, y_column]).copy()
    if top is not None:
        data = data.sort_values(size_column, ascending=False).head(top)
    fig = px.scatter(
        data,
        x=x_column,
        y=y_column,
        size=size_column,
        color=color_column,
        color_discrete_map=dict(color_map or {}),
        size_max=26,
        hover_data={size_column: ":.0f"},
    )
    fig.update_traces(marker=dict(line=dict(width=1, color="#FFFFFF"), opacity=0.85))
    return theme.style_figure(fig, title, height=height, showlegend=False)


# ---------------------------------------------------------------------------
# Tables and export
# ---------------------------------------------------------------------------


def search_frame(
    frame: pd.DataFrame,
    query: str,
    columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Case-insensitive search across text-like columns."""
    if not query or frame.empty:
        return frame
    candidates = list(columns or frame.select_dtypes(include=["object", "string"]).columns)
    mask = pd.Series(False, index=frame.index)
    for column in candidates:
        mask |= (
            frame[column]
            .astype("string")
            .str.contains(query, case=False, na=False)
        )
    return frame[mask]


def _prepare_view(
    frame: pd.DataFrame,
    columns: Iterable[str] | None,
    labels: Mapping[str, str] | None,
    formats: Mapping[str, str] | None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    view = frame.copy()
    if columns is not None:
        view = view[[column for column in columns if column in view.columns]]

    for column in view.columns:
        if pd.api.types.is_datetime64_any_dtype(view[column]):
            view[column] = view[column].dt.strftime("%d %b %Y %H:%M")

    config: dict[str, object] = {}
    for column in view.columns:
        label = (labels or {}).get(column, column.replace("_", " ").title())
        if column in (formats or {}) and formats is not None:
            config[column] = st.column_config.NumberColumn(
                label=label, format=formats[column]
            )
        elif pd.api.types.is_integer_dtype(view[column]):
            config[column] = st.column_config.NumberColumn(label=label, format="%d")
        elif pd.api.types.is_float_dtype(view[column]):
            config[column] = st.column_config.NumberColumn(label=label, format="%.2f")
        elif column in {"description", "action_description", "state_transition"}:
            config[column] = st.column_config.TextColumn(label=label, width="large")
        else:
            config[column] = st.column_config.TextColumn(label=label)
    return view, config


def show_table(
    frame: pd.DataFrame,
    *,
    columns: Iterable[str] | None = None,
    labels: Mapping[str, str] | None = None,
    formats: Mapping[str, str] | None = None,
    height: int = 340,
    key: str | None = None,
) -> None:
    """Render a styled, formatted dataframe."""
    view, config = _prepare_view(frame, columns, labels, formats)
    st.dataframe(
        view,
        hide_index=True,
        column_config=config,
        height=height,
        key=key,
    )


def download_button(
    frame: pd.DataFrame,
    filename: str,
    label: str = "Download CSV",
    *,
    key: str | None = None,
) -> None:
    """CSV download with an Excel-friendly UTF-8 BOM."""
    if frame.empty:
        return
    st.download_button(
        label,
        data=frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )
