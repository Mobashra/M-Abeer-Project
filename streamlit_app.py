import streamlit as st
import utils

# ======================================================
# PAGE CONFIGURATION
# ======================================================
st.set_page_config(
    page_title="Energy Atlas",
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
    /* --- HERO SECTION TEXT --- */
    /* Removed fixed colors so they adapt to Dark/Light mode automatically */
    .hero-title { font-weight: 800; margin-bottom: 0px; }
    
    /* Slight transparency for subtitle instead of gray color */
    .hero-subtitle { font-size: 1.1rem; opacity: 0.7; margin-bottom: 2rem; }
    
    .big-font { font-size: 1.15rem; line-height: 1.6; }

    /* --- HIGHLIGHT COLORS (Brighter for Dark Mode) --- */
    .highlight-teal { color: #2DD4BF; font-weight: 800; }   /* Bright Teal */
    .highlight-indigo { color: #818CF8; font-weight: 800; } /* Bright Indigo */

    /* --- THEME HEADERS --- */
    .theme-exp { color: #2DD4BF; font-weight: 800; font-size: 1.4rem; margin-bottom: 0px; }
    .sub-exp { color: #14B8A6; font-weight: 600; font-size: 1.0rem; font-style: italic; margin-bottom: 1rem; }
    
    .theme-diag { color: #FB923C; font-weight: 800; font-size: 1.4rem; margin-bottom: 0px; }
    .sub-diag { color: #EA580C; font-weight: 600; font-size: 1.0rem; font-style: italic; margin-bottom: 1rem; }
    
    .theme-pred { color: #818CF8; font-weight: 800; font-size: 1.4rem; margin-bottom: 0px; }
    .sub-pred { color: #4F46E5; font-weight: 600; font-size: 1.0rem; font-style: italic; margin-bottom: 1rem; }

    /* --- CARD LINKS (Opaque Backgrounds) --- */
    [data-testid="stPageLink-NavLink"] {
        background-color: #1F2937;  /* Dark Grey Background for Dark Mode Cards */
        border: 1px solid #374151;  /* Subtle Dark Border */
        border-radius: 8px;
        padding: 0.75rem 1rem;
        transition: all 0.2s ease-in-out;
        margin-bottom: 8px;
    }

    [data-testid="stPageLink-NavLink"]:hover {
        background-color: #374151;  /* Lighter Grey on Hover */
        border-color: #6B7280;
        transform: translateY(-2px);
    }
    
    /* Force text inside cards to be light/white */
    [data-testid="stPageLink-NavLink"] p {
        font-weight: 500;
        font-size: 1rem;
        color: #E5E7EB !important;
    }
</style>
""", unsafe_allow_html=True)

# ======================================================
# HERO SECTION
# ======================================================
st.title("Norwegian Energy & Weather Atlas")
st.markdown('<p class="hero-subtitle">Advanced Analytics for Meteorological Drivers & Grid Dynamics</p>', unsafe_allow_html=True)

# UPDATED: Added specific span classes for the colors you wanted to keep
st.markdown("""
<p class="big-font">
    This platform bridges the gap between raw <span class="highlight-teal">Observation Data</span> and 
    <span class="highlight-indigo">Operational Intelligence</span>. 
    By integrating historical grid data with ERA5 weather reanalysis, we provide tools to diagnose 
    past grid behaviors, detect physical anomalies, and forecast future load risks.
</p>
""", unsafe_allow_html=True)

st.divider()

# ======================================================
# DATA ECOSYSTEM
# ======================================================
st.subheader("Data Ecosystem & Methodology")

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
        """)
    
    with d2:
        st.markdown("#### ☁️ Meteorology")
        st.markdown("**Source:** Open-Meteo (ERA5)")
        st.warning("""
        **Dimensions:**
        * **Variables:** Temp, Wind, Precip.
        * **Derived:** Snow Water Equivalent (SWE).
        * **Analysis:** 5-Day Lag & Rolling Windows.
        """)
        
    with d3:
        st.markdown("#### 🗺️ Geospatial")
        st.markdown("**Source:** Kartverket & GeoNorge")
        st.success("""
        **Dimensions:**
        * **Boundaries:** Municipal GeoJSON.
        * **Interaction:** Point-and-click selection.
        * **Elevation:** Dynamic lookups via Mapbox/API.
        """)

st.markdown("### 🧭 Analytic Modules")

# ======================================================
# NAVIGATION CARDS
# ======================================================
col_exp, col_diag, col_pred = st.columns(3, gap="large")

# --- 1. EXPLORATIVE (TEAL) ---
with col_exp:
    with st.container():
        st.markdown('<p class="theme-exp">Explorative</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-exp">"What is the baseline?"</p>', unsafe_allow_html=True)
        st.markdown("Visualize spatial distribution and historical baselines.")
        st.write("") 
        
        st.page_link("pages/01_Map_Selector.py", label="Map Selector", icon="🗺️", help="Interactive Mapbox interface")
        st.page_link("pages/02_Energy_Stats.py", label="Energy Statistics", icon="⚡", help="Seasonal trends & mix")
        st.page_link("pages/03_Weather_Stats.py", label="Weather Statistics", icon="🌤️", help="ERA5 data overview")

# --- 2. DIAGNOSTIC (AMBER/ORANGE) ---
with col_diag:
    with st.container():
        st.markdown('<p class="theme-diag">Diagnostic</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-diag">"Why did it happen?"</p>', unsafe_allow_html=True)
        st.markdown("Advanced signal processing to find relationships and outliers.")
        st.write("") 
        
        st.page_link("pages/04_Correlations.py", label="Correlation Analysis", icon="🔗", help="Sliding window analysis")
        st.page_link("pages/05_Anomalies.py", label="Anomaly Detection", icon="⚠️", help="DCT & LOF methods")
        st.page_link("pages/06_Signal_Processing.py", label="Signal Processing", icon="📡", help="STL & Spectrograms")

# --- 3. PREDICTIVE (INDIGO) ---
with col_pred:
    with st.container():
        st.markdown('<p class="theme-pred">Predictive</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-pred">"What comes next?"</p>', unsafe_allow_html=True)
        st.markdown("Physics-based risk modeling and time-series forecasting.")
        st.write("") 
        
        st.page_link("pages/07_Snow_Drift.py", label="Snow Drift Risk", icon="❄️", help="Tabler (2003) Physics")
        st.page_link("pages/08_Forecasting.py", label="Load Forecasting", icon="📈", help="SARIMAX + Exogenous")