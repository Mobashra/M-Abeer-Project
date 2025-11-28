import streamlit as st
import utils

# ======================================================
# PAGE CONFIGURATION
# ======================================================
st.set_page_config(
    page_title="Energy Atlas",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Render the sidebar (ensure utils.py has the updated styling from previous steps)
utils.render_sidebar()

# ======================================================
# HERO SECTION
# ======================================================
st.title("⚡ Norwegian Energy & Weather Atlas")
st.markdown("""
<style>
    .big-font { font-size: 1.2rem; color: #555; }
    .highlight { color: #2E86C1; font-weight: bold; }
</style>
<p class="big-font">
    Bridging the gap between <span class="highlight">Meteorological Drivers</span> and 
    <span class="highlight">Energy Market Dynamics</span>.
</p>
""", unsafe_allow_html=True)

st.markdown("---")

# ======================================================
# DATA SOURCES & CONTEXT
# ======================================================
with st.expander("📚 Data Sources & Methodology", expanded=True):
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("**⚡ Energy Data**")
        st.markdown("Sourced from **Elhub** and **Nord Pool**.")
        st.caption("Granularity: Hourly • Range: 2021-2024")
    
    with c2:
        st.markdown("**☁️ Weather Data**")
        st.markdown("Sourced from **Open-Meteo (ERA5 Reanalysis)**.")
        st.caption("Variables: Temp, Wind, Precip • Lag: 5-day")
        
    with c3:
        st.markdown("**🗺️ Geospatial**")
        st.markdown("Boundaries from **Kartverket**.")
        st.caption("Levels: Price Areas (NO1-NO5) & Municipalities")

st.markdown("### 🧭 Select an Analysis Module")

# ======================================================
# NAVIGATION CARDS (THE 3 PILLARS)
# ======================================================
# We use containers to create "Cards" for the three logical groupings

col_exp, col_diag, col_pred = st.columns(3, gap="medium")

# --- 1. EXPLORATIVE (BLUE) ---
with col_exp:
    with st.container(border=True):
        st.markdown("### 🟦 Explorative")
        st.markdown("*\"What happened and where?\"*")
        st.markdown("Visualizing historical trends across regions.")
        
        st.divider()
        
        st.page_link("pages/01_Map_Selector.py", label="Map Selector", icon="🗺️", help="Select Region & Coordinates")
        st.page_link("pages/02_Energy_Stats.py", label="Energy Statistics", icon="⚡", help="Production & Consumption Trends")
        st.page_link("pages/03_Weather_Stats.py", label="Weather Statistics", icon="🌤️", help="Climate trends 2021-2024")

# --- 2. DIAGNOSTIC (GREEN) ---
with col_diag:
    with st.container(border=True):
        st.markdown("### 🟩 Diagnostic")
        st.markdown("*\"Why did it happen?\"*")
        st.markdown("Identifying relationships and anomalies.")
        
        st.divider()
        
        st.page_link("pages/04_Correlations.py", label="Correlation Analysis", icon="🔗", help="Wind vs Production, Temp vs Consumption")
        st.page_link("pages/05_Anomalies.py", label="Anomaly Detection", icon="⚠️", help="Detect Outliers in Weather Data")
        st.page_link("pages/06_Signal_Processing.py", label="Signal Processing", icon="⚠️", help="Detect Outliers in Weather Data")

# --- 3. PREDICTIVE (PURPLE) ---
with col_pred:
    with st.container(border=True):
        st.markdown("### 🟪 Predictive")
        st.markdown("*\"What happens next?\"*")
        st.markdown("Modeling risks and future loads.")
        
        st.divider()
        
        # Adjust these filenames to match your actual file names
        st.page_link("pages/07_Snow_Drift.py", label="Snow Drift Risk", icon="❄️", help="Road availability modeling")
        st.page_link("pages/08_Forecasting.py", label="Load Forecasting", icon="📈", help="Predict future consumption")

