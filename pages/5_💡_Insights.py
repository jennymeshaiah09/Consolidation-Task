"""
Phase 5: Insights & Analytics
Advanced analytics and insights (Coming Soon)
"""

import streamlit as st

# Import UI utilities
from utils.ui_components import (
    apply_custom_css,
    render_page_header,
    render_progress_tracker,
    render_sidebar_info,
    render_custom_divider,
    render_info_banner,
    render_header_navigation,
    render_summary_section
)
from utils.state_manager import init_session_state

# Page configuration
st.set_page_config(
    page_title="Phase 5: Insights & Analytics",
    page_icon="💡",
    layout="wide"
)

# Initialize session state
init_session_state()

# Apply custom CSS
apply_custom_css()


def main():
    """Main page rendering"""
    render_header_navigation(current_page="Phase 5")

    # Page header
    render_page_header(
        title="Phase 5: Insights & Analytics",
        subtitle="Advanced analytics and insights from consolidated data",
        icon="💡"
    )

    # Progress tracker
    render_progress_tracker(current_phase=5)

    # Sidebar
    render_sidebar_info(current_phase=5)

    # Main content - Coming soon
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <div style="font-size: 5rem; margin-bottom: 24px;">🚧</div>
        <h2 style="color: var(--dark); margin-bottom: 16px;">Coming Soon</h2>
        <p style="font-size: 1.2rem; color: #64748b; max-width: 600px; margin: 0 auto;">
            Advanced analytics and insights features are currently in development.
            This phase will provide powerful analytics capabilities to help you understand your data better.
        </p>
    </div>
    """, unsafe_allow_html=True)

    render_custom_divider()

    # Planned features
    st.markdown("### 🎯 Planned Features")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 📊 Analytics

        - **Trend Analysis**
          - Product popularity trends over time
          - Category performance comparison
          - Brand analysis

        - **Seasonal Patterns**
          - Identify seasonal products
          - Peak month analysis
          - Year-over-year comparisons
        """)

    with col2:
        st.markdown("""
        #### 🔍 Keyword Intelligence

        - **Keyword Analysis**
          - Keyword clustering
          - Diversity metrics
          - Search intent patterns

        - **Performance Metrics**
          - Category effectiveness
          - Keyword quality scores
          - Optimization suggestions
        """)

    render_custom_divider()

    # Additional planned features
    st.markdown("### 🚀 Future Enhancements")

    features = [
        ("📈", "Historical Comparison", "Compare performance across multiple time periods"),
        ("🎨", "Custom Dashboards", "Create personalized analytics dashboards"),
        ("📧", "Automated Reports", "Schedule and email regular insight reports"),
        ("🤖", "AI Recommendations", "Get AI-powered product optimization suggestions"),
        ("📊", "Data Export", "Export insights in multiple formats (CSV, JSON, PDF)"),
        ("🔗", "API Integration", "Connect with external analytics platforms"),
    ]

    cols = st.columns(2)
    for i, (icon, title, description) in enumerate(features):
        with cols[i % 2]:
            st.markdown(f"""
            <div style="background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px; border: 1px solid #e5e7eb;">
                <div style="font-size: 2rem; margin-bottom: 12px;">{icon}</div>
                <h4 style="color: var(--dark); margin-bottom: 8px;">{title}</h4>
                <p style="color: #64748b; margin: 0; font-size: 0.9rem;">{description}</p>
            </div>
            """, unsafe_allow_html=True)

    render_custom_divider()

    # Feedback section
    st.markdown("### 💬 Feedback & Suggestions")

    render_info_banner(
        "We'd love to hear your feedback! What insights would be most valuable for your workflow?",
        "info"
    )

    with st.form("feedback_form"):
        st.markdown("**Share your ideas:**")

        feedback_type = st.selectbox(
            "What type of insight would you find most helpful?",
            [
                "Trend Analysis",
                "Seasonal Patterns",
                "Keyword Intelligence",
                "Performance Metrics",
                "Custom Dashboards",
                "Other"
            ]
        )

        feedback_text = st.text_area(
            "Additional details (optional)",
            placeholder="Tell us more about what you'd like to see...",
            height=100
        )

        submitted = st.form_submit_button("Submit Feedback", type="primary")

        if submitted:
            st.success("✅ Thank you for your feedback! Your suggestions help us improve.")
            st.balloons()

    # Navigation
    render_custom_divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back to Phase 4", use_container_width=True):
            st.switch_page("pages/4_⭐_Peak_Analysis.py")

    with col2:
        if st.button("🏠 Back to Home", type="primary", use_container_width=True):
            st.switch_page("Home.py")

    with col3:
        if st.button("Start New Session →", use_container_width=True):
            st.switch_page("pages/1_📊_Data_Consolidation.py")

    # Footer
    render_custom_divider()
    st.caption("💡 Have ideas for this phase? Please share your feedback above!")


if __name__ == "__main__":
    main()
