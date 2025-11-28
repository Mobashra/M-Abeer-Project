import streamlit as st
import utils




# --- SIDEBAR NAVIGATION GROUPS ---
st.sidebar.markdown("### 🗺️ Exploration")
# The pages 01, 02, 03 will appear here naturally due to sorting

if st.sidebar.checkbox("Show Advanced Modules", value=True):
    st.sidebar.markdown("### 🔍 Diagnostics")
    # Pages 04, 05, 06 fall here visually
    
    st.sidebar.markdown("### 🔮 Prediction")
    # Pages 07, 08 fall here visually

    
# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Norwegian Energy Atlas",
    page_icon="⚡",
    layout="wide"
)

# ======================================================
# 1. INITIALIZE GLOBAL STATE (Crucial for App Stability)
# ======================================================
# We set defaults here so other pages don't crash if visited first.
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

if "selected_coords" not in st.session_state:
    # Default to Oslo
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

# ======================================================
# 2. HEADER & INTRO
# ======================================================
st.title("⚡ Norwegian Energy & Weather Atlas")

st.markdown("""
### Welcome to the Energy Analytics Platform
This application provides a comprehensive suite of tools to analyze the relationship between 
**Meteorological Events** and **Energy Dynamics** across Norway's price areas.
""")

st.divider()

# ======================================================
# 3. NAVIGATION HUB (Cards)
# ======================================================
st.subheader("🚀 Start Analysis")

# We create 3 columns for the 3 main "Groups" of analysis
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("### 🗺️ Exploration")
    st.info("**Descriptive Analytics**")
    st.markdown("""
    Visualize historical data and trends.
    * **Map Selector:** Choose regions & coordinates.
    * **Energy Stats:** Production/Consumption trends.
    * **Weather Stats:** Historical ERA5 data.
    """)
    # Direct Link to the Map Page
    st.page_link("pages/01_🗺️_Map_Selector.py", label="Go to Map", icon="🗺️")

with c2:
    st.markdown("### 🔍 Diagnostics")
    st.info("**Why did it happen?**")
    st.markdown("""
    Deep dive into anomalies and patterns.
    * **Correlations:** Weather vs. Energy impact.
    * **Anomalies:** Detect outliers (SPC/LOF).
    * **Signals:** Frequency analysis (STL).
    """)
    st.page_link("pages/04_🔗_Correlations.py", label="Analyze Correlations", icon="🔗")

with c3:
    st.markdown("### 🔮 Prediction")
    st.info("**What will happen?**")
    st.markdown("""
    Forecast future events.
    * **Snow Drift:** Physics-based accumulation.
    * **Forecasting:** SARIMAX Energy prediction.
    """)
    st.page_link("pages/08_📈_Forecasting.py", label="Go to Forecasting", icon="📈")

st.divider()

# ======================================================
# 4. CURRENT STATUS
# ======================================================
st.caption("Global Context Status")
col_stat1, col_stat2 = st.columns(2)

with col_stat1:
    st.success(f"**Active Region:** {st.session_state['selected_price_area']}")

with col_stat2:
    lat = st.session_state['selected_coords']['lat']
    lon = st.session_state['selected_coords']['lon']
    st.success(f"**Active Coordinates:** {lat:.2f}, {lon:.2f}")

st.warning("👈 **Tip:** Use the sidebar to navigate between specific modules.")