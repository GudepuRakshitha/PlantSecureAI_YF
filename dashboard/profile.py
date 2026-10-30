"""Developer Profile module for SAFEGUARD dashboard.

Presents a professional portfolio view for Gudepu Rakshitha Reddy,
including professional summary, technical expertise, research & academic
highlights, and verified professional links.
"""

from __future__ import annotations

import html
from typing import Mapping

import streamlit as st

# ---------------------------------------------------------------------------
# Developer information & configurable settings
# ---------------------------------------------------------------------------

DEVELOPER_NAME = "GUDEPU RAKSHITHA REDDY"
DEVELOPER_INITIALS = "GR"
DEVELOPER_ROLE = "Project Developer"
DEVELOPER_HEADLINE = (
    "Computer Science Engineer | AI/ML Enthusiast | "
    "Associate AI Forward Deployed Engineer"
)

ABOUT_PARAGRAPHS = (
    (
        "I am a Computer Science graduate specializing in Artificial Intelligence "
        "and Machine Learning from Alliance University, Bengaluru, with a "
        "CGPA of 8.9/10."
    ),
    (
        "I have hands-on experience in Java Backend Development, Python, "
        "Spring Boot, SQL, Machine Learning, Deep Learning, NLP, and Generative AI."
    ),
    (
        "I have published 7 research papers in IEEE and Springer publications "
        "and completed 100+ technical certifications covering various technologies."
    ),
    (
        "I enjoy building AI-powered applications, exploring emerging technologies, "
        "solving real-world problems, and continuously improving my technical skills."
    ),
    (
        "I am passionate about developing practical AI solutions and contributing "
        "to innovative projects."
    ),
)

# Configurable profile links.
# The Google Drive portfolio URL can be added here when available.
GOOGLE_DRIVE_PORTFOLIO_URL: str | None = None

PROFILE_LINKS = {
    "linkedin": {
        "title": "LinkedIn",
        "label": "Professional Network & Recommendations",
        "url": "https://www.linkedin.com/in/gudepu-rakshitha-reddy-516aa72a9/",
        "icon": "linkedin",
        "action": "View LinkedIn Profile",
    },
    "github": {
        "title": "GitHub",
        "label": "Open-Source Code & Project Repositories",
        "url": "https://github.com/GudepuRakshitha",
        "icon": "github",
        "action": "Explore GitHub Repos",
    },
    "researchgate": {
        "title": "ResearchGate",
        "label": "Scientific Research & Publications",
        "url": "https://www.researchgate.net/profile/Rakshitha-Reddy-Gudepu",
        "icon": "researchgate",
        "action": "View Research Papers",
    },
    "blogs": {
        "title": "Technical Blogs",
        "label": "Engineering Articles & Insights",
        "url": "https://www.blogger.com/profile/08555579845123121571",
        "icon": "blogger",
        "action": "Read Technical Blogs",
    },
}

TECHNICAL_SKILLS: Mapping[str, tuple[str, ...]] = {
    "Backend & Languages": (
        "Java",
        "Python",
        "Spring Boot",
        "SQL",
        "REST APIs",
        "Object-Oriented Design",
    ),
    "AI, Machine Learning & NLP": (
        "Machine Learning",
        "Deep Learning",
        "Natural Language Processing (NLP)",
        "Generative AI",
        "Model Evaluation",
        "Applied AI Solutions",
    ),
    "Data & Analytics Stack": (
        "Data Pipeline Architecture",
        "Pandas",
        "NumPy",
        "Plotly",
        "Streamlit",
        "Statistical Quality Control",
    ),
    "Engineering Practices": (
        "Test-Driven Development",
        "Synthetic Data Validation",
        "Anomaly Detection",
        "Enterprise Dashboard Architecture",
        "Root Cause Analysis",
    ),
}

HIGHLIGHTS = (
    {
        "metric": "7 Papers",
        "title": "Research Publications",
        "desc": "Published in peer-reviewed IEEE and Springer conferences and journals.",
        "tag": "Peer-Reviewed",
    },
    {
        "metric": "100+",
        "title": "Technical Certifications",
        "desc": "Verified certifications covering AI, Cloud, Software Engineering and Data Science.",
        "tag": "Continuous Learning",
    },
    {
        "metric": "8.9 / 10",
        "title": "Alliance University",
        "desc": "B.Tech in Computer Science Engineering (Specialization: AI & ML), Bengaluru.",
        "tag": "Academic Excellence",
    },
    {
        "metric": "SAFEGUARD",
        "title": "Industrial Monitoring",
        "desc": "End-to-end industrial safety intelligence dashboard with anomaly oversight.",
        "tag": "Production Project",
    },
)


# ---------------------------------------------------------------------------
# SVG icons helper
# ---------------------------------------------------------------------------


def _render_svg(icon_name: str) -> str:
    """Return inline SVG markup for a given icon name."""
    if icon_name == "linkedin":
        return """<svg width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/>
<rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>"""
    if icon_name == "github":
        return """<svg width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
</svg>"""
    if icon_name == "researchgate":
        return """<svg width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="10"/>
<path d="M9 8h4.5a2.5 2.5 0 0 1 0 5H9m0-5v8m4.5-3 3 5"/>
</svg>"""
    if icon_name == "blogger":
        return """<svg width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect x="3" y="3" width="18" height="18" rx="4"/>
<circle cx="8.5" cy="9.5" r="1.5"/>
<path d="M8.5 14h7M12 17.5h3.5"/>
</svg>"""
    if icon_name == "drive":
        return """<svg width="18" height="18" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
<polyline points="14 2 14 8 20 8"/>
<line x1="16" y1="13" x2="8" y2="13"/>
<line x1="16" y1="17" x2="8" y2="17"/>
<polyline points="10 9 9 9 8 9"/>
</svg>"""
    if icon_name == "external":
        return """<svg width="13" height="13" viewBox="0 0 24 24" fill="none"
stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
<polyline points="15 3 21 3 21 9"/>
<line x1="10" y1="14" x2="21" y2="3"/>
</svg>"""
    return ""


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------


def navigate_to_profile() -> None:
    """Set the navigation state to Developer Profile."""
    st.session_state["navigation"] = "Developer Profile"


def navigate_to_dashboard() -> None:
    """Return to the last visited dashboard view or default to Overview."""
    last_page = st.session_state.get("_last_dashboard_page", "Overview")
    if last_page == "Developer Profile":
        last_page = "Overview"
    st.session_state["navigation"] = last_page


# ---------------------------------------------------------------------------
# Sidebar components
# ---------------------------------------------------------------------------


def render_sidebar_profile(is_active: bool = False) -> None:
    """Render the Developer Profile card and action button at sidebar bottom."""
    active_cls = "sidebar-profile-card sidebar-profile-card-active" if is_active else "sidebar-profile-card"

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">Project Developer</div>', unsafe_allow_html=True)

    card_html = f"""
    <div class="{active_cls}">
      <div class="sidebar-profile-header">
        <div class="sidebar-avatar" title="{html.escape(DEVELOPER_NAME)}">
          {DEVELOPER_INITIALS}
        </div>
        <div class="sidebar-profile-info">
          <div class="sidebar-profile-name">{html.escape(DEVELOPER_NAME)}</div>
          <div class="sidebar-profile-role">{html.escape(DEVELOPER_ROLE)}</div>
        </div>
      </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    st.button(
        "About the Developer",
        key="btn_about_developer_sidebar",
        on_click=navigate_to_profile,
        use_container_width=True,
    )


def render_sidebar_attribution() -> None:
    """Render a subtle, single clickable developer attribution at sidebar bottom."""
    st.markdown('<div class="sidebar-attribution-container">', unsafe_allow_html=True)
    if st.button(
        f"Developed by {DEVELOPER_NAME.title()}",
        key="btn_sidebar_attribution",
        on_click=navigate_to_profile,
        help="Open Developer Profile",
        use_container_width=True,
    ):
        pass
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main Developer Profile Page
# ---------------------------------------------------------------------------


def render_developer_profile() -> None:
    """Render the full enterprise Developer Profile portfolio page."""
    # Top breadcrumbs / Back to Dashboard action bar
    top_col1, top_col2 = st.columns([1.8, 6.2], vertical_alignment="center")
    with top_col1:
        st.button(
            "← Back to Dashboard",
            key="btn_back_to_dashboard_top",
            on_click=navigate_to_dashboard,
            help="Return to industrial safety monitoring dashboard",
        )
    with top_col2:
        st.markdown(
            '<div class="profile-breadcrumb">'
            '<span>SAFEGUARD</span> <span class="sep">/</span> '
            '<span class="curr">Developer Profile</span>'
            "</div>",
            unsafe_allow_html=True,
        )

    # 1. Profile Introduction
    intro_html = f"""
    <div class="profile-hero-card">
      <div class="profile-hero-main">
        <div class="profile-hero-avatar">{DEVELOPER_INITIALS}</div>
        <div class="profile-hero-content">
          <div class="profile-hero-badge">PROJECT DEVELOPER</div>
          <h1 class="profile-hero-name">{html.escape(DEVELOPER_NAME)}</h1>
          <div class="profile-hero-headline">{html.escape(DEVELOPER_HEADLINE)}</div>
          <div class="profile-hero-tags">
            <span class="profile-tag">Alliance University, Bengaluru</span>
            <span class="profile-tag">CGPA: 8.9 / 10.0</span>
            <span class="profile-tag">7 Research Publications</span>
            <span class="profile-tag">100+ Certifications</span>
          </div>
        </div>
      </div>
    </div>
    """
    st.markdown(intro_html, unsafe_allow_html=True)

    # 2. About Me Section
    st.markdown(
        """
        <div class="profile-section-header">
          <div class="profile-section-title">About Me</div>
          <div class="profile-section-sub">Background, academic foundation, and technical philosophy</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bio_paragraphs_html = "".join(
        f'<p class="profile-bio-p">{html.escape(p)}</p>' for p in ABOUT_PARAGRAPHS
    )
    st.markdown(
        f"""
        <div class="profile-card profile-bio-card">
          {bio_paragraphs_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Technical Expertise Section
    st.markdown(
        """
        <div class="profile-section-header">
          <div class="profile-section-title">Technical Expertise</div>
          <div class="profile-section-sub">Core programming languages, backend systems, AI/ML paradigms, and tooling</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    skills_cols = st.columns(2)
    cat_items = list(TECHNICAL_SKILLS.items())

    for idx, (category, items) in enumerate(cat_items):
        col = skills_cols[idx % 2]
        with col:
            pills = "".join(
                f'<span class="profile-skill-pill">{html.escape(skill)}</span>'
                for skill in items
            )
            col_html = f"""
            <div class="profile-card profile-skill-card">
              <div class="profile-skill-category">{html.escape(category)}</div>
              <div class="profile-skill-pills">{pills}</div>
            </div>
            """
            st.markdown(col_html, unsafe_allow_html=True)

    # 4. Research and Certifications Highlights
    st.markdown(
        """
        <div class="profile-section-header">
          <div class="profile-section-title">Research & Certifications Highlights</div>
          <div class="profile-section-sub">Peer-reviewed publications, academic credentials, and continuous learning</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    hl_cols = st.columns(4)
    for idx, hl in enumerate(HIGHLIGHTS):
        with hl_cols[idx]:
            card_html = f"""
            <div class="profile-card profile-highlight-card">
              <div class="profile-highlight-tag">{html.escape(hl['tag'])}</div>
              <div class="profile-highlight-metric">{html.escape(hl['metric'])}</div>
              <div class="profile-highlight-title">{html.escape(hl['title'])}</div>
              <div class="profile-highlight-desc">{html.escape(hl['desc'])}</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

    # 5. Professional Profiles Links
    st.markdown(
        """
        <div class="profile-section-header">
          <div class="profile-section-title">Professional Profiles & Connect</div>
          <div class="profile-section-sub">Verified academic, open-source, and professional profiles</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    link_cols = st.columns(2)

    # LinkedIn & GitHub
    with link_cols[0]:
        _render_profile_link_card("linkedin")
        _render_profile_link_card("researchgate")

    with link_cols[1]:
        _render_profile_link_card("github")
        _render_profile_link_card("blogs")

    # Certifications Portfolio (Configurable Google Drive link)
    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    _render_certifications_card()

    # Bottom Back button
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    b_col1, _ = st.columns([2, 6])
    with b_col1:
        st.button(
            "← Back to Dashboard",
            key="btn_back_to_dashboard_bottom",
            on_click=navigate_to_dashboard,
        )


def _render_profile_link_card(key: str) -> None:
    """Render a clickable card for a verified professional profile."""
    info = PROFILE_LINKS[key]
    svg_icon = _render_svg(info["icon"])
    ext_icon = _render_svg("external")
    url = info["url"]

    card_html = f"""
    <a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer" class="profile-link-card">
      <div class="profile-link-icon-wrap">
        {svg_icon}
      </div>
      <div class="profile-link-text">
        <div class="profile-link-title">{html.escape(info['title'])}</div>
        <div class="profile-link-label">{html.escape(info['label'])}</div>
      </div>
      <div class="profile-link-action">
        <span>{html.escape(info['action'])}</span>
        {ext_icon}
      </div>
    </a>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def _render_certifications_card() -> None:
    """Render the 100+ Technical Certifications Google Drive portfolio card."""
    drive_icon = _render_svg("drive")
    ext_icon = _render_svg("external")

    if GOOGLE_DRIVE_PORTFOLIO_URL:
        card_html = f"""
        <a href="{html.escape(GOOGLE_DRIVE_PORTFOLIO_URL)}" target="_blank" rel="noopener noreferrer" class="profile-link-card profile-cert-card">
          <div class="profile-link-icon-wrap">
            {drive_icon}
          </div>
          <div class="profile-link-text">
            <div class="profile-link-title">100+ Technical Certifications</div>
            <div class="profile-link-label">Google Drive Portfolio · Complete documentation & certificates</div>
          </div>
          <div class="profile-link-action">
            <span>Open Portfolio</span>
            {ext_icon}
          </div>
        </a>
        """
    else:
        card_html = f"""
        <div class="profile-link-card profile-cert-card profile-cert-configurable">
          <div class="profile-link-icon-wrap">
            {drive_icon}
          </div>
          <div class="profile-link-text">
            <div class="profile-link-title">100+ Technical Certifications — Google Drive Portfolio</div>
            <div class="profile-link-label">Repository link configurable in <code>dashboard/profile.py</code> (GOOGLE_DRIVE_PORTFOLIO_URL)</div>
          </div>
          <div class="profile-link-badge">
            <span class="badge badge-info">Portfolio Archive</span>
          </div>
        </div>
        """
    st.markdown(card_html, unsafe_allow_html=True)
