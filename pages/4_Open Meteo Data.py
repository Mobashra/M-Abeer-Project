import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
from datetime import datetime

st.set_page_config(page_title="Weather Visualization", layout="wide")

st.title("Weather Data Visualisation (2021–2024)")

# --- 1. GET LOCATION & DATA ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

# --- 2. BLUE CONTEXT BOX ---
st.info(f"""
**Analysis Scope** (by the explorer page configuration):
* **Weather Location (Price Area):** {current_area} ({coords['lat']:.2f}, {coords['lon']:.2f})
""")

# --- 3. FETCH FULL HISTORY (2021-2024) ---
# We fetch the full range once and cache it. This allows the slider to be instant.
with st.spinner("Fetching 4-year weather history..."):
    df = utils.fetch_weather_api(coords['lat'], coords['lon'], "2021-01-01", "2024-12-31")

if df.empty:
    st.error("No weather data available.")
    st.stop()

# --- 4. CONTROLS ---
# Variable Selector
all_cols = ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m"]
selected_cols = st.multiselect("Select columns", all_cols, default=all_cols)

# Create Year-Month list for Slider
# We convert dates to "YYYY-MM" strings for the slider labels
df['YYYY-MM'] = df['time'].dt.to_period('M').astype(str)
unique_months = sorted(df['YYYY-MM'].unique())

# Slider Logic
start_month, end_month = st.select_slider(
    "Select Month Range (Year-Month)",
    options=unique_months,
    value=(unique_months[-12], unique_months[-1]) # Default to last year
)

# Normalization Checkbox
normalize = st.checkbox("Normalize numeric columns (0-1 scale)", value=True)

# --- 5. DATA PROCESSING ---
# Filter by Date Range
start_date = pd.to_datetime(start_month)
# For end date, we want the end of that month. Trick: go to next month day 1, subtract 1 sec.
end_date = (pd.to_datetime(end_month) + pd.offsets.MonthBegin(1)) + pd.offsets.MonthEnd(1)

mask = (df['time'] >= start_date) & (df['time'] <= end_date)
filtered_df = df.loc[mask].copy()

# Normalization Logic
if normalize:
    for col in selected_cols:
        min_val = filtered_df[col].min()
        max_val = filtered_df[col].max()
        if max_val != min_val:
            filtered_df[col] = (filtered_df[col] - min_val) / (max_val - min_val)

# --- 6. PLOTTING ---
st.subheader(f"All columns for {start_month} – {end_month}")

fig = go.Figure()

# Plot Lines
colors = {"temperature_2m": "#1f77b4", "precipitation": "#2ca02c", "wind_speed_10m": "#ff7f0e", "wind_gusts_10m": "#7f7f7f"}

for col in selected_cols:
    fig.add_trace(go.Scatter(
        x=filtered_df['time'], 
        y=filtered_df[col], 
        mode='lines', 
        name=col,
        line=dict(width=1.5, color=colors.get(col, "black"))
    ))

# --- WIND DIRECTION ARROWS (The Advanced Feature) ---
# We don't want 1 arrow per hour (too messy). We downsample to 1 arrow every ~12-24 hours depending on zoom.
# Calculate step size based on total data points to show ~30-50 arrows max
step = max(1, len(filtered_df) // 40)
arrow_data = filtered_df.iloc[::step]

# Plot Arrows (using Markers)
# Symbol 'arrow-up' rotated by the wind direction angle
fig.add_trace(go.Scatter(
    x=arrow_data['time'],
    y=[-0.05] * len(arrow_data), # Place them just below the graph (y=0)
    mode='markers',
    marker=dict(
        symbol="arrow-up",
        size=10,
        angle=arrow_data['wind_direction_10m'], # Rotates the arrow
        color="teal"
    ),
    name="Wind Direction",
    hoverinfo="skip" # Don't show hover tooltip for arrows
))

# Layout Styling
fig.update_layout(
    height=600,
    template="plotly_white",
    legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
    yaxis=dict(title="Normalized Value (0-1)" if normalize else "Value", showgrid=True, gridcolor='#f0f0f0'),
    xaxis=dict(showgrid=False),
    margin=dict(l=40, r=40, t=40, b=80)
)

st.plotly_chart(fig, use_container_width=True)