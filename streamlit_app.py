import streamlit as st
import utils

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Norwegian Energy Atlas",
    page_icon="⚡",
    layout="wide"
)

# ======================================================
# 1. INITIALIZE GLOBAL STATE
# ======================================================
# Defaults to prevent crashes if user skips the map page
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

if "selected_coords" not in st.session_state:
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

# ======================================================
# 2. HEADER
# ======================================================
st.title("⚡ Norwegian Energy & Weather Atlas")

st.markdown("""
### Welcome
This platform analyzes the relationship between **Meteorological Events** and **Energy Dynamics** across Norway.
Use the modules below or the sidebar to navigate.
""")

st.divider()

# ======================================================
# 3. NAVIGATION CARDS
# ======================================================
c1, c2, c3 = st.columns(3)

with c1:
    st.info("**1. Descriptive Analytics**")
    st.markdown("Visualize data trends and history.")
    # Link to the renamed map file
    st.page_link("pages/01_Map_Selector.py", label="Open Map", icon="🗺️")
    st.page_link("pages/02_Energy_Stats.py", label="Energy Data", icon="📊")

with c2:
    st.info("**2. Diagnostic Analysis**")
    st.markdown("Investigate anomalies and correlations.")
    st.page_link("pages/04_Correlations.py", label="Correlations", icon="🔗")
    st.page_link("pages/05_Anomalies.py", label="Anomalies", icon="🚨")

with c3:
    st.info("**3. Predictive Modelling**")
    st.markdown("Forecast future conditions.")
    st.page_link("pages/07_Snow_Drift.py", label="Snow Drift", icon="❄️")
    st.page_link("pages/08_Forecasting.py", label="Forecasting", icon="📈")

st.divider()

# ======================================================
# 4. STATUS BAR
# ======================================================
# Shows the user what is currently selected in the background
cols = st.columns(4)
cols[0].markdown("**Current Context:**")
cols[1].success(f"Region: {st.session_state['selected_price_area']}")
cols[2].success(f"Lat: {st.session_state['selected_coords']['lat']:.2f}")
cols[3].success(f"Lon: {st.session_state['selected_coords']['lon']:.2f}")