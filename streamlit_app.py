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

# Render the sidebar
utils.render_sidebar()

# ======================================================
# CUSTOM CSS & STYLING
# ======================================================
st.markdown("""
<style>
    /* Global Text Styles */
    .big-font { font-size: 1.15rem; color: #374151; line-height: 1.6; }
    .hero-title { font-weight: 800; color: #111827; margin-bottom: 0px; }
    .hero-subtitle { font-size: 1.1rem; color: #6B7280; margin-bottom: 2rem; }
    
    /* New Color Palette Classes (Nordic/Scientific Theme) */
    .theme-exp { color: #0F766E; font-weight: bold; } /* Teal */
    .theme-diag { color: #D97706; font-weight: bold; } /* Amber/Orange */
    .theme-pred { color: #4338CA; font-weight: bold; } /* Indigo */
    
    /* Card Headers */
    .card-header-exp { color: #0F766E; font-size: 1.3rem; font-weight: 700; margin-bottom: 0.5rem; }
    .card-header-diag { color: #D97706; font-size: 1.3rem; font-weight: 700; margin-bottom: 0.5rem; }
    .card-header-pred { color: #4338CA; font-size: 1.3rem; font-weight: 700; margin-bottom: 0.5rem; }
    
    /* Metrics */
    .metric-box { background-color: #F3F4F6; padding: 15px; border-radius: 8px; border-left: 4px solid #9CA3AF; }
</style>
""", unsafe_allow_html=True)

# ======================================================
# HERO SECTION
# ======================================================
st.title("⚡ Norwegian Energy & Weather Atlas")
st.markdown('<p class="hero-subtitle">Advanced Analytics for Meteorological Drivers & Grid Dynamics</p>', unsafe_allow_html=True)

st.markdown("""
<p class="big-font">
    This platform bridges the gap between raw <span class="theme-exp">Observation Data</span> and 
    <span class="theme-pred">Operational Intelligence</span>. 
    By integrating historical grid data with ERA5 weather reanalysis, we provide tools to diagnose 
    past grid behaviors, detect physical anomalies, and forecast future load risks.
</p>
""", unsafe_allow_html=True)

st.divider()

# ======================================================
# DATA ECOSYSTEM (Based on your utils.py)
# ======================================================
st.subheader("📚 Data Ecosystem & Methodology")

with st.container(border=True):
    d1, d2, d3 = st.columns(3)
    
    with d1:
        st.markdown("#### ⚡ Energy Grid")
        st.markdown("**Source:** Elhub & Nord Pool")
        st.info("""
        **Dimensions:**
        * **Granularity:** Hourly resolution.
        * **Scope:** Consumption & Production.
        * **Segments:** 5 Price Areas (NO1-NO5).
        * **Format:** Time-series aggregations.
        """)
    
    with d2:
        st.markdown("#### ☁️ Meteorology")
        st.markdown("**Source:** Open-Meteo (ERA5)")
        st.warning("""
        **Dimensions:**
        * **Variables:** Temp, Wind (10m/Gusts), Precip.
        * **Derived:** Snow Water Equivalent (SWE).
        * **Analysis:** 5-Day Lag & Rolling Windows.
        * **Physics:** Tabler (2003) Drift Model.
        """)
        
    with d3:
        st.markdown("#### 🗺️ Geospatial")
        st.markdown("**Source:** Kartverket & GeoNorge")
        st.success("""
        **Dimensions:**
        * **Boundaries:** Detailed Municipal GeoJSON.
        * **Interaction:** Point-and-click selection.
        * **Elevation:** Dynamic lookups via Mapbox/API.
        * **Mapping:** Plotly Mapbox Integration.
        """)

st.markdown("### 🧭 Analytic Modules")

# ======================================================
# NAVIGATION CARDS (Matched to your actual code features)
# ======================================================
col_exp, col_diag, col_pred = st.columns(3, gap="medium")

# --- 1. EXPLORATIVE (TEAL) ---
with col_exp:
    with st.container(border=True):
        st.markdown('<p class="card-header-exp">🟦 Explorative</p>', unsafe_allow_html=True)
        st.markdown("*\"What is the baseline?\"*")
        st.markdown("Visualize spatial distribution and historical baselines.")
        
        st.divider()
        
        st.page_link("pages/01_Map_Selector.py", label="Map Selector", icon="🗺️", help="Interactive Mapbox interface for region selection")
        st.page_link("pages/02_Energy_Stats.py", label="Energy Statistics", icon="⚡", help="Seasonal trends and production mix (Pie/Line)")
        st.page_link("pages/03_Weather_Stats.py", label="Weather Statistics", icon="🌤️", help="ERA5 data overview and normalization")

# --- 2. DIAGNOSTIC (AMBER/ORANGE) ---
with col_diag:
    with st.container(border=True):
        st.markdown('<p class="card-header-diag">🟧 Diagnostic</p>', unsafe_allow_html=True)
        st.markdown("*\"Why did it happen?\"*")
        st.markdown("Advanced signal processing to find relationships and outliers.")
        
        st.divider()
        
        st.page_link("pages/04_Correlations.py", label="Correlation Analysis", icon="🔗", help="Sliding window correlations with lag")
        st.page_link("pages/05_Anomalies.py", label="Anomaly Detection", icon="⚠️", help="DCT (Temperature) and LOF (Precipitation)")
        st.page_link("pages/06_Signal_Processing.py", label="Signal Processing", icon="📡", help="STL Decomposition & Frequency Spectrograms")

# --- 3. PREDICTIVE (INDIGO/PURPLE) ---
with col_pred:
    with st.container(border=True):
        st.markdown('<p class="card-header-pred">🟪 Predictive</p>', unsafe_allow_html=True)
        st.markdown("*\"What comes next?\"*")
        st.markdown("Physics-based risk modeling and time-series forecasting.")
        
        st.divider()
        
        st.page_link("pages/07_Snow_Drift.py", label="Snow Drift Risk", icon="❄️", help="Tabler (2003) Physics Model & Fence Sizing")
        st.page_link("pages/08_Forecasting.py", label="Load Forecasting", icon="📈", help="SARIMAX with Exogenous Weather variables")