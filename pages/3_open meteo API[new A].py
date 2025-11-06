# page_new_A_weather_analysis.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from statsmodels.tsa.seasonal import STL
from scipy.signal import spectrogram

st.set_page_config(page_title="Weather Analysis (STL & Spectrogram)", layout="wide")
st.title("🌦️ Weather Analysis: STL Decomposition & Spectrogram")

# --- Mapping for price areas to coordinates ---
CITIES = [
    {"price_area": "NO1", "city": "Oslo",          "latitude": 59.9139, "longitude": 10.7522},
    {"price_area": "NO2", "city": "Kristiansand",  "latitude": 58.1467, "longitude": 7.9956},
    {"price_area": "NO3", "city": "Trondheim",     "latitude": 63.4305, "longitude": 10.3951},
    {"price_area": "NO4", "city": "Tromsø",        "latitude": 69.6492, "longitude": 18.9553},
    {"price_area": "NO5", "city": "Bergen",        "latitude": 60.3942, "longitude": 5.3221},
]
df_cities = pd.DataFrame(CITIES)

# --- Get selected area from session state ---
if "selected_price_area" not in st.session_state:
    st.warning("⚠️ Please select a price area in the 'Elhub API Data' page first.")
    st.stop()

selected_area = st.session_state["selected_price_area"]
city_info = df_cities[df_cities["price_area"] == selected_area].iloc[0]
st.subheader(f"Selected Area: {city_info.city} ({selected_area})")

# --- Fetch Open-Meteo ERA5 data ---
@st.cache_data(show_spinner=False)
def fetch_weather_data(latitude, longitude, year=2021, timezone="UTC"):
    variables = [
        "temperature_2m",
        "precipitation",
        "wind_speed_10m",
        "wind_gusts_10m",
        "wind_direction_10m",
    ]
    base_url = "https://archive-api.open-meteo.com/v1/era5"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(variables),
        "timezone": timezone,
    }
    response = requests.get(base_url, params=params, timeout=60)
    response.raise_for_status()
    js = response.json()
    hourly = js["hourly"]
    df = pd.DataFrame({"time": pd.to_datetime(hourly["time"])})
    for v in variables:
        df[v] = hourly.get(v)
    df = df.sort_values("time").reset_index(drop=True)
    return df

with st.spinner("Fetching weather data from Open-Meteo..."):
    df_weather = fetch_weather_data(city_info.latitude, city_info.longitude)

st.success(f"✅ Data loaded for {city_info.city}, {selected_area} (2021)")
st.caption(f"Data source: [Open-Meteo ERA5 Reanalysis](https://open-meteo.com/)")

variables = [
    "temperature_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
]

# --- Tabs for STL and Spectrogram ---
tab1, tab2 = st.tabs(["📈 STL Decomposition", "🎵 Spectrogram"])

# --- Tab 1: STL decomposition ---
with tab1:
    st.subheader("Seasonal-Trend Decomposition using STL")
    variable = st.selectbox("Select variable:", variables, index=0)

    df_plot = df_weather.set_index("time")[variable].dropna()
    if df_plot.empty:
        st.warning("No data available for this variable.")
        st.stop()

    # STL decomposition (period=24 for daily pattern)
    st.info("STL decomposition with daily periodicity (period = 24).")
    stl = STL(df_plot, period=24).fit()

    # Build Plotly figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot, name="Original", line=dict(width=1)))
    fig.add_trace(go.Scatter(x=df_plot.index, y=stl.trend, name="Trend", line=dict(width=2)))
    fig.add_trace(go.Scatter(x=df_plot.index, y=stl.seasonal, name="Seasonal", line=dict(width=1, dash="dot")))
    fig.add_trace(go.Scatter(x=df_plot.index, y=stl.resid, name="Residual", line=dict(width=1, dash="dash")))
    fig.update_layout(
        title=f"STL Decomposition for {variable} in {city_info.city} (2021)",
        xaxis_title="Time",
        yaxis_title="Value",
        template="plotly_white",
        legend=dict(x=0, y=1, bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Tab 2: Spectrogram ---
with tab2:
    st.subheader("Spectrogram Analysis")
    variable = st.selectbox("Select variable for spectrogram:", variables, index=0, key="spectrogram_var")

    df_spec = df_weather.set_index("time")[variable].dropna()
    if df_spec.empty:
        st.warning("No data available for this variable.")
        st.stop()

    # Compute spectrogram
    fs = 1  # 1 sample/hour
    f, t, Sxx = spectrogram(df_spec.values, fs=fs, nperseg=168, noverlap=84)  # 1-week window
    Sxx_dB = 10 * np.log10(Sxx + 1e-9)

    # Plotly heatmap
    fig_spec = go.Figure(
        data=go.Heatmap(
            z=Sxx_dB,
            x=t,
            y=f,
            colorscale="Viridis",
            colorbar=dict(title="Power (dB)"),
        )
    )
    fig_spec.update_layout(
        title=f"Spectrogram of {variable} in {city_info.city} (2021)",
        xaxis_title="Time (hours since start)",
        yaxis_title="Frequency (1/hour)",
        template="plotly_white",
    )
    st.plotly_chart(fig_spec, use_container_width=True)
