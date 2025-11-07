# page_new_B_weather_analysis.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
from sklearn.neighbors import LocalOutlierFactor
from datetime import datetime
import plotly.graph_objects as go
from scipy.fft import dct, idct

#Page setup
st.set_page_config(page_title="Weather Analysis (SPC & LOF)", layout="wide")
st.title("Outliers/SPC & Anomalies/LOF (ERA5 2021)")

# Mapping price areas to cities 
cities = {"NO1": {"city": "Oslo", "latitude": 59.9139, "longitude": 10.7522},
        "NO2": {"city": "Kristiansand", "latitude": 58.1467, "longitude": 7.9956},
        "NO3": {"city": "Trondheim", "latitude": 63.4305, "longitude": 10.3951},
        "NO4": {"city": "Tromsø", "latitude": 69.6492, "longitude": 18.9553},
        "NO5": {"city": "Bergen", "latitude": 60.3942, "longitude": 5.3221},}

# Check selected price area
if "selected_price_area" not in st.session_state:
    # If the user has not selected a price area previously, show warning and stop
    st.warning("Please select a price area on the 'Elhub API Data' page first.")
    st.stop()

# Retrieve the selected price area from the session state
selected_area = st.session_state["selected_price_area"]
city_info = cities[selected_area]
st.subheader(f"Selected Price Area: {selected_area}")


# Weather variables to fetch 
variables = ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]

# Fetch ERA5 weather data (cached)
@st.cache_data(ttl=600)
def fetch_weather_data(lat: float, lon: float, year: int = 2021, timezone: str = "Europe/Oslo") -> pd.DataFrame:
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    hourly_vars = ",".join(variables)
    url = (
        f"https://archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&hourly={hourly_vars}&timezone={timezone}"
    )
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        js = resp.json()
        if "hourly" not in js or "time" not in js["hourly"]:
            return pd.DataFrame()
        hourly = js["hourly"]
        df = pd.DataFrame({"time": pd.to_datetime(hourly["time"])})
        for v in variables:
            df[v] = hourly.get(v)
        return df.sort_values("time").reset_index(drop=True)
    except Exception as e:
        st.error(f"Failed to fetch weather data: {e}")
        return pd.DataFrame()

#Load data
df = fetch_weather_data(city_info["latitude"], city_info["longitude"], year=2021)

if df.empty:
    st.warning("No weather data found for this price area.")
    st.stop()

# Tabs for SPC and LOF
tab_spc, tab_lof = st.tabs(["SPC / Outliers", "LOF / Anomalies"])

# SPC Analysis tab 
with tab_spc:
    st.subheader("Statistical Process Control (SPC) Analysis")
    st.markdown("Detect outliers in weather variables using high-pass filtered seasonal adjustment and mean±3*std control limits.")

    # User selects variable
    selected_var = st.selectbox("Select weather variable for SPC:", variables, index=0)

    # Prepare time series
    ts = df[["time", selected_var]].dropna().set_index("time")
    ts = ts.asfreq("h").interpolate(method="time")

    # High-pass filtering via DCT to remove seasonal trends
    cutoff = st.slider("DCT frequency cutoff (0 = keep all low freq):", 0, 2000, 1000)
    ts_values = ts[selected_var].values
    ts_dct = dct(ts_values, norm="ortho")
    ts_dct[:cutoff] = 0  # Remove low frequencies (seasonal)
    ts_hp = idct(ts_dct, norm="ortho")  # High-pass filtered

    # SPC limits
    mean_val = np.mean(ts_hp)
    std_val = np.std(ts_hp)
    ucl = mean_val + 3 * std_val
    lcl = mean_val - 3 * std_val
    outliers_idx = np.where((ts_hp > ucl) | (ts_hp < lcl))[0]

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ts.index, y=ts[selected_var], mode="lines", name=selected_var))
    fig.add_trace(go.Scatter(x=ts.index, y=[ucl]*len(ts), mode="lines", name="UCL", line=dict(color="red", dash="dash")))
    fig.add_trace(go.Scatter(x=ts.index, y=[lcl]*len(ts), mode="lines", name="LCL", line=dict(color="red", dash="dash")))
    if len(outliers_idx) > 0:
        fig.add_trace(go.Scatter(x=ts.index[outliers_idx], y=ts[selected_var].iloc[outliers_idx],mode="markers", name="Outliers", marker=dict(color="orange", size=6)))

    fig.update_layout(title=f"SPC Analysis: {selected_var} ({selected_area})",xaxis_title="Time", yaxis_title=selected_var,template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"Detected outliers: {len(outliers_idx)}")

# LOF Analysis tab 
with tab_lof:
    st.subheader("Local Outlier Factor (LOF) Anomaly Detection")
    st.markdown("Detect anomalous points in weather variables using LOF (Isolation compared to neighbors).")

    # User selects variable
    selected_var_lof = st.selectbox("Select weather variable for LOF:", variables, index=0, key="lof_var")
    ts_lof = df[["time", selected_var_lof]].dropna().set_index("time")
    ts_lof = ts_lof.asfreq("h").interpolate(method="time")

    if len(ts_lof) < 20:
        st.warning("Not enough data points for LOF analysis.")
    else:
        # Fit LOF
        lof = LocalOutlierFactor(n_neighbors=20, contamination=0.01)
        ts_lof["lof_outlier"] = lof.fit_predict(ts_lof[[selected_var_lof]])
        ts_lof["anomaly_score"] = -lof.negative_outlier_factor_
        anomalies = ts_lof[ts_lof["lof_outlier"] == -1]

        # Plot
        fig_lof = go.Figure()
        fig_lof.add_trace(go.Scatter(x=ts_lof.index, y=ts_lof[selected_var_lof], mode="lines", name=selected_var_lof))
        if not anomalies.empty:
            fig_lof.add_trace(go.Scatter(x=anomalies.index, y=anomalies[selected_var_lof],mode="markers", name="Anomalies", marker=dict(color="red", size=6)))

        fig_lof.update_layout(title=f"LOF Anomaly Detection: {selected_var_lof} ({selected_area})",xaxis_title="Time", yaxis_title=selected_var_lof,template="plotly_white")
        st.plotly_chart(fig_lof, use_container_width=True)
        st.markdown(f"Detected anomalies: {len(anomalies)}")

#Data source expander
with st.expander("Data Sources"):
    st.markdown("""
    1. **Open-Meteo ERA5 Weather Reanalysis 2021**
       - Source: [Open-Meteo API](https://open-meteo.com/en/docs)
       - Variables: temperature_2m, precipitation, wind_speed_10m, wind_gusts_10m, wind_direction_10m
       - Hourly data for the selected Norwegian city.
    """)
