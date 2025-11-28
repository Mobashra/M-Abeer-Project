import streamlit as st
import plotly.graph_objects as go
import utils
import analysis_functions as af

st.set_page_config(page_title="Anomalies", layout="wide")

utils.check_session_state()
utils.render_sidebar()

st.title("🚨 Anomaly Detection")

# 1. CONTROLS
c1, c2 = st.columns([1, 3])
with c1: year = st.selectbox("Analysis Year", [2021, 2022, 2023, 2024])
with c2: st.info("Detects extreme events using Statistical Process Control (SPC) and LOF.")

# 2. LOAD
coords = st.session_state["selected_coords"]
with st.spinner("Analyzing..."):
    df = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{year}-01-01", f"{year}-12-31")

if df.empty: st.stop()

# 3. TABS
tab1, tab2 = st.tabs(["🌡️ Temperature (SPC)", "🌧️ Precipitation (LOF)"])

with tab1:
    std_dev = st.slider("Sigma Threshold", 1.0, 5.0, 3.0)
    t, temp, upper, lower, outliers = af.detect_temperature_anomalies_spc(df, n_std=std_dev)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=temp, name="Temp", line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=t, y=upper, name="UCL", line=dict(dash='dash', color='red')))
    fig.add_trace(go.Scatter(x=t, y=lower, name="LCL", line=dict(dash='dash', color='red')))
    if outliers.any():
        fig.add_trace(go.Scatter(x=t[outliers], y=temp[outliers], mode='markers', name="Outlier", marker=dict(color='black', size=6, symbol='x')))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    contam = st.slider("Contamination %", 0.1, 5.0, 1.0) / 100.0
    t, precip, outliers = af.detect_precipitation_anomalies_lof(df, contamination=contam)
    
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=t, y=precip, name="Precipitation", line=dict(color='green')))
    if outliers.any():
        fig2.add_trace(go.Scatter(x=t[outliers], y=precip[outliers], mode='markers', name="Anomaly", marker=dict(color='red', size=8, symbol='circle-open')))
    st.plotly_chart(fig2, use_container_width=True)