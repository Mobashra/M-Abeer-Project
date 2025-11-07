# page_new_B_weather_analysis.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
from sklearn.neighbors import LocalOutlierFactor
from scipy.fftpack import dct, idct
import plotly.graph_objects as go

# ------------------- PAGE CONFIG -------------------
st.set_page_config(page_title="Weather Outlier & Anomaly Analysis", layout="wide")
st.title("Weather Analysis: Outliers (SPC) & Anomalies (LOF)")

# ------------------- CITY AND COORDINATES -------------------
city_coords = {
    "Oslo": (59.9139, 10.7522),
    "Bergen": (60.39299, 5.32415),
    "Trondheim": (63.4305, 10.3951),
    "Tromsø": (69.6492, 18.9553),
    "Kristiansand": (58.1467, 7.9956),
}

# ------------------- USER INPUTS -------------------
col1, col2 = st.columns(2)
with col1:
    selected_city = st.selectbox("Select City:", list(city_coords.keys()), index=0)
with col2:
    selected_year = st.selectbox("Select Year:", [2019, 2020, 2021, 2022, 2023, 2024], index=2)

lat, lon = city_coords[selected_city]
st.info(f"📍 Selected City: **{selected_city}** (Lat: {lat}, Lon: {lon})")

# ------------------- API DATA LOADING -------------------
@st.cache_data(ttl=3600)
def fetch_weather_data(lat, lon, year):
    """Fetch hourly ERA5 reanalysis data from Open-Meteo API for a given city and year."""
    url = (
        f"https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={year}-01-01&end_date={year}-12-31"
        "&hourly=temperature_2m,precipitation"
        "&timezone=Europe/Oslo"
    )
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame({
        "time": pd.to_datetime(data["hourly"]["time"]),
        "temperature": data["hourly"]["temperature_2m"],
        "precipitation": data["hourly"]["precipitation"],
    })
    return df

df = fetch_weather_data(lat, lon, selected_year)

if df.empty:
    st.warning("No weather data retrieved. Please check API or parameters.")
    st.stop()

# ------------------- HELPER FUNCTIONS -------------------
def high_pass_dct(temp_series, cutoff=50):
    """Apply Direct Cosine Transform high-pass filter for seasonal adjustment."""
    temp_dct = dct(temp_series, norm='ortho')
    temp_dct[:cutoff] = 0  # remove low-frequency components (trend/seasonal)
    return idct(temp_dct, norm='ortho')

# ------------------- TAB LAYOUT -------------------
tab1, tab2 = st.tabs(["Outlier Detection (SPC)", "Anomaly Detection (LOF)"])

# ------------------- TAB 1: SPC OUTLIERS -------------------
with tab1:
    st.subheader("Outlier Detection using Statistical Process Control (SPC)")
    st.markdown("""
    This analysis detects **temperature outliers** using a high-pass filtered signal (DCT) 
    and control limits based on robust statistics.
    """)

    cutoff = st.slider("Frequency cut-off for DCT (lower = more smoothing)", 10, 200, 50, step=10)
    std_mult = st.slider("Number of standard deviations for control limits", 1.0, 4.0, 3.0, step=0.5)

    # Compute seasonally adjusted temperature
    satv = high_pass_dct(df["temperature"].values, cutoff=cutoff)
    satv_mean, satv_std = np.mean(satv), np.std(satv)
    upper_limit, lower_limit = satv_mean + std_mult * satv_std, satv_mean - std_mult * satv_std

    outliers = (satv > upper_limit) | (satv < lower_limit)

    # Plot
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df["time"], y=df["temperature"], mode="lines", name="Temperature (°C)"))
    fig1.add_trace(go.Scatter(x=df["time"][outliers], y=df["temperature"][outliers],
                              mode="markers", name="Outliers", marker=dict(color="red", size=5)))
    fig1.add_hline(y=np.mean(df["temperature"]), line_dash="dot", annotation_text="Mean Temp")
    fig1.update_layout(
        title=f"SPC Outlier Detection for {selected_city} ({selected_year})",
        xaxis_title="Time", yaxis_title="Temperature (°C)", template="plotly_white"
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.write(f"Detected **{outliers.sum()} outliers** out of {len(df)} hourly records.")

# ------------------- TAB 2: LOF ANOMALIES -------------------
with tab2:
    st.subheader("Anomaly Detection using Local Outlier Factor (LOF)")
    st.markdown("""
    This tab detects **precipitation anomalies** using the Local Outlier Factor (LOF) method, 
    which measures how isolated each observation is from its neighbors.
    """)

    contamination = st.slider("Proportion of anomalies", 0.001, 0.05, 0.01, step=0.005)
    neighbors = st.slider("Number of neighbors (LOF parameter)", 5, 50, 20, step=5)

    df_lof = df[["precipitation"]].copy()
    df_lof["precipitation_smooth"] = df_lof["precipitation"].rolling(window=3, center=True, min_periods=1).mean()

    lof = LocalOutlierFactor(n_neighbors=neighbors, contamination=contamination)
    df_lof["lof_label"] = lof.fit_predict(df_lof[["precipitation_smooth"]])
    anomalies = df_lof[df_lof["lof_label"] == -1]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["time"], y=df["precipitation"], mode="lines", name="Precipitation (mm)"))
    fig2.add_trace(go.Scatter(x=df["time"].iloc[anomalies.index],
                              y=df["precipitation"].iloc[anomalies.index],
                              mode="markers", name="Anomalies", marker=dict(color="orange", size=6)))
    fig2.update_layout(
        title=f"LOF Precipitation Anomaly Detection for {selected_city} ({selected_year})",
        xaxis_title="Time", yaxis_title="Precipitation (mm)", template="plotly_white"
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.write(f"Detected **{len(anomalies)} precipitation anomalies** out of {len(df)} hourly records.")
