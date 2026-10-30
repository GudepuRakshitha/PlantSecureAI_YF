"""Visual design system for the SAFEGUARD dashboard.

A single light-theme palette, font stack and Plotly layout are defined here so
that every page renders the same way.  Nothing in this module touches data.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

COLORS = {
    "bg": "#F5F7FA",
    "surface": "#FFFFFF",
    "navy": "#17324D",
    "accent": "#2878B5",
    "teal": "#168C8C",
    "text": "#172B3A",
    "muted": "#667085",
    "border": "#E4E9EF",
    "grid": "#EDF1F5",
    "soft": "#F0F4F8",
}

SEVERITY_COLORS = {
    "LOW": "#3F8F6B",
    "MEDIUM": "#C99400",
    "HIGH": "#D9661F",
    "CRITICAL": "#C0392B",
}

ACK_COLORS = {
    "ON_TIME": "#2F8F6B",
    "LATE": "#D9661F",
    "UNACKNOWLEDGED": "#C0392B",
}

ALARM_STATUS_COLORS = {
    "ACTIVE": "#C99400",
    "ACKNOWLEDGED": "#2878B5",
    "CLEARED": "#2F8F6B",
    "UNACKNOWLEDGED": "#C0392B",
}

INCIDENT_COLORS = {
    "OPEN": "#C0392B",
    "INVESTIGATING": "#C99400",
    "CLOSED": "#2F8F6B",
}

ACTION_COLORS = {
    "OPEN": "#C0392B",
    "IN_PROGRESS": "#2878B5",
    "PENDING_VERIFICATION": "#7A5EA8",
    "CLOSED": "#2F8F6B",
}

VERIFICATION_COLORS = {
    "PENDING": "#C99400",
    "VERIFIED": "#2F8F6B",
    "NOT_VERIFIED": "#C0392B",
}

EFFECTIVENESS_COLORS = {
    "PENDING": "#98A2B3",
    "EFFECTIVE": "#2F8F6B",
    "PARTIALLY_EFFECTIVE": "#C99400",
    "NOT_EFFECTIVE": "#C0392B",
}

CHART_COLORWAY = [
    "#2878B5",
    "#168C8C",
    "#17324D",
    "#C99400",
    "#D9661F",
    "#7A5EA8",
    "#3F8F6B",
    "#98A2B3",
]

FONT_STACK = (
    "Inter, 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', "
    "Arial, sans-serif"
)


# ---------------------------------------------------------------------------
# Global stylesheet
# ---------------------------------------------------------------------------

_CSS = f"""
<style>
  html, body, [class*="css"], .stApp {{
      font-family: {FONT_STACK};
  }}
  .stApp {{ background: {COLORS['bg']}; color: {COLORS['text']}; }}
  [data-testid="stAppViewContainer"] > .main {{ background: {COLORS['bg']}; }}
  header[data-testid="stHeader"] {{
      background: rgba(245, 247, 250, 0.9);
      backdrop-filter: blur(6px);
  }}
  #MainMenu, footer {{ visibility: hidden; }}
  .block-container {{
      max-width: 1520px;
      padding: 1.1rem 2rem 3rem 2rem;
  }}

  /* ---------- Sidebar ---------- */
  section[data-testid="stSidebar"] {{
      background: {COLORS['surface']};
      border-right: 1px solid {COLORS['border']};
  }}
  section[data-testid="stSidebar"] > div {{
      padding-top: 0.6rem;
  }}
  .brand {{
      display: flex;
      align-items: center;
      gap: 11px;
      padding: 2px 4px 6px 4px;
  }}
  .brand-mark {{
      width: 34px; height: 34px;
      display: flex; align-items: center; justify-content: center;
      background: {COLORS['navy']};
      border-radius: 7px;
      flex: none;
  }}
  .brand-name {{
      font-size: 15.5px; font-weight: 700; letter-spacing: .09em;
      color: {COLORS['navy']}; line-height: 1.15;
  }}
  .brand-sub {{
      font-size: 10.5px; letter-spacing: .04em; color: {COLORS['muted']};
      text-transform: uppercase; margin-top: 1px;
  }}
  .sidebar-divider {{
      height: 1px; background: {COLORS['border']};
      margin: 12px 0 12px 0;
  }}
  .sidebar-label {{
      font-size: 10.5px; font-weight: 700; letter-spacing: .08em;
      text-transform: uppercase; color: {COLORS['muted']};
      padding: 4px 6px 6px 6px;
  }}

  section[data-testid="stSidebar"] div[role="radiogroup"] {{ gap: 2px; }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label {{
      width: 100%;
      padding: 8px 10px 8px 12px;
      margin: 0;
      border-radius: 6px;
      border-left: 3px solid transparent;
      transition: background .12s ease;
  }}
  /* Hide the default radio dot: navigation reads as a menu, not a form. */
  section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
      display: none;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
      background: {COLORS['bg']};
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
      background: #EEF4FA;
      border-left-color: {COLORS['accent']};
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label p {{
      font-size: 13px !important;
      font-weight: 500;
      color: {COLORS['text']};
      margin: 0;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{
      color: {COLORS['navy']};
      font-weight: 650;
  }}

  .sidebar-footer {{
      display: flex; align-items: center; gap: 8px;
      padding: 10px 6px 2px 6px;
      font-size: 11.5px; color: {COLORS['muted']};
  }}
  .status-dot {{
      width: 7px; height: 7px; border-radius: 50%;
      background: #2F8F6B; flex: none;
      box-shadow: 0 0 0 3px rgba(47, 143, 107, .12);
  }}

  /* ---------- Header ---------- */
  .page-head {{ margin: 0 0 12px 0; }}
  .page-title {{
      font-size: 26px; font-weight: 700; letter-spacing: -.02em;
      color: {COLORS['navy']}; line-height: 1.2;
      margin: 0 0 2px 0;
  }}
  .page-subtitle {{
      font-size: 13px; color: {COLORS['muted']}; margin: 0 0 0 0;
  }}
  .header-meta {{
      display: flex; flex-direction: column; align-items: flex-end; gap: 5px;
      padding-top: 2px;
  }}
  .meta-line {{ font-size: 11.5px; color: {COLORS['muted']}; }}

  /* ---------- Badges / notices ---------- */
  .badge {{
      display: inline-flex; align-items: center; gap: 6px;
      padding: 3px 10px; border-radius: 999px;
      font-size: 11px; font-weight: 650; letter-spacing: .02em;
      white-space: nowrap;
  }}
  .badge-info {{ background: #EEF4FA; color: {COLORS['navy']}; border: 1px solid #D3E2F0; }}
  .badge-warn {{ background: #FFF6E5; color: #8A5A00; border: 1px solid #F1DDAE; }}
  .badge-good {{ background: #EAF6F1; color: #1F6F4F; border: 1px solid #CFE9DD; }}
  .badge-bad  {{ background: #FDECEA; color: #8F2A22; border: 1px solid #F3CFCB; }}
  .badge-neutral {{ background: #F2F4F7; color: #475467; border: 1px solid #E4E9EF; }}

  .notice {{
      display: flex; gap: 10px; align-items: flex-start;
      background: #FFF9EC; border: 1px solid #F0DFB5; color: #6B4E00;
      padding: 9px 13px; border-radius: 6px; font-size: 12.5px;
      margin: 2px 0 14px 0;
  }}
  .notice strong {{ color: #5A4100; }}

  /* ---------- Section headings ---------- */
  .section-head {{ margin: 20px 0 8px 0; }}
  .section-title {{
      font-size: 15.5px; font-weight: 650; color: {COLORS['navy']};
      letter-spacing: -.01em;
  }}
  .section-sub {{ font-size: 12px; color: {COLORS['muted']}; margin-top: 1px; }}

  /* ---------- KPI cards ---------- */
  .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(176px, 1fr));
      grid-auto-rows: 1fr;
      align-items: stretch;
      gap: 12px;
      margin: 4px 0 8px 0;
  }}
  .kpi-card {{
      background: {COLORS['surface']};
      border: 1px solid {COLORS['border']};
      border-radius: 8px;
      padding: 14px 16px 13px 16px;
      min-height: 108px;
      display: flex; flex-direction: column; justify-content: space-between;
  }}
  .kpi-label {{
      font-size: 10.5px; font-weight: 700; letter-spacing: .065em;
      text-transform: uppercase; color: {COLORS['muted']};
  }}
  .kpi-value {{
      font-size: 27px; font-weight: 650; letter-spacing: -.02em;
      color: {COLORS['text']}; line-height: 1.15; margin: 7px 0 3px 0;
  }}
  .kpi-desc {{ font-size: 11.5px; color: {COLORS['muted']}; }}
  .kpi-foot {{
      display: flex; align-items: center; gap: 6px;
      margin-top: 8px; font-size: 11px; font-weight: 600;
  }}
  .kpi-foot .status-dot {{ width: 6px; height: 6px; box-shadow: none; }}
  .tone-good {{ color: #1F6F4F; }}
  .tone-warn {{ color: #8A5A00; }}
  .tone-bad {{ color: #8F2A22; }}
  .tone-neutral {{ color: {COLORS['muted']}; }}
  .tone-good .status-dot {{ background: #2F8F6B; }}
  .tone-warn .status-dot {{ background: #C99400; }}
  .tone-bad .status-dot {{ background: #C0392B; }}
  .tone-neutral .status-dot {{ background: #98A2B3; }}

  /* ---------- Insights ---------- */
  .insight-card {{
      background: {COLORS['surface']};
      border: 1px solid {COLORS['border']};
      border-radius: 8px;
      padding: 4px 16px;
  }}
  .insight-row {{
      display: flex; gap: 10px; padding: 10px 0;
      border-bottom: 1px solid #F0F3F7;
  }}
  .insight-row:last-child {{ border-bottom: none; }}
  .insight-row .status-dot {{ margin-top: 6px; box-shadow: none; }}
  .insight-label {{
      font-size: 10.5px; font-weight: 700; letter-spacing: .055em;
      text-transform: uppercase; color: {COLORS['muted']};
  }}
  .insight-text {{
      font-size: 13px; color: {COLORS['text']}; font-weight: 500;
      margin-top: 1px;
  }}

  /* ---------- Empty states ---------- */
  .empty-state {{
      background: {COLORS['surface']};
      border: 1px dashed #D7DEE8;
      border-radius: 8px;
      padding: 26px 20px;
      text-align: center;
      color: {COLORS['muted']};
      font-size: 12.5px;
  }}
  .empty-title {{
      font-weight: 650; color: {COLORS['text']};
      font-size: 13px; margin-bottom: 3px;
  }}

  .table-hint {{ font-size: 11.5px; color: {COLORS['muted']}; margin: 1px 0 6px 0; }}

  /* ---------- Native widget polish ---------- */
  div[data-baseweb="select"] > div,
  div[data-baseweb="input"] > div {{
      background: {COLORS['surface']};
      border-color: {COLORS['border']};
      border-radius: 6px;
      font-size: 13px;
  }}
  .stTextInput input, .stNumberInput input, .stDateInput input {{
      font-size: 13px;
  }}
  .stButton > button, .stDownloadButton > button {{
      border: 1px solid #D7DEE8;
      background: {COLORS['surface']};
      color: {COLORS['navy']};
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 600;
      padding: 5px 12px;
  }}
  .stButton > button:hover, .stDownloadButton > button:hover {{
      border-color: {COLORS['accent']};
      color: {COLORS['accent']};
  }}
  .stButton > button:focus:not(:active) {{
      border-color: {COLORS['accent']}; color: {COLORS['accent']};
  }}
  div[data-testid="stVerticalBlockBorderWrapper"] {{
      background: {COLORS['surface']};
  }}
  div[data-testid="stPlotlyChart"] {{
      background: {COLORS['surface']};
      border: 1px solid {COLORS['border']};
      border-radius: 8px;
      padding: 10px 12px 4px 12px;
  }}
  div[data-testid="stDataFrame"] {{
      border: 1px solid {COLORS['border']};
      border-radius: 8px;
      overflow: hidden;
  }}
  div[data-testid="stAlert"] {{ border-radius: 6px; font-size: 12.5px; }}
  div[data-testid="stCaptionContainer"] p {{ font-size: 11.5px; color: {COLORS['muted']}; }}

  @media (max-width: 1100px) {{
      .block-container {{ padding: 1rem 1rem 2.5rem 1rem; }}
      .header-meta {{ align-items: flex-start; }}
  }}
</style>
"""


def inject_css() -> None:
    """Add the SAFEGUARD stylesheet to the current page."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Plotly layout
# ---------------------------------------------------------------------------


def style_figure(
    fig: go.Figure,
    title: str,
    *,
    height: int = 320,
    showlegend: bool = False,
    x_title: str | None = None,
    y_title: str | None = None,
    legend_horizontal: bool = True,
) -> go.Figure:
    """Apply the shared enterprise chart layout."""
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=8, r=16, t=44, b=44 if showlegend else 8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, size=11.5, color=COLORS["text"]),
        title=dict(
            text=title,
            x=0,
            xanchor="left",
            font=dict(size=13.5, color=COLORS["navy"]),
        ),
        showlegend=showlegend,
        legend=dict(
            orientation="h" if legend_horizontal else "v",
            yanchor="bottom",
            y=1.02,
            x=0,
            xanchor="left",
            font=dict(size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor=COLORS["surface"],
            bordercolor=COLORS["border"],
            font=dict(family=FONT_STACK, size=11.5, color=COLORS["text"]),
        ),
        colorway=CHART_COLORWAY,
        bargap=0.28,
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=COLORS["border"],
        tickfont=dict(size=11, color=COLORS["muted"]),
        title=dict(
            text=x_title or "",
            font=dict(size=11, color=COLORS["muted"]),
            standoff=8,
        ),
        automargin=True,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLORS["grid"],
        zeroline=False,
        linecolor=COLORS["border"],
        tickfont=dict(size=11, color=COLORS["muted"]),
        title=dict(
            text=y_title or "",
            font=dict(size=11, color=COLORS["muted"]),
            standoff=8,
        ),
        automargin=True,
    )
    return fig
