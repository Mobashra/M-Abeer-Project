# page_2_weather_table.py
import streamlit as st
import pandas as pd
from datetime import datetime
from functools import lru_cache

# --- Mapping of price areas to city coordinates ---
cities = {
    "NO1": {"city": "Oslo", "latitude": 59.9139, "longitude": 10.7522},
    "NO2": {"city": "Kristiansand", "latitude": 58.1467, "longitude": 7.9956},
    "NO3": {"city": "Trondheim", "latitude": 63.4305, "longitude": 10.3951},
    "NO4": {"city": "Tromsø", "latitude": 69.6492, "longitude": 18.9553},
    "NO5": {"city": "Bergen", "latitude": 60.3942, "longitude": 5.3221},
}

variables = [
    "temperature_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m"
]

# --- Function to fetch weather data from Open-Meteo ---
@st.cache_data
def fetch_weather_data(lat: float, lon: float, year: int = 2021, timezone: str = "UTC") -> pd.DataFrame:
    import requests
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

# --- Page content ---
st.title("📊 Weather Data Table (2021)")

# Get selected price area from page 4
selected_area = st.session_state.get("selected_price_area", "NO1")
city_info = cities[selected_area]

st.markdown(f"### Weather data for **{city_info['city']} ({selected_area})**")

# Fetch weather data
df = fetch_weather_data(city_info["latitude"], city_info["longitude"], year=2021)

if df.empty:
    st.warning("No weather data found for the selected price area.")
    st.stop()

# Extract month for table purposes
df["month"] = df["time"].dt.month

# Filter for January as default overview
january = df[df["month"] == 1]

# Build summary DataFrame with sparkline trend for January
summary = pd.DataFrame({
    "Variable": variables,
    "January Trend": [january[var].tolist() for var in variables]
})

st.markdown("---")
st.dataframe(
    summary,
    column_config={
        "January Trend": st.column_config.LineChartColumn("January Trend")
    },
    hide_index=True,
    use_container_width=True
)
