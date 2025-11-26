import streamlit as st
import plotly.graph_objects as go
import utils
import analysis_functions as af

st.title("Anomalies: SPC & LOF")
area = st.session_state.get("selected_price_area", "NO1")
city = utils.CITIES[area]

df = utils.fetch_weather_api(city["lat"], city["lon"], "2021-01-01", "2021-12-31")

tab1, tab2 = st.tabs(["Temperature SPC", "Precipitation LOF"])

with tab1:
    st.markdown("SPC with **Corrected Physics** (Daily cycle included in Trend).")
    cutoff = st.slider("DCT Cutoff", 100, 2000, 1500) # Default 1500 fixes the issue
    t, temp, upper, lower, outliers = af.detect_temperature_anomalies_spc(df, freq_cutoff=cutoff)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=temp, name="Temp"))
    fig.add_trace(go.Scatter(x=t, y=upper, name="UCL", line=dict(dash='dash', color='orange')))
    fig.add_trace(go.Scatter(x=t, y=lower, name="LCL", line=dict(dash='dash', color='orange')))
    fig.add_trace(go.Scatter(x=t[outliers], y=temp[outliers], mode='markers', name="Outlier", marker=dict(color='red')))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    t, precip, outliers = af.detect_precipitation_anomalies_lof(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=precip, name="Precip"))
    fig.add_trace(go.Scatter(x=t[outliers], y=precip[outliers], mode='markers', name="Anomaly", marker=dict(color='red')))
    st.plotly_chart(fig, use_container_width=True)