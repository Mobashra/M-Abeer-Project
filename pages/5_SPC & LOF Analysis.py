import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
import analysis_functions as af


st.set_page_config(page_title="Weather Anomalies", layout="wide")
st.title("⚡ Anomalies: SPC & LOF")


# --- 1. GLOBAL SETTINGS ---
if "selected_price_area" not in st.session_state:
   st.session_state["selected_price_area"] = "NO1"
   default = utils.CITIES["NO1"]
   st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}


current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]


st.info(f"**Analysis Scope:** {current_area} ({coords['lat']:.2f}, {coords['lon']:.2f})")


# --- 2. FETCH DATA (2021 Default) ---
# The assignment implies analyzing "a whole year". We default to 2021 but allow selection.
selected_year = st.sidebar.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)


with st.spinner(f"Fetching {selected_year} weather data..."):
   # Fetch just the selected year for focused anomaly detection
   df = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{selected_year}-01-01", f"{selected_year}-12-31")


if df.empty:
   st.error("No weather data available.")
   st.stop()


# --- 3. TABS ---
tab1, tab2 = st.tabs(["Temperature SPC", "Precipitation LOF"])


# ==================================================
# TAB 1: TEMPERATURE SPC (REQUIREMENT 1)
# ==================================================
with tab1:
   st.markdown("### Statistical Process Control (SPC)")
   st.caption("Detects outliers based on Seasonally Adjusted Temperature Variations (SATV).")
  
   # --- PARAMETERS (Required by Assignment) ---
   with st.expander("⚙️ SPC Parameters", expanded=True):
       c1, c2 = st.columns(2)
       with c1:
           # Frequency Cutoff for DCT
           cutoff = st.slider(
               "DCT Frequency Cutoff",
               min_value=100, max_value=2000, value=1500,
               help="Higher values include faster changes (like daily cycles) in the Trend."
           )
       with c2:
           # Number of Standard Deviations (n_std)
           n_std = st.slider(
               "Standard Deviations (σ)",
               min_value=1.0, max_value=5.0, value=3.0, step=0.1,
               help="Width of the boundary. Typically 3.0."
           )


   # --- CALCULATION ---
   try:
       t, temp, upper, lower, outliers = af.detect_temperature_anomalies_spc(
           df, freq_cutoff=cutoff, n_std=n_std
       )
      
       # --- PLOT ---
       fig = go.Figure()
      
       # 1. Raw Temperature
       fig.add_trace(go.Scatter(
           x=t, y=temp, mode='lines', name="Temperature",
           line=dict(color='#1f77b4', width=1)
       ))
      
       # 2. SPC Boundaries (Inliers vs Outliers boundary)
       fig.add_trace(go.Scatter(x=t, y=upper, name="UCL", line=dict(dash='dash', color='orange', width=1)))
       fig.add_trace(go.Scatter(x=t, y=lower, name="LCL", line=dict(dash='dash', color='orange', width=1)))
      
       # 3. Outliers (Contrasting Color)
       if outliers.sum() > 0:
           fig.add_trace(go.Scatter(
               x=t[outliers], y=temp[outliers],
               mode='markers', name="Outliers",
               marker=dict(color='red', size=6, symbol='x')
           ))


       fig.update_layout(
           title=f"Temperature Anomalies ({selected_year})",
           xaxis_title="Time", yaxis_title="Temperature (°C)",
           template="plotly_white", height=500
       )
       st.plotly_chart(fig, use_container_width=True)
      
       # --- SUMMARY ---
       st.metric("Total Outliers Detected", f"{outliers.sum()} hours")


   except Exception as e:
       st.error(f"SPC Analysis Failed: {e}")


# ==================================================
# TAB 2: PRECIPITATION LOF (REQUIREMENT 2)
# ==================================================
with tab2:
   st.markdown("### Local Outlier Factor (LOF)")
   st.caption("Detects anomalies in precipitation density.")
  
   # --- PARAMETERS (Required by Assignment) ---
   with st.expander("⚙️ LOF Parameters", expanded=True):
       # Proportion of outliers (Default 1%)
       contamination_pct = st.slider(
           "Outlier Proportion (%)",
           min_value=0.1, max_value=10.0, value=1.0, step=0.1,
           help="The percentage of the dataset to be considered anomalous."
       )
       contamination = contamination_pct / 100.0


   # --- CALCULATION ---
   try:
       t, precip, outliers = af.detect_precipitation_anomalies_lof(
           df, contamination=contamination
       )
      
       # --- PLOT ---
       fig = go.Figure()
      
       # 1. Precipitation
       fig.add_trace(go.Scatter(
           x=t, y=precip, mode='lines', name="Precipitation",
           line=dict(color='#2ca02c', width=1)
       ))
      
       # 2. Anomalies
       if outliers.sum() > 0:
           fig.add_trace(go.Scatter(
               x=t[outliers], y=precip[outliers],
               mode='markers', name="Anomaly",
               marker=dict(color='red', size=6, symbol='circle-open', line=dict(width=2))
           ))


       fig.update_layout(
           title=f"Precipitation Anomalies (LOF {contamination_pct}%)",
           xaxis_title="Time", yaxis_title="Precipitation (mm)",
           template="plotly_white", height=500
       )
       st.plotly_chart(fig, use_container_width=True)
      
       # --- SUMMARY ---
       st.metric("Anomalous Events", f"{outliers.sum()} hours")
      
   except Exception as e:
       st.error(f"LOF Analysis Failed: {e}")
