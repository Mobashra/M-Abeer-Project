import streamlit as st
import plotly.graph_objects as go
import utils
import analysis_functions as af

st.set_page_config(page_title="Anomaly Detection", page_icon="🚨", layout="wide")
st.title("🚨 Anomaly Detection (SPC & LOF)")

if "selected_coords" not in st.session_state:
    st.error("Select a location on the Home Map.")
    st.stop()

coords = st.session_state["selected_coords"]
year = st.sidebar.selectbox("Year", [2021, 2022, 2023], index=0)

# Fetch Weather Data
df = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{year}-01-01", f"{year}-12-31")
if df.empty: st.stop()

tab_spc, tab_lof = st.tabs(["Temperature (SPC)", "Precipitation (LOF)"])

with tab_spc:
    st.info("Statistical Process Control using DCT filtering.")
    cutoff = st.slider("DCT Cutoff", 500, 2000, 1500)
    n_std = st.slider("Sigma (Standard Deviations)", 2.0, 5.0, 3.0)
    
    t, temp, upper, lower, outliers = af.detect_temperature_anomalies_spc(df, freq_cutoff=cutoff, n_std=n_std)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=temp, name="Temp"))
    fig.add_trace(go.Scatter(x=t, y=upper, name="UCL", line=dict(dash='dash', color='red')))
    fig.add_trace(go.Scatter(x=t, y=lower, name="LCL", line=dict(dash='dash', color='red')))
    # Add outliers
    if outliers.any():
        fig.add_trace(go.Scatter(x=t[outliers], y=temp[outliers], mode='markers', name="Outlier", marker=dict(color='black', size=8, symbol='x')))
        
    st.plotly_chart(fig, use_container_width=True)

with tab_lof:
    st.info("Local Outlier Factor (Unsupervised Learning).")
    contam = st.slider("Contamination %", 0.1, 5.0, 1.0) / 100.0
    
    t, precip, outliers = af.detect_precipitation_anomalies_lof(df, contamination=contam)
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=t, y=precip, name="Precipitation"))
    if outliers.any():
        fig2.add_trace(go.Scatter(x=t[outliers], y=precip[outliers], mode='markers', name="Anomaly", marker=dict(color='red', size=8, symbol='circle-open')))
    
    st.plotly_chart(fig2, use_container_width=True)