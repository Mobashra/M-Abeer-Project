import streamlit as st
import utils

st.set_page_config(page_title="Energy Atlas", page_icon="⚡", layout="wide")

# Initialize Defaults (Silent)
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

utils.render_sidebar()

# --- HEADER ---
st.title("⚡ Norwegian Energy & Weather Atlas")
st.markdown("### Interactive Data Science Platform")
st.markdown("""
Welcome. This platform aggregates **Energy Data** (Elhub) and **Meteorological Data** (ERA5) 
to perform advanced analysis on the Norwegian power grid.
""")

st.divider()

# --- DASHBOARD NAVIGATION ---
st.subheader("🚀 Select Module")

# 3 Columns for the 3 Phases
col_expl, col_diag, col_pred = st.columns(3)

# --- 1. EXPLORATIVE (Blue) ---
with col_expl:
    with st.container(border=True):
        st.markdown("#### 🟦 Explorative")
        st.caption("Visualizing history & trends")
        
        st.page_link("pages/01_Map_Selector.py", label="📍 Map Selector", icon="🗺️", help="Start Here")
        st.page_link("pages/02_Energy_Stats.py", label="Energy Statistics", icon="📊")
        st.page_link("pages/03_Weather_Stats.py", label="Weather History", icon="🌤️")

# --- 2. DIAGNOSTICS (Orange) ---
with col_diag:
    with st.container(border=True):
        st.markdown("#### 🟧 Diagnostics")
        st.caption("Understanding relationships")
        
        st.page_link("pages/04_Correlations.py", label="Correlations", icon="🔗")
        st.page_link("pages/05_Anomalies.py", label="Anomaly Detection", icon="🚨")
        st.page_link("pages/06_Signal_Processing.py", label="Signal Processing", icon="📡")

# --- 3. PREDICTIVE (Purple) ---
with col_pred:
    with st.container(border=True):
        st.markdown("#### 🟪 Predictive")
        st.caption("Forecasting the future")
        
        st.page_link("pages/07_Snow_Drift.py", label="Snow Drift Model", icon="❄️")
        st.page_link("pages/08_Forecasting.py", label="SARIMAX Forecast", icon="📈")

st.divider()

# --- STATUS FOOTER ---
c1, c2, c3 = st.columns(3)
c1.info(f"**Region:** {st.session_state['selected_price_area']}")
coords = st.session_state['selected_coords']
c2.info(f"**Lat:** {coords['lat']:.2f}")
c3.info(f"**Lon:** {coords['lon']:.2f}")