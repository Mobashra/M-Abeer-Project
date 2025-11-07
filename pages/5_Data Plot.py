# page_3_weather_plot.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import calendar
import requests

#Mapping of price areas to city coordinates
cities = {"NO1": {"city": "Oslo", "latitude": 59.9139, "longitude": 10.7522},
    "NO2": {"city": "Kristiansand", "latitude": 58.1467, "longitude": 7.9956},
    "NO3": {"city": "Trondheim", "latitude": 63.4305, "longitude": 10.3951},
    "NO4": {"city": "Tromsø", "latitude": 69.6492, "longitude": 18.9553},
    "NO5": {"city": "Bergen", "latitude": 60.3942, "longitude": 5.3221},}

variables = ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]

# Function to fetch Open-Meteo weather data using era5 reanalysis
@st.cache_data
def fetch_weather_data(lat: float, lon: float, year: int = 2021, timezone: str = "UTC") -> pd.DataFrame:
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    hourly_vars = ",".join(variables)
    url = (
        f"https://archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&hourly={hourly_vars}&timezone={timezone}")
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

# Page content
st.title("Weather Variable Plot 2021")
st.info("By default, the graph shows weather variables for price area NO1. If you want to see a different price area, select from 'Elhub API Data' page.")
# Get selected price area from page 2
selected_area = st.session_state.get("selected_price_area", "NO1")
city_info = cities[selected_area]

st.markdown(f"### Weather data for **{city_info['city']} ({selected_area})**")

# Fetch weather data
df = fetch_weather_data(city_info["latitude"], city_info["longitude"], year=2021)

if df.empty:
    st.warning("No weather data available for the selected price area.")
    st.stop()

# Prepare month column for filtering 
df["Month"] = df["time"].dt.month
months = list(calendar.month_name)[1:]  # ['January', 'February', ...]

# Month slider
selected_range = st.select_slider("Select month range",options=months,value=(months[0], months[0]))

# Filter based on month selection
if isinstance(selected_range, tuple):
    start, end = [months.index(m) + 1 for m in selected_range]
    subset = df[(df['Month'] >= start) & (df['Month'] <= end)]
else:
    month_num = months.index(selected_range) + 1
    subset = df[df['Month'] == month_num]

subset_plot = subset.set_index("time")

# Select numeric columns
numeric_columns = [col for col in subset_plot.select_dtypes(include='number').columns if col != "Month"]

# Column selection
choice = st.selectbox("Select a column to plot", ["All"] + numeric_columns)

# Plotly figure
fig = go.Figure()
if choice == "All":
    for col in numeric_columns:
        fig.add_trace(go.Scatter(x=subset_plot.index, y=subset_plot[col], mode="lines", name=col))
    plot_title = "Graph of all variables"
else:
    fig.add_trace(go.Scatter(x=subset_plot.index, y=subset_plot[choice], mode="lines", name=choice))
    plot_title = f"Graph of {choice}"

# Add month range to title
if isinstance(selected_range, tuple):
    plot_title += f" ({selected_range[0]} - {selected_range[1]})"
else:
    plot_title += f" ({selected_range})"

# Layout
fig.update_layout(title=plot_title, xaxis_title="Time", yaxis_title="Range of values of the variables",
    template="plotly_white", legend=dict(x=1, y=1, bgcolor="rgba(0,0,0,0)"))

# Hover format
fig.update_traces(hovertemplate='%{x|%b %d, %Y}<br>%{y}')

# X-axis month formatting
fig.update_xaxes(dtick="M1", tickformat="%b")

# Display figure
st.plotly_chart(fig, use_container_width=True)
