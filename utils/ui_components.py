"""
UI Components — Meridian design system for the consolidation pipeline.
"""

from __future__ import annotations

import streamlit as st
from typing import Optional, Dict, Any, List, Tuple


# ---------------------------------------------------------------------------
# Design tokens (mirrored in CSS)
# ---------------------------------------------------------------------------
BRAND_NAME = "Meridian"
BRAND_TAGLINE = "Product data consolidation"

NAV_ITEMS: List[Tuple[str, str, str]] = [
    ("Home", "Home", "Home.py"),
    ("01", "Consolidate", "pages/01_Consolidate.py"),
    ("02", "Keywords", "pages/02_Keywords.py"),
    ("03", "MSV", "pages/03_MSV.py"),
    ("04", "Peaks", "pages/04_Peaks.py"),
    ("05", "Insights", "pages/05_Insights.py"),
]

TOOL_ITEMS: List[Tuple[str, str, str]] = [
    ("Gen", "Keyword Gen", "pages/06_Keyword_Generator.py"),
    ("Chk", "Verifier", "pages/07_Keyword_Verifier.py"),
]


def apply_custom_css():
    """Inject Meridian theme CSS once per page."""
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Figtree:wght@400;500;600;700&display=swap');

:root {
  --ink: #0B1F2A;
  --ink-soft: #243B48;
  --mist: #F4F6F8;
  --paper: #FFFFFF;
  --line: #D5DEE5;
  --line-soft: #E8EEF2;
  --accent: #FF5C35;
  --accent-deep: #E04520;
  --accent-soft: #FFE8E1;
  --teal: #1F6F78;
  --teal-soft: #E4F3F4;
  --ok: #1B7A4E;
  --ok-soft: #E3F5EB;
  --warn: #A15C12;
  --warn-soft: #FFF1DC;
  --muted: #5C7380;
  --radius: 14px;
  --shadow: 0 1px 0 rgba(11, 31, 42, 0.04), 0 12px 32px rgba(11, 31, 42, 0.06);
  --font-display: 'Bricolage Grotesque', Georgia, serif;
  --font-body: 'Figtree', system-ui, sans-serif;
}

html, body, [class*="css"] {
  font-family: var(--font-body) !important;
}

.stApp {
  background:
    radial-gradient(1200px 500px at 12% -10%, rgba(255, 92, 53, 0.10), transparent 55%),
    radial-gradient(900px 420px at 100% 0%, rgba(31, 111, 120, 0.10), transparent 50%),
    linear-gradient(180deg, #EEF3F6 0%, var(--mist) 40%, #F7F9FA 100%) !important;
}

.block-container {
  padding-top: 1.25rem !important;
  padding-bottom: 3rem !important;
  max-width: 1180px !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; height: 0; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0B1F2A 0%, #132A36 55%, #183643 100%) !important;
  border-right: 1px solid rgba(255,255,255,0.06) !important;
}
section[data-testid="stSidebar"] * {
  color: #E8EEF2 !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] .stCaption {
  color: rgba(232, 238, 242, 0.72) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
  padding-top: 0.5rem;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
  border-radius: 10px !important;
  margin: 2px 8px !important;
  padding: 0.55rem 0.75rem !important;
  font-weight: 500 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
  background: rgba(255,255,255,0.06) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
  background: rgba(255, 92, 53, 0.18) !important;
  box-shadow: inset 3px 0 0 var(--accent);
}
section[data-testid="stSidebar"] hr {
  border-color: rgba(255,255,255,0.1) !important;
}
section[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,0.06) !important;
  color: #fff !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255, 92, 53, 0.22) !important;
  border-color: var(--accent) !important;
}

/* Typography overrides for Streamlit widgets */
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  font-family: var(--font-display) !important;
  color: var(--ink) !important;
  letter-spacing: -0.02em;
}

/* Brand bar */
.m-brandbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 0.85rem 1.1rem;
  background: rgba(255,255,255,0.72);
  backdrop-filter: blur(10px);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow);
}
.m-brand {
  display: flex;
  align-items: baseline;
  gap: 0.65rem;
  min-width: 0;
}
.m-brand-mark {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 1.35rem;
  color: var(--ink);
  letter-spacing: -0.04em;
  line-height: 1;
}
.m-brand-mark span {
  color: var(--accent);
}
.m-brand-sub {
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.m-phase-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

/* Hero (home) */
.m-hero {
  position: relative;
  overflow: hidden;
  border-radius: 24px;
  padding: 2.75rem 2.5rem 2.5rem;
  margin-bottom: 1.75rem;
  background:
    linear-gradient(135deg, rgba(11,31,42,0.92) 0%, rgba(31,111,120,0.88) 55%, rgba(255,92,53,0.75) 100%),
    radial-gradient(circle at 80% 20%, rgba(255,255,255,0.18), transparent 40%);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 24px 60px rgba(11, 31, 42, 0.22);
  animation: m-fade-up 0.55s ease both;
}
.m-hero::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(120deg, transparent 10%, #000 60%);
  pointer-events: none;
}
.m-hero-inner { position: relative; z-index: 1; max-width: 640px; }
.m-hero-kicker {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.78);
  margin-bottom: 0.85rem;
}
.m-hero-title {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: clamp(2.4rem, 4.5vw, 3.4rem);
  letter-spacing: -0.045em;
  line-height: 0.98;
  margin: 0 0 0.85rem 0;
}
.m-hero-title em {
  font-style: normal;
  color: #FFD2C5;
}
.m-hero-copy {
  font-size: 1.05rem;
  line-height: 1.55;
  color: rgba(255,255,255,0.88);
  margin: 0;
  max-width: 34rem;
}

/* Page header */
.m-pagehead {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  align-items: end;
  margin: 0.25rem 0 1.5rem;
  padding-bottom: 1.1rem;
  border-bottom: 1px solid var(--line);
  animation: m-fade-up 0.4s ease both;
}
.m-pagehead-kicker {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.35rem;
}
.m-pagehead h1 {
  font-family: var(--font-display) !important;
  font-size: clamp(1.7rem, 2.6vw, 2.15rem) !important;
  font-weight: 800 !important;
  letter-spacing: -0.03em !important;
  margin: 0 !important;
  color: var(--ink) !important;
}
.m-pagehead p {
  margin: 0.4rem 0 0 !important;
  color: var(--muted) !important;
  font-size: 1rem !important;
  max-width: 42rem;
}

/* Metrics */
.m-metric {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1.05rem 1.15rem;
  box-shadow: var(--shadow);
  height: 100%;
  transition: transform 0.2s ease, border-color 0.2s ease;
  animation: m-fade-up 0.45s ease both;
}
.m-metric:hover {
  transform: translateY(-2px);
  border-color: #B7C8D2;
}
.m-metric-label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.45rem;
}
.m-metric-value {
  font-family: var(--font-display);
  font-size: 1.85rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--ink);
  line-height: 1.1;
}

/* Phase cards */
.m-phase {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 1.35rem 1.35rem 1.15rem;
  box-shadow: var(--shadow);
  height: 100%;
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
  animation: m-fade-up 0.5s ease both;
}
.m-phase:hover {
  transform: translateY(-3px);
  border-color: rgba(255, 92, 53, 0.45);
  box-shadow: 0 16px 40px rgba(11, 31, 42, 0.10);
}
.m-phase-num {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.55rem;
}
.m-phase h3 {
  font-family: var(--font-display) !important;
  font-size: 1.25rem !important;
  font-weight: 750 !important;
  margin: 0 0 0.45rem !important;
  color: var(--ink) !important;
  letter-spacing: -0.02em;
}
.m-phase p {
  color: var(--muted) !important;
  font-size: 0.95rem !important;
  line-height: 1.5 !important;
  margin: 0 0 0.9rem !important;
  min-height: 2.8rem;
}

/* Status badges */
.m-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.m-badge-ready, .m-badge-complete {
  background: var(--ok-soft);
  color: var(--ok);
}
.m-badge-pending {
  background: var(--warn-soft);
  color: var(--warn);
}
.m-badge-in-progress {
  background: var(--teal-soft);
  color: var(--teal);
}
.m-badge-tenny {
  background: #EDE7FF;
  color: #4C3A9B;
}
.m-badge-coming-soon {
  background: var(--line-soft);
  color: var(--muted);
}

/* Progress tracker */
.m-progress {
  display: flex;
  gap: 0.5rem;
  margin: 0 0 1.5rem;
  padding: 0.85rem;
  background: rgba(255,255,255,0.7);
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow-x: auto;
}
.m-step {
  flex: 1;
  min-width: 88px;
  text-align: center;
  padding: 0.55rem 0.4rem;
  border-radius: 12px;
  border: 1px solid transparent;
}
.m-step.active {
  background: var(--accent-soft);
  border-color: rgba(255, 92, 53, 0.25);
}
.m-step.complete {
  background: var(--ok-soft);
}
.m-step-dot {
  width: 28px;
  height: 28px;
  margin: 0 auto 0.35rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 800;
  background: var(--line-soft);
  color: var(--muted);
}
.m-step.active .m-step-dot {
  background: var(--accent);
  color: #fff;
}
.m-step.complete .m-step-dot {
  background: var(--ok);
  color: #fff;
}
.m-step-label {
  font-size: 0.7rem;
  font-weight: 650;
  color: var(--muted);
  letter-spacing: 0.02em;
}
.m-step.active .m-step-label { color: var(--accent-deep); }
.m-step.complete .m-step-label { color: var(--ok); }

/* Banners */
.m-banner {
  border-radius: 14px;
  padding: 1rem 1.15rem;
  margin: 0.85rem 0 1.25rem;
  border: 1px solid var(--line);
  background: var(--paper);
  box-shadow: var(--shadow);
}
.m-banner.info {
  border-left: 4px solid var(--teal);
  background: linear-gradient(90deg, var(--teal-soft), var(--paper) 55%);
}
.m-banner.warning {
  border-left: 4px solid var(--warn);
  background: linear-gradient(90deg, var(--warn-soft), var(--paper) 55%);
}
.m-banner p {
  margin: 0 !important;
  color: var(--ink-soft) !important;
  font-weight: 500 !important;
  font-size: 0.95rem !important;
}

/* Summary */
.m-summary {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 1.25rem 1.25rem 0.5rem;
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow);
}
.m-summary-title {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 750;
  color: var(--ink);
  margin-bottom: 1rem;
  letter-spacing: -0.02em;
}

/* Divider */
.m-divider {
  height: 1px;
  border: none;
  margin: 1.75rem 0;
  background: linear-gradient(90deg, transparent, var(--line), transparent);
}

/* Section labels used in page markdown */
.m-section-label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 0.35rem;
}

/* Buttons */
.stButton > button {
  border-radius: 11px !important;
  font-family: var(--font-body) !important;
  font-weight: 650 !important;
  letter-spacing: 0.01em;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease !important;
  border: 1px solid var(--line) !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: var(--accent) !important;
  color: #fff !important;
  border-color: var(--accent) !important;
  box-shadow: 0 8px 20px rgba(255, 92, 53, 0.28) !important;
}
.stButton > button:hover {
  transform: translateY(-1px);
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
  background: var(--accent-deep) !important;
  border-color: var(--accent-deep) !important;
}

/* Inputs / uploaders */
[data-testid="stFileUploader"] {
  background: var(--paper);
  border: 1.5px dashed #B7C8D2;
  border-radius: 16px;
  padding: 0.75rem;
}
[data-testid="stFileUploader"]:hover {
  border-color: var(--accent);
  background: #FFFBF9;
}
div[data-baseweb="select"] > div,
.stTextInput input, .stNumberInput input {
  border-radius: 10px !important;
}

/* Dataframes */
[data-testid="stDataFrame"] {
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 0.35rem;
  background: transparent;
  border-bottom: 1px solid var(--line);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 10px 10px 0 0;
  font-weight: 650;
  color: var(--muted);
}
.stTabs [aria-selected="true"] {
  color: var(--ink) !important;
  background: rgba(255,255,255,0.8);
}

/* Expanders */
[data-testid="stExpander"] {
  border: 1px solid var(--line) !important;
  border-radius: 14px !important;
  background: var(--paper);
  box-shadow: var(--shadow);
}

/* Alerts */
[data-testid="stAlert"] {
  border-radius: 12px !important;
}

@keyframes m-fade-up {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .m-hero { padding: 1.75rem 1.25rem; border-radius: 18px; }
  .m-hero-title { font-size: 2rem; }
  .m-brand-sub { display: none; }
  .m-pagehead { grid-template-columns: 1fr; }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_bar(current_page: str = "Home", phase_label: Optional[str] = None):
    """Top brand strip with optional phase chip."""
    chip = (
        f'<div class="m-phase-chip">{phase_label}</div>'
        if phase_label
        else '<div class="m-phase-chip">Pipeline</div>'
    )
    st.markdown(
        f"""
<div class="m-brandbar">
  <div class="m-brand">
    <div class="m-brand-mark">Meri<span>dian</span></div>
    <div class="m-brand-sub">{BRAND_TAGLINE}</div>
  </div>
  {chip}
</div>
        """,
        unsafe_allow_html=True,
    )


def render_top_nav(current_page: str = "Home"):
    """Primary phase navigation using Streamlit page switching."""
    items = NAV_ITEMS
    cols = st.columns(len(items))
    for idx, (short, label, path) in enumerate(items):
        is_active = (
            current_page == label
            or current_page == short
            or (current_page == "Home" and label == "Home")
            or (f"Phase {short}" == current_page)
            or (current_page.startswith("Phase") and label.lower() in current_page.lower())
        )
        # Match common current_page strings used across pages
        active_map = {
            "Home": "Home",
            "Phase 1": "Consolidate",
            "Phase 2": "Keywords",
            "Phase 3": "MSV",
            "Phase 4": "Peaks",
            "Phase 5": "Insights",
            "Verifier": "Verifier",
            "Generator": "Keyword Gen",
        }
        mapped = active_map.get(current_page, current_page)
        is_active = mapped == label or current_page == label

        with cols[idx]:
            btn_type = "primary" if is_active else "secondary"
            display = label if label == "Home" else f"{short} {label}"
            if st.button(
                display,
                key=f"topnav_{idx}_{label}",
                use_container_width=True,
                type=btn_type,
            ):
                st.switch_page(path)


def render_header_navigation(current_page: str = "Phase 1"):
    """Compat wrapper used by existing pages."""
    render_brand_bar(current_page=current_page, phase_label=current_page)
    # Home already has phase cards — skip redundant top button row there
    if current_page != "Home":
        render_top_nav(current_page=current_page)


def render_page_header(title: str, subtitle: str, icon: str = ""):
    """Clean page header — icon optional, brand-adjacent typography."""
    # Strip leading emoji/noise if callers still pass them via title
    clean_title = title.strip()
    for prefix in ("📊 ", "🔤 ", "📈 ", "⭐ ", "💡 ", "🔑 ", "✅ ", "🎯 "):
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix) :]
    st.markdown(
        f"""
<div class="m-pagehead">
  <div>
    <div class="m-pagehead-kicker">Meridian pipeline</div>
    <h1>{clean_title}</h1>
    <p>{subtitle}</p>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_hero_section(title: str = "", subtitle: str = ""):
    """Home hero — brand-first composition."""
    st.markdown(
        f"""
<div class="m-hero">
  <div class="m-hero-inner">
    <div class="m-hero-kicker">Catalog intelligence</div>
    <h1 class="m-hero-title">Meri<em>dian</em></h1>
    <p class="m-hero-copy">
      Consolidate monthly product data, classify into taxonomy, generate
      MSV-ready keywords, and surface seasonal peaks — in one pipeline.
    </p>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, icon: str = ""):
    """Compact metric tile."""
    st.markdown(
        f"""
<div class="m-metric">
  <div class="m-metric-label">{label}</div>
  <div class="m-metric-value">{value}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_status_badge(status: str) -> str:
    """Return HTML for a status badge."""
    status_classes = {
        "Ready": "m-badge-ready",
        "Complete": "m-badge-complete",
        "Pending": "m-badge-pending",
        "In Progress": "m-badge-in-progress",
        "Tenny's Work": "m-badge-tenny",
        "Coming Soon": "m-badge-coming-soon",
    }
    status_class = status_classes.get(status, "m-badge-pending")
    return f'<span class="m-badge {status_class}">{status}</span>'


def render_phase_card(
    phase_num: int,
    title: str,
    description: str,
    status: str,
    icon: str = "",
    page_link: Optional[str] = None,
):
    """Phase overview card + enter button."""
    status_badge = render_status_badge(status)
    st.markdown(
        f"""
<div class="m-phase">
  <div class="m-phase-num">Phase {phase_num:02d}</div>
  <h3>{title}</h3>
  <p>{description}</p>
  {status_badge}
</div>
        """,
        unsafe_allow_html=True,
    )
    if page_link:
        if st.button(
            "Open phase",
            key=f"phase_enter_{phase_num}",
            use_container_width=True,
            type="primary" if status in ("Ready", "Complete", "In Progress") else "secondary",
        ):
            # page_link may be a stem like "01_Consolidate" or full path
            path = page_link
            if not path.endswith(".py"):
                path = f"pages/{path}.py"
            elif not path.startswith("pages/") and path != "Home.py":
                path = f"pages/{path}"
            st.switch_page(path)


def render_progress_tracker(current_phase: int, total_phases: int = 5):
    """Horizontal phase progress strip."""
    phase_labels = ["Consolidate", "Keywords", "MSV", "Peaks", "Insights"]
    parts = ['<div class="m-progress">']
    for i in range(1, total_phases + 1):
        if i < current_phase:
            cls = "complete"
        elif i == current_phase:
            cls = "active"
        else:
            cls = "inactive"
        label = phase_labels[i - 1] if i - 1 < len(phase_labels) else f"P{i}"
        parts.append(
            f"""
<div class="m-step {cls}">
  <div class="m-step-dot">{i}</div>
  <div class="m-step-label">{label}</div>
</div>
            """
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_info_banner(message: str, banner_type: str = "info"):
    """Inline information / warning banner."""
    banner_class = "info" if banner_type == "info" else "warning"
    st.markdown(
        f"""
<div class="m-banner {banner_class}">
  <p>{message}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_info(current_phase: Optional[Any] = None):
    """Sidebar helper copy — keeps dark theme readable."""
    with st.sidebar:
        st.markdown("### Pipeline")
        st.caption("Work phases in order. Session data persists across pages.")
        if current_phase is not None:
            label = (
                f"Phase {current_phase}"
                if isinstance(current_phase, int)
                else str(current_phase)
            )
            st.markdown(f"**Current:** {label}")
        st.markdown("---")
        st.markdown("**Flow**")
        st.markdown(
            """
1. Consolidate  
2. Keywords  
3. MSV  
4. Peaks  
5. Insights  
            """
        )
        st.markdown("---")
        st.caption("Tools")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Generator", key="sb_gen", use_container_width=True):
                st.switch_page("pages/06_Keyword_Generator.py")
        with c2:
            if st.button("Verifier", key="sb_ver", use_container_width=True):
                st.switch_page("pages/07_Keyword_Verifier.py")


def render_custom_divider():
    """Subtle horizontal rule."""
    st.markdown('<hr class="m-divider">', unsafe_allow_html=True)


def render_summary_section(title: str, metrics: Dict[str, Any], icon: str = ""):
    """Aligned summary metrics block."""
    clean_title = title
    for prefix in ("📊 ", "📈 ", "🔤 ", "⭐ ", "💡 "):
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix) :]

    st.markdown(
        f"""
<div class="m-summary">
  <div class="m-summary-title">{clean_title}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(len(metrics))
    for idx, (label, value) in enumerate(metrics.items()):
        with cols[idx]:
            if isinstance(value, tuple):
                display_value, _metric_icon = value
            else:
                display_value = value
            render_metric_card(label, str(display_value))


def render_section_heading(title: str, subtitle: str = ""):
    """Consistent in-page section heading."""
    sub = f'<p style="margin:0.15rem 0 0.85rem;color:var(--muted);">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
<div style="margin:1.25rem 0 0.75rem;">
  <div class="m-section-label">Section</div>
  <h3 style="margin:0;font-family:var(--font-display);letter-spacing:-0.02em;">{title}</h3>
  {sub}
</div>
        """,
        unsafe_allow_html=True,
    )
