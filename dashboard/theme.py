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
  /* Completely hide Streamlit default header bar, deploy button, and toolbar */
  header[data-testid="stHeader"] {{
      background: transparent !important;
      height: 0 !important;
      min-height: 0 !important;
      padding: 0 !important;
      margin: 0 !important;
      border: none !important;
      pointer-events: none !important;
      z-index: 1 !important;
  }}
  .stDeployButton,
  [data-testid="stAppDeployButton"],
  [data-testid="stToolbar"],
  #MainMenu,
  footer {{
      display: none !important;
      visibility: hidden !important;
      height: 0 !important;
      width: 0 !important;
      overflow: hidden !important;
  }}
  header[data-testid="stHeader"] * {{
      pointer-events: auto;
  }}

  .block-container {{
      max-width: 100% !important;
      padding: 1.5rem 2.25rem 3rem 2.25rem !important;
      margin-left: 0 !important;
      margin-right: auto !important;
  }}

  /* ---------- Sidebar ---------- */
  section[data-testid="stSidebar"] {{
      background: {COLORS['surface']} !important;
      border-right: 1px solid {COLORS['border']} !important;
      min-width: 295px !important;
      max-width: 325px !important;
      width: 305px !important;
  }}
  section[data-testid="stSidebar"] > div:first-child,
  section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
      padding-top: 0.85rem !important;
      padding-left: 1.15rem !important;
      padding-right: 1.15rem !important;
      padding-bottom: 2rem !important;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {{
      padding: 0.25rem 0.5rem 0 0.5rem !important;
      height: auto !important;
      min-height: unset !important;
  }}
  .brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 2px 2px 8px 2px;
      margin: 0;
  }}
  .brand-mark {{
      width: 34px;
      height: 34px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: {COLORS['navy']};
      border-radius: 7px;
      flex-shrink: 0;
  }}
  .brand-text {{
      display: flex;
      flex-direction: column;
      justify-content: center;
  }}
  .brand-name {{
      font-size: 15px;
      font-weight: 750;
      letter-spacing: .08em;
      color: {COLORS['navy']};
      line-height: 1.15;
      margin: 0;
  }}
  .brand-sub {{
      font-size: 10px;
      font-weight: 600;
      letter-spacing: .04em;
      color: {COLORS['muted']};
      text-transform: uppercase;
      margin-top: 2px;
      line-height: 1.1;
  }}
  .sidebar-divider {{
      height: 1px;
      background: {COLORS['border']};
      margin: 10px 0 10px 0;
  }}
  .sidebar-label {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: {COLORS['muted']};
      padding: 0 4px 6px 4px;
      margin: 0;
  }}

  section[data-testid="stSidebar"] div[role="radiogroup"] {{
      gap: 3px;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label {{
      display: flex !important;
      align-items: center !important;
      width: 100% !important;
      padding: 7px 10px !important;
      margin: 0 !important;
      border-radius: 6px !important;
      border-left: 3px solid transparent !important;
      cursor: pointer !important;
      transition: all .12s ease !important;
  }}
  /* Hide the default radio dot: navigation reads as a menu, not a form. */
  section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
      display: none !important;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
      background: {COLORS['bg']} !important;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
      background: #EEF4FA !important;
      border-left-color: {COLORS['accent']} !important;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label p {{
      font-size: 13px !important;
      font-weight: 500 !important;
      color: {COLORS['text']} !important;
      margin: 0 !important;
      line-height: 1.4 !important;
      display: flex !important;
      align-items: center !important;
      gap: 8px !important;
      white-space: nowrap !important;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{
      color: {COLORS['navy']} !important;
      font-weight: 650 !important;
  }}

  .sidebar-footer {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 2px 4px 2px 4px;
      font-size: 12px;
      font-weight: 550;
      color: {COLORS['text']};
  }}
  .status-dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #2F8F6B;
      flex-shrink: 0;
      box-shadow: 0 0 0 3px rgba(47, 143, 107, .12);
  }}

  /* ---------- Header ---------- */
  .page-header-container {{
      margin: 0 0 1.25rem 0;
      padding: 0;
  }}
  .page-title-row {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 4px;
  }}
  .page-title {{
      font-size: 26px !important;
      font-weight: 750 !important;
      letter-spacing: -.02em !important;
      color: {COLORS['navy']} !important;
      line-height: 1.25 !important;
      margin: 0 !important;
      padding: 0 !important;
  }}
  .page-subtitle {{
      font-size: 13.5px !important;
      color: {COLORS['muted']} !important;
      margin: 0 !important;
      line-height: 1.4 !important;
  }}

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
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      grid-auto-rows: 1fr;
      align-items: stretch;
      gap: 12px;
      margin: 4px 0 10px 0;
  }}
  .kpi-grid-6 {{
      grid-template-columns: repeat(6, 1fr);
  }}
  .kpi-grid-4 {{
      grid-template-columns: repeat(4, 1fr);
  }}
  .kpi-grid-3 {{
      grid-template-columns: repeat(3, 1fr);
  }}
  @media (max-width: 1280px) {{
      .kpi-grid-6 {{
          grid-template-columns: repeat(3, 1fr) !important;
      }}
      .kpi-grid-4 {{
          grid-template-columns: repeat(2, 1fr) !important;
      }}
  }}
  @media (max-width: 768px) {{
      .kpi-grid-6, .kpi-grid-4, .kpi-grid-3, .kpi-grid {{
          grid-template-columns: repeat(2, 1fr) !important;
      }}
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
      border: 1px solid #CBD5E1 !important;
      background: {COLORS['surface']} !important;
      color: {COLORS['navy']} !important;
      border-radius: 6px !important;
      font-size: 12.5px !important;
      font-weight: 600 !important;
      padding: 6px 14px !important;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04) !important;
      transition: all .15s ease !important;
  }}
  .stButton > button *, .stDownloadButton > button * {{
      color: {COLORS['navy']} !important;
      font-weight: 600 !important;
  }}
  .stButton > button:hover, .stDownloadButton > button:hover {{
      border-color: {COLORS['accent']} !important;
      color: {COLORS['accent']} !important;
      background: #F0F6FA !important;
  }}
  .stButton > button:hover *, .stDownloadButton > button:hover * {{
      color: {COLORS['accent']} !important;
  }}
  .stButton > button:focus:not(:active) {{
      border-color: {COLORS['accent']} !important;
      color: {COLORS['accent']} !important;
  }}

  /* Back to Dashboard buttons: solid dark navy with bold pure white text */
  .st-key-btn_back_to_dashboard_top button,
  .st-key-btn_back_to_dashboard_bottom button,
  div[data-testid="stButton"]:has(button[key*="btn_back_to_dashboard"]) button,
  button[kind="primary"] {{
      background: {COLORS['navy']} !important;
      background-color: {COLORS['navy']} !important;
      border: 1px solid {COLORS['navy']} !important;
      color: #FFFFFF !important;
      border-radius: 6px !important;
      font-size: 13px !important;
      font-weight: 700 !important;
      padding: 7px 18px !important;
      box-shadow: 0 1px 3px rgba(23, 50, 77, 0.2) !important;
      cursor: pointer !important;
  }}
  .st-key-btn_back_to_dashboard_top button *,
  .st-key-btn_back_to_dashboard_bottom button *,
  .st-key-btn_back_to_dashboard_top button p,
  .st-key-btn_back_to_dashboard_bottom button p,
  .st-key-btn_back_to_dashboard_top button span,
  .st-key-btn_back_to_dashboard_bottom button span,
  .st-key-btn_back_to_dashboard_top button div,
  .st-key-btn_back_to_dashboard_bottom button div,
  button[kind="primary"] *,
  button[kind="primary"] p {{
      color: #FFFFFF !important;
      font-weight: 700 !important;
      font-size: 13px !important;
      fill: #FFFFFF !important;
  }}
  .st-key-btn_back_to_dashboard_top button:hover,
  .st-key-btn_back_to_dashboard_bottom button:hover,
  button[kind="primary"]:hover {{
      background: {COLORS['accent']} !important;
      background-color: {COLORS['accent']} !important;
      border-color: {COLORS['accent']} !important;
      color: #FFFFFF !important;
  }}
  .st-key-btn_back_to_dashboard_top button:hover *,
  .st-key-btn_back_to_dashboard_bottom button:hover *,
  button[kind="primary"]:hover * {{
      color: #FFFFFF !important;
  }}

  /* About the Developer button in sidebar */
  .st-key-btn_about_developer_sidebar button {{
      background: #F1F5F9 !important;
      border: 1px solid #CBD5E1 !important;
      color: {COLORS['navy']} !important;
      font-weight: 600 !important;
      font-size: 12.5px !important;
      border-radius: 6px !important;
      padding: 6px 12px !important;
      width: 100% !important;
      transition: all .15s ease !important;
  }}
  .st-key-btn_about_developer_sidebar button * {{
      color: {COLORS['navy']} !important;
      font-weight: 600 !important;
  }}
  .st-key-btn_about_developer_sidebar button:hover {{
      background: {COLORS['accent']} !important;
      border-color: {COLORS['accent']} !important;
      color: #FFFFFF !important;
  }}
  .st-key-btn_about_developer_sidebar button:hover * {{
      color: #FFFFFF !important;
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

  /* ---------- Sidebar Developer Profile ---------- */
  .sidebar-profile-card {{
      background: #F8FAFC;
      border: 1px solid {COLORS['border']};
      border-radius: 8px;
      padding: 10px 11px;
      margin-bottom: 8px;
      transition: all .15s ease;
  }}
  .sidebar-profile-card-active {{
      background: #EEF4FA;
      border-color: {COLORS['accent']};
      box-shadow: 0 0 0 1px {COLORS['accent']};
  }}
  .sidebar-profile-header {{
      display: flex;
      align-items: center;
      gap: 10px;
  }}
  .sidebar-avatar {{
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: {COLORS['navy']};
      color: #FFFFFF;
      font-weight: 700;
      font-size: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      letter-spacing: .02em;
      flex-shrink: 0;
  }}
  .sidebar-profile-name {{
      font-size: 11.5px;
      font-weight: 700;
      color: {COLORS['navy']};
      line-height: 1.25;
      letter-spacing: .01em;
  }}
  .sidebar-profile-role {{
      font-size: 10.5px;
      color: {COLORS['muted']};
      margin-top: 1px;
  }}
  .sidebar-attribution-container {{
      text-align: center;
      margin-top: 4px;
      padding-bottom: 6px;
  }}
  .sidebar-attribution-container button {{
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      color: {COLORS['muted']} !important;
      font-size: 11px !important;
      font-weight: 500 !important;
      letter-spacing: .01em !important;
      padding: 2px 4px !important;
      min-height: unset !important;
      height: auto !important;
      cursor: pointer !important;
  }}
  .sidebar-attribution-container button:hover {{
      color: {COLORS['accent']} !important;
      text-decoration: underline !important;
      background: transparent !important;
  }}

  /* ---------- Developer Profile Page ---------- */
  .profile-breadcrumb {{
      display: flex;
      align-items: center;
      font-size: 12px;
      color: {COLORS['muted']};
      padding-top: 2px;
  }}
  .profile-breadcrumb .curr {{
      color: {COLORS['navy']};
      font-weight: 650;
  }}
  .profile-breadcrumb .sep {{
      margin: 0 6px;
      color: #98A2B3;
  }}
  .profile-hero-card {{
      background: {COLORS['surface']};
      border: 1px solid {COLORS['border']};
      border-radius: 10px;
      padding: 22px 26px;
      margin: 12px 0 20px 0;
      box-shadow: 0 1px 3px rgba(16, 24, 40, .04);
  }}
  .profile-hero-main {{
      display: flex;
      gap: 20px;
      align-items: center;
  }}
  .profile-hero-avatar {{
      width: 62px;
      height: 62px;
      border-radius: 50%;
      background: {COLORS['navy']};
      color: #FFFFFF;
      font-size: 22px;
      font-weight: 750;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2px solid {COLORS['accent']};
      flex-shrink: 0;
      box-shadow: 0 2px 8px rgba(23, 50, 77, .12);
  }}
  .profile-hero-content {{
      flex: 1;
  }}
  .profile-hero-badge {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: {COLORS['accent']};
      background: #EEF4FA;
      padding: 2px 8px;
      border-radius: 4px;
      display: inline-block;
      margin-bottom: 5px;
  }}
  .profile-hero-name {{
      font-size: 24px;
      font-weight: 750;
      color: {COLORS['navy']};
      margin: 0 0 3px 0;
      letter-spacing: -.01em;
      line-height: 1.2;
  }}
  .profile-hero-headline {{
      font-size: 13.5px;
      color: {COLORS['accent']};
      font-weight: 550;
      line-height: 1.4;
      margin-bottom: 10px;
  }}
  .profile-hero-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
  }}
  .profile-tag {{
      background: {COLORS['soft']};
      color: {COLORS['navy']};
      font-size: 11px;
      font-weight: 550;
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid #D9E2EC;
  }}
  .profile-section-header {{
      margin: 22px 0 10px 0;
  }}
  .profile-section-title {{
      font-size: 16px;
      font-weight: 700;
      color: {COLORS['navy']};
      letter-spacing: -.01em;
  }}
  .profile-section-sub {{
      font-size: 12px;
      color: {COLORS['muted']};
      margin-top: 1px;
  }}
  .profile-card {{
      background: {COLORS['surface']};
      border: 1px solid {COLORS['border']};
      border-radius: 8px;
      padding: 16px 18px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, .03);
  }}
  .profile-bio-card {{
      padding: 18px 22px;
  }}
  .profile-bio-p {{
      font-size: 13.5px;
      line-height: 1.65;
      color: {COLORS['text']};
      margin: 0 0 11px 0;
  }}
  .profile-bio-p:last-child {{
      margin-bottom: 0;
  }}
  .profile-skill-card {{
      margin-bottom: 12px;
  }}
  .profile-skill-category {{
      font-size: 11.5px;
      font-weight: 700;
      color: {COLORS['navy']};
      text-transform: uppercase;
      letter-spacing: .06em;
      margin-bottom: 10px;
  }}
  .profile-skill-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
  }}
  .profile-skill-pill {{
      background: #F8FAFC;
      border: 1px solid {COLORS['border']};
      color: {COLORS['text']};
      font-size: 12px;
      font-weight: 550;
      padding: 4px 10px;
      border-radius: 6px;
      transition: all .12s ease;
  }}
  .profile-highlight-card {{
      text-align: left;
      padding: 15px 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 136px;
      margin-bottom: 10px;
  }}
  .profile-highlight-tag {{
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: {COLORS['accent']};
      margin-bottom: 3px;
  }}
  .profile-highlight-metric {{
      font-size: 20px;
      font-weight: 750;
      color: {COLORS['navy']};
      margin-bottom: 3px;
      line-height: 1.2;
  }}
  .profile-highlight-title {{
      font-size: 12.5px;
      font-weight: 650;
      color: {COLORS['text']};
      margin-bottom: 3px;
  }}
  .profile-highlight-desc {{
      font-size: 11.5px;
      color: {COLORS['muted']};
      line-height: 1.4;
  }}
  .profile-link-card {{
      display: flex;
      align-items: center;
      gap: 13px;
      background: {COLORS['surface']};
      border: 1px solid {COLORS['border']};
      border-radius: 8px;
      padding: 13px 15px;
      margin-bottom: 10px;
      text-decoration: none !important;
      color: inherit !important;
      transition: all .15s ease;
  }}
  .profile-link-card:hover {{
      border-color: {COLORS['accent']};
      box-shadow: 0 2px 8px rgba(40, 120, 181, .09);
      transform: translateY(-1px);
  }}
  .profile-link-icon-wrap {{
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: {COLORS['soft']};
      color: {COLORS['navy']};
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
  }}
  .profile-link-text {{
      flex: 1;
      min-width: 0;
  }}
  .profile-link-title {{
      font-size: 13px;
      font-weight: 650;
      color: {COLORS['navy']};
      line-height: 1.3;
  }}
  .profile-link-label {{
      font-size: 11px;
      color: {COLORS['muted']};
      margin-top: 1px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
  }}
  .profile-link-action {{
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 11.5px;
      font-weight: 600;
      color: {COLORS['accent']};
      white-space: nowrap;
      flex-shrink: 0;
  }}
  .profile-cert-card {{
      border-left: 3px solid {COLORS['accent']};
  }}
  .profile-cert-configurable {{
      opacity: 0.95;
      cursor: default;
  }}
  .profile-cert-configurable:hover {{
      border-color: {COLORS['border']};
      box-shadow: 0 1px 2px rgba(16, 24, 40, .03);
      transform: none;
  }}

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
        margin=dict(l=10, r=16, t=42, b=42 if showlegend else 14),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, size=11.5, color=COLORS["text"]),
        title=dict(
            text=title,
            x=0,
            xanchor="left",
            y=0.98,
            yanchor="top",
            font=dict(size=13.5, color=COLORS["navy"]),
        ),
        showlegend=showlegend,
        legend=dict(
            orientation="h" if legend_horizontal else "v",
            yanchor="top",
            y=-0.16 if legend_horizontal else 1.0,
            x=0 if legend_horizontal else 1.02,
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
