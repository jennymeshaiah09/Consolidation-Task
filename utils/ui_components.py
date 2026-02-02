"""
UI Components Module
Reusable components for consistent modern design across all pages
"""

import streamlit as st
from typing import Optional, Dict, Any


def apply_custom_css():
    """Apply custom CSS styling for modern look with Green/Teal theme"""
    st.markdown("""
    <style>
    /* Color Scheme Variables */
    :root {
        --primary: #10b981;
        --secondary: #14b8a6;
        --accent: #6ee7b7;
        --success: #22c55e;
        --warning: #f59e0b;
        --info: #06b6d4;
        --dark: #0f172a;
        --light: #f0fdfa;
    }

    /* Global Styles */
    .main {
        background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%);
    }

    /* Modern Card Styling */
    .phase-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease;
        border: 1px solid rgba(16, 185, 129, 0.1);
        margin-bottom: 20px;
    }

    .phase-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        border-color: var(--primary);
    }

    /* Hero Section */
    .hero-section {
        background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
        color: white;
        padding: 48px 32px;
        border-radius: 16px;
        margin-bottom: 32px;
        text-align: center;
    }

    .hero-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 12px;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .hero-subtitle {
        font-size: 1.2rem;
        opacity: 0.95;
        margin-bottom: 0;
    }

    /* Metric Cards */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-left: 4px solid var(--primary);
        margin-bottom: 16px;
    }

    .metric-label {
        font-size: 0.875rem;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--dark);
        margin: 0;
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 600;
        margin: 8px 0;
    }

    .status-ready {
        background: #d1fae5;
        color: #065f46;
    }

    .status-complete {
        background: #d1fae5;
        color: #065f46;
    }

    .status-pending {
        background: #fef3c7;
        color: #92400e;
    }

    .status-in-progress {
        background: #dbeafe;
        color: #1e40af;
    }

    .status-tenny {
        background: #e0e7ff;
        color: #3730a3;
    }

    .status-coming-soon {
        background: #f3f4f6;
        color: #4b5563;
    }

    /* Page Header */
    .page-header {
        background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
        color: white;
        padding: 32px;
        border-radius: 12px;
        margin-bottom: 32px;
    }

    .page-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }

    .page-header p {
        margin: 8px 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }

    /* Progress Tracker */
    .progress-tracker {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 32px 0;
        padding: 0 20px;
    }

    .progress-step {
        flex: 1;
        text-align: center;
        position: relative;
    }

    .progress-dot {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        margin: 0 auto 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }

    .progress-dot.active {
        background: var(--primary);
        color: white;
        box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.3);
    }

    .progress-dot.inactive {
        background: #e5e7eb;
        color: #9ca3af;
    }

    .progress-dot.complete {
        background: var(--success);
        color: white;
    }

    .progress-label {
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 500;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Info Banner */
    .info-banner {
        background: linear-gradient(135deg, #dbeafe 0%, #e0f2fe 100%);
        border-left: 4px solid var(--info);
        padding: 20px;
        border-radius: 8px;
        margin: 20px 0;
    }

    .warning-banner {
        background: linear-gradient(135deg, #fef3c7 0%, #fef9c3 100%);
        border-left: 4px solid var(--warning);
        padding: 20px;
        border-radius: 8px;
        margin: 20px 0;
    }

    /* Data Preview Table */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Sidebar Styling */
    .css-1d391kg {
        background: #f8fafc;
    }

    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Custom Divider */
    .custom-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--primary), transparent);
        margin: 32px 0;
        border: none;
    }

    /* Header Navigation Bar */
    .header-nav {
        background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
        padding: 16px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .header-nav-title {
        color: white;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
    }

    .header-nav-links {
        display: flex;
        gap: 8px;
        align-items: center;
    }

    .nav-link {
        color: white;
        text-decoration: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s ease;
        background: rgba(255, 255, 255, 0.1);
        font-size: 0.9rem;
    }

    .nav-link:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: translateY(-1px);
    }

    .nav-link.active {
        background: rgba(255, 255, 255, 0.25);
        font-weight: 600;
    }

    /* Summary Section */
    .summary-section {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
    }

    .summary-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--dark);
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
    }

    /* Improved Metric Card Alignment */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border-left: 4px solid var(--primary);
        margin-bottom: 0;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    </style>
    """, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str, icon: str = "🎯"):
    """Render consistent page header with gradient background"""
    st.markdown(f"""
    <div class="page-header">
        <h1>{icon} {title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_hero_section(title: str, subtitle: str):
    """Render hero section for homepage"""
    st.markdown(f"""
    <div class="hero-section">
        <div class="hero-title">{title}</div>
        <div class="hero-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, icon: str = ""):
    """Render modern metric card"""
    icon_html = f'<span style="font-size: 1.5rem; margin-right: 8px;">{icon}</span>' if icon else ''
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{icon_html}{value}</div>
    </div>
    """, unsafe_allow_html=True)


def render_status_badge(status: str) -> str:
    """Return HTML for status badge"""
    status_classes = {
        "Ready": "status-ready",
        "Complete": "status-complete",
        "Pending": "status-pending",
        "In Progress": "status-in-progress",
        "Tenny's Work": "status-tenny",
        "Coming Soon": "status-coming-soon"
    }

    status_class = status_classes.get(status, "status-pending")
    return f'<span class="status-badge {status_class}">{status}</span>'


def render_phase_card(
    phase_num: int,
    title: str,
    description: str,
    status: str,
    icon: str,
    page_link: Optional[str] = None
):
    """Render phase card for homepage"""
    status_badge = render_status_badge(status)
    button_html = ""

    if page_link:
        button_html = f'<a href="{page_link}" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #10b981, #14b8a6); color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; cursor: pointer; margin-top: 16px;">Enter Phase →</button></a>'

    st.markdown(f"""
    <div class="phase-card">
        <div style="font-size: 2.5rem; margin-bottom: 12px;">{icon}</div>
        <h3 style="color: var(--dark); margin-bottom: 8px;">Phase {phase_num}: {title}</h3>
        <p style="color: #64748b; margin-bottom: 12px;">{description}</p>
        {status_badge}
        {button_html}
    </div>
    """, unsafe_allow_html=True)


def render_progress_tracker(current_phase: int, total_phases: int = 5):
    """Render visual progress tracker"""
    progress_html = '<div class="progress-tracker">'

    phase_labels = ["Consolidate", "Keywords", "MSV", "Peaks", "Insights"]

    for i in range(1, total_phases + 1):
        if i < current_phase:
            dot_class = "complete"
        elif i == current_phase:
            dot_class = "active"
        else:
            dot_class = "inactive"

        progress_html += f"""
        <div class="progress-step">
            <div class="progress-dot {dot_class}">{i}</div>
            <div class="progress-label">{phase_labels[i-1]}</div>
        </div>
        """

        # Add arrow between steps (except after last)
        if i < total_phases:
            progress_html += '<div style="flex: 0 0 40px; text-align: center; color: #d1d5db;">→</div>'

    progress_html += '</div>'
    st.markdown(progress_html, unsafe_allow_html=True)


def render_info_banner(message: str, banner_type: str = "info"):
    """Render information banner"""
    banner_class = "info-banner" if banner_type == "info" else "warning-banner"
    st.markdown(f"""
    <div class="{banner_class}">
        <p style="margin: 0; font-weight: 500;">{message}</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_info(current_phase: Optional[int] = None):
    """Render standardized sidebar content"""
    with st.sidebar:
        st.markdown("### 🗺️ Navigation")
        st.markdown("Use the sidebar to navigate between phases or return to the homepage.")

        if current_phase:
            st.markdown("---")
            st.markdown(f"### 📍 Current Phase")
            st.info(f"You are in Phase {current_phase}")

        st.markdown("---")
        st.markdown("### ℹ️ Help")
        st.markdown("""
        **Phase Order:**
        1. Data Consolidation
        2. Keywords & Categories
        3. MSV Management
        4. Peak Analysis
        5. Insights
        """)


def render_custom_divider():
    """Render custom styled divider"""
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)


def render_header_navigation(current_page: str = "Phase 1"):
    """Render simple phase navigation buttons"""
    # Only phases - no Home page
    nav_items = [
        ("📊", "Phase 1", "pages/1_📊_Data_Consolidation.py"),
        ("🔤", "Phase 2", "pages/2_🔤_Keywords_Categories.py"),
        ("📈", "Phase 3", "pages/3_📈_MSV_Management.py"),
        ("⭐", "Phase 4", "pages/4_⭐_Peak_Analysis.py"),
        ("💡", "Phase 5", "pages/5_💡_Insights.py"),
    ]

    # Just render the navigation buttons - no top bar
    cols = st.columns(len(nav_items))
    for idx, (icon, label, page_path) in enumerate(nav_items):
        with cols[idx]:
            button_type = "primary" if current_page in label else "secondary"
            if st.button(f"{icon} {label}", key=f"nav_{idx}", use_container_width=True, type=button_type):
                st.switch_page(page_path)


def render_summary_section(title: str, metrics: Dict[str, Any], icon: str = "📊"):
    """Render aligned summary section with metrics"""
    st.markdown(f"""
    <div class="summary-section">
        <div class="summary-title">{icon} {title}</div>
        <div class="summary-grid">
    """, unsafe_allow_html=True)

    # Use columns for proper alignment
    cols = st.columns(len(metrics))
    for idx, (label, value) in enumerate(metrics.items()):
        with cols[idx]:
            # Extract icon if provided in value
            if isinstance(value, tuple):
                display_value, metric_icon = value
            else:
                display_value = value
                metric_icon = ""

            render_metric_card(label, str(display_value), metric_icon)

    st.markdown('</div></div>', unsafe_allow_html=True)
