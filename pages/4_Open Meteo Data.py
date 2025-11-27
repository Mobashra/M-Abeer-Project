import streamlit as st
import pandas as pd
import numpy as np 
import plotly.graph_objects as go
import utils # <--- Using your existing utils

st.set_page_config(page_title="Weather Data Visualization", layout="wide")
st.title("Weather Data Visualisation (2021–2024)")

# --- 1. GLOBAL SETTINGS ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

# --- DISPLAY CONTEXT BOX ---
st.info(f"""
**Analysis Scope:**
* **Weather Location (Price Area):** {current_area} ({coords['lat']:.2f}, {coords['lon']:.2f})
""")

# --- 2. FETCH DATA ---
# We load the full history once so the slider is fast
with st.spinner("Fetching weather history..."):
    df_raw = utils.fetch_weather_api(coords['lat'], coords['lon'], "2021-01-01", "2024-12-31")

if df_raw.empty:
    st.error("No weather data available.")
    st.stop()

# --- 3. WIDGETS ---
WIND_DIRECTION_COL = "wind_direction_10m"
WIND_ARROW_COLOR = '#128264'
LINE_COLORS = ['#035397', '#128264', '#f9c80e', '#546e7a', '#9dc183']

# Column Selector
columns = [c for c in df_raw.columns if c not in ['time', WIND_DIRECTION_COL]]
selected_col = st.selectbox("Select a column", ["All columns"] + columns)

# Month Slider
df_raw['year_month'] = df_raw['time'].dt.to_period('M').astype(str)
available_months = sorted(df_raw['year_month'].unique())

if not available_months:
    st.error("No date data found.")
    st.stop()

start_month, end_month = st.select_slider(
    "Select Month Range (Year-Month)",
    options=available_months,
    value=(available_months[-12], available_months[-1]) # Default last year
)

normalize_flag = st.checkbox("Normalize numeric columns (0-1 scale)", value=True)

# --- 4. DATA PROCESSING ---
# Filter by Date
start_date = pd.to_datetime(start_month)
end_date = (pd.to_datetime(end_month) + pd.offsets.MonthEnd(0)) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

mask = (df_raw['time'] >= start_date) & (df_raw['time'] <= end_date)
df_plot = df_raw.loc[mask].copy()

# Normalize
if normalize_flag:
    cols_to_norm = [c for c in df_plot.select_dtypes(include="number").columns if c != WIND_DIRECTION_COL]
    for col in cols_to_norm:
        min_val = df_plot[col].min()
        max_val = df_plot[col].max()
        if max_val != min_val:
            df_plot[col] = (df_plot[col] - min_val) / (max_val - min_val)
        else:
            df_plot[col] = 0.5 

# --- 5. PLOTTING LOGIC ---
fig = go.Figure()

# A. Plot Lines
if selected_col == "All columns":
    plot_cols = [c for c in columns if c in df_plot.columns]
    for i, col in enumerate(plot_cols):
        fig.add_trace(go.Scatter(
            x=df_plot["time"], y=df_plot[col], mode="lines",
            line=dict(color=LINE_COLORS[i % len(LINE_COLORS)], width=2), name=col
        ))
else:
    fig.add_trace(go.Scatter(
        x=df_plot["time"], y=df_plot[selected_col], mode="lines",
        line=dict(color=LINE_COLORS[0], width=2), name=selected_col
    ))

# B. Arrow Logic (The Advanced Part)
# Only show arrows if "All columns" or "Wind Direction" is relevant
if WIND_DIRECTION_COL in df_plot.columns:
    # 1. Determine Y-position for arrows (Below the chart)
    # If normalized, data is 0-1. We put arrows at -0.1
    # If raw, we find the min value and go 10% lower
    if normalize_flag:
        arrow_y = -0.1
        arrow_len = 0.1
    else:
        # Find global min/max to scale arrows properly
        current_vals = df_plot[selected_col] if selected_col != "All columns" else df_plot[columns]
        g_min = current_vals.min().min() if isinstance(current_vals, pd.DataFrame) else current_vals.min()
        g_max = current_vals.max().max() if isinstance(current_vals, pd.DataFrame) else current_vals.max()
        arrow_y = g_min - (g_max - g_min) * 0.1
        arrow_len = (g_max - g_min) * 0.1

    # 2. Downsample (Show 1 arrow every ~30-50 points)
    arrow_step = max(1, len(df_plot) // 40)
    
    # 3. Calculate Time Offset for X-axis vector component
    time_span = df_plot['time'].iloc[-1] - df_plot['time'].iloc[0]
    time_offset_mag = time_span * 0.015 

    for i in range(0, len(df_plot), arrow_step):
        row = df_plot.iloc[i]
        t = row["time"]
        wind_dir = row[WIND_DIRECTION_COL]

        # Math: Convert degrees to radians. 
        # 0 deg = North (Up). In Plotly X/Y:
        # X is Time, Y is Value.
        # We rotate 180 because wind "comes from" the direction.
        theta = np.deg2rad(wind_dir + 180) 

        # Calculate Arrow Head position
        y_change = np.cos(theta) * arrow_len
        arrow_y2 = arrow_y + y_change * 0.8

        x_change = np.sin(theta)
        arrow_x2 = t + (time_offset_mag * x_change)
        
        # Add Annotation (The Arrow)
        fig.add_annotation(
            x=t, y=arrow_y,       # Tail
            ax=arrow_x2, ay=arrow_y2, # Head
            xref="x", yref="y", axref="x", ayref="y",
            text="", showarrow=True, 
            arrowhead=3, arrowsize=1, arrowwidth=1.5,
            arrowcolor=WIND_ARROW_COLOR
        )

    # Legend Item
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(symbol="triangle-up", color=WIND_ARROW_COLOR, size=10),
        name="Wind Direction", showlegend=True
    ))

# --- 6. FINAL LAYOUT ---
header_text = f"{selected_col} ({start_month} to {end_month})"
fig.update_layout(
    title=dict(text=header_text, x=0.5, xanchor="center", font=dict(size=20)),
    xaxis_title="Time",
    template="plotly_white",
    height=600,
    legend=dict(orientation="h", y=-0.2),
    margin=dict(b=80, t=80) # Extra bottom margin for arrows
)

st.plotly_chart(fig, use_container_width=True)