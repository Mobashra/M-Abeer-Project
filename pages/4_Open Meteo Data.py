import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import utils 

st.set_page_config(page_title="Weather Statistics", layout="wide")
st.title("🌤️ Weather Data Analysis")

# --- 1. GLOBAL SETTINGS ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

st.info(f"**Analysis Scope:** {current_area} ({coords['lat']:.2f}, {coords['lon']:.2f})")

# --- 2. FETCH DATA ---
with st.spinner("Fetching weather history (2021-2024)..."):
    df_full = utils.fetch_weather_api(coords['lat'], coords['lon'], "2021-01-01", "2024-12-31")

if df_full.empty:
    st.error("No weather data available.")
    st.stop()

df_full['Year'] = df_full['time'].dt.year

# --- 3. TABS ---
tab1, tab2 = st.tabs(["📊 Statistics & Trends", "📈 Advanced Visualization"])

# ==================================================
# TAB 1: STATISTICS (Your Original Logic)
# ==================================================
with tab1:
    st.subheader("Yearly Statistics")
    stat_year = st.selectbox("Select Year:", [2021, 2022, 2023, 2024], index=0)
    
    df_stats = df_full[df_full['Year'] == stat_year].copy()
    
    if not df_stats.empty:
        summary_data = []
        for var in utils.WEATHER_VARS:
            summary_data.append({
                "Variable": var,
                "Average": round(df_stats[var].mean(), 2),
                "Std Dev": round(df_stats[var].std(), 2),
                "Min": round(df_stats[var].min(), 2),
                "Max": round(df_stats[var].max(), 2),
                "Trend": df_stats[var].tolist()
            })
        
        st.dataframe(
            pd.DataFrame(summary_data),
            column_config={"Trend": st.column_config.LineChartColumn(f"Trend ({stat_year})")},
            hide_index=True, use_container_width=True
        )
    else:
        st.warning("No data.")

# ==================================================
# TAB 2: PLOT (With Improved Arrow Logic)
# ==================================================
with tab2:
    st.subheader("Interactive Weather Plot")
    
    # --- CONTROLS ---
    c1, c2 = st.columns([3, 1])
    with c1:
        df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
        months = sorted(df_full['YYYY-MM'].unique())
        
        # Default: First 2 months
        start_m, end_m = st.select_slider("Time Range", options=months, value=(months[0], months[1]))
        
    with c2:
        normalize = st.checkbox("Normalize (0-1)", value=True)

    selected_cols = st.multiselect("Variables:", utils.WEATHER_VARS, default=["temperature_2m", "precipitation", "wind_speed_10m"])

    # --- FILTER ---
    start_date = pd.to_datetime(start_m)
    end_date = (pd.to_datetime(end_m) + pd.offsets.MonthEnd(0)) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    mask = (df_full['time'] >= start_date) & (df_full['time'] <= end_date)
    df_plot = df_full.loc[mask].copy()

    # --- NORMALIZE ---
    if normalize:
        for col in selected_cols:
            min_v, max_v = df_plot[col].min(), df_plot[col].max()
            if max_v != min_v:
                df_plot[col] = (df_plot[col] - min_v) / (max_v - min_v)

    # --- PLOTTING ---
    fig = go.Figure()
    
    # 1. Lines
    for col in selected_cols:
        if col == "wind_direction_10m": continue
        fig.add_trace(go.Scatter(x=df_plot['time'], y=df_plot[col], mode='lines', name=col))

    # 2. ARROWS (The Advanced Logic)
    # Only draw if Wind Direction is available
    if "wind_direction_10m" in df_plot.columns and ("wind_direction_10m" in selected_cols or "wind_speed_10m" in selected_cols):
        
        # Constants for arrow drawing
        ARROW_COLOR = "teal"
        ARROW_Y_POS = -0.1 if normalize else df_plot[selected_cols[0]].min() * 0.95
        ARROW_LEN = 0.1  # Length of arrow shaft
        
        # Downsample (1 arrow every ~30 points)
        step = max(1, len(df_plot) // 30)
        
        # Calculate Time Span for X-axis vector math
        time_span = df_plot['time'].iloc[-1] - df_plot['time'].iloc[0]
        time_offset_mag = time_span * 0.015 # Scale X-vector relative to total time

        for i in range(0, len(df_plot), step):
            row = df_plot.iloc[i]
            t = row["time"]
            wind_dir = row["wind_direction_10m"]

            # Vector Math: Convert degrees to radians (Rotate 180 to point 'with' wind)
            theta = np.deg2rad(wind_dir + 180)
            
            # Calculate Tail Position (ax, ay) relative to Head (x, y)
            # Y-axis (Value): Cosine
            y_change = np.cos(theta) * ARROW_LEN
            tail_y = ARROW_Y_POS + y_change
            
            # X-axis (Time): Sine
            x_change = np.sin(theta)
            tail_x = t + (time_offset_mag * x_change)

            # Draw Vector Arrow
            fig.add_annotation(
                x=t, y=ARROW_Y_POS,        # Arrow Head
                ax=tail_x, ay=tail_y,      # Arrow Tail
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=1.5,
                arrowcolor=ARROW_COLOR
            )
            
        # Legend Dummy (so user knows what Teal arrows are)
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(symbol='triangle-up', color='teal', size=10),
            name='Wind Direction', showlegend=True
        ))

    fig.update_layout(
        height=600, template="plotly_white",
        title=f"Weather Trends ({start_m} to {end_m})",
        margin=dict(b=80, t=50),
        yaxis=dict(title="Normalized" if normalize else "Value")
    )

    st.plotly_chart(fig, use_container_width=True)