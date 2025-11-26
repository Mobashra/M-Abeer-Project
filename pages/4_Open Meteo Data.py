import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
import numpy as np 

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

# --- 2. FETCH DATA (FULL HISTORY) ---
with st.spinner("Fetching weather history (2021-2024)..."):
    df_full = utils.fetch_weather_api(coords['lat'], coords['lon'], "2021-01-01", "2024-12-31")

if df_full.empty:
    st.error("No weather data available.")
    st.stop()

df_full['Year'] = df_full['time'].dt.year

# --- 3. TABS ---
tab1, tab2 = st.tabs(["📊 Statistics & Trends", "📈 Advanced Visualization"])

# ==================================================
# TAB 1: STATISTICS TABLE
# ==================================================
with tab1:
    st.subheader("Yearly Statistics")
    stat_year = st.selectbox("Select Year for Statistics:", [2021, 2022, 2023, 2024], index=0)
    
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
                "Trend Line": df_stats[var].tolist()
            })
        
        st.dataframe(
            pd.DataFrame(summary_data),
            column_config={
                "Trend Line": st.column_config.LineChartColumn(
                    f"Trend ({stat_year})", y_min=0, y_max=None
                )
            },
            hide_index=True, use_container_width=True
        )
    else:
        st.warning(f"No data available for {stat_year}.")

# ==================================================
# TAB 2: ADVANCED VISUALIZATION (ARROWS FIXED)
# ==================================================
with tab2:
    st.subheader("Interactive Weather Plot")
    
    # --- CONTROLS ---
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        # Slider
        df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
        unique_months = sorted(df_full['YYYY-MM'].unique())
        
        # Default: Jan 2021 - Mar 2021
        start_month, end_month = st.select_slider(
            "Select Time Range",
            options=unique_months,
            value=(unique_months[0], unique_months[2]) 
        )
    
    with c2:
        normalize = st.checkbox("Normalize (0-1 scale)", value=True)
        show_arrows = st.checkbox("Show Wind Direction", value=True) # Explicit toggle

    with c3:
        # Variable Selection
        default_cols = ["temperature_2m", "precipitation"]
        selected_cols = st.multiselect("Variables:", utils.WEATHER_VARS, default=default_cols)

    # --- FILTER DATA ---
    # Use MonthEnd(0) to stop exactly at the end of the selected month
    start_date = pd.to_datetime(start_month)
    end_date = (pd.to_datetime(end_month) + pd.offsets.MonthEnd(0)) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    
    mask = (df_full['time'] >= start_date) & (df_full['time'] <= end_date)
    filtered_df = df_full.loc[mask].copy()

    # Normalization
    if normalize:
        for col in selected_cols:
            min_v = filtered_df[col].min()
            max_v = filtered_df[col].max()
            if max_v != min_v:
                filtered_df[col] = (filtered_df[col] - min_v) / (max_v - min_v)

    # --- PLOTTING ---
    fig = go.Figure()
    
    colors = {
        "temperature_2m": "#1f77b4", 
        "precipitation": "#2ca02c", 
        "wind_speed_10m": "#ff7f0e", 
        "wind_gusts_10m": "#7f7f7f", 
        "wind_direction_10m": "purple"
    }

    # 1. Plot Lines
    for col in selected_cols:
        if col == "wind_direction_10m": continue # Never plot direction as a line
        
        fig.add_trace(go.Scatter(
            x=filtered_df['time'], 
            y=filtered_df[col], 
            mode='lines', 
            name=col,
            line=dict(width=1.5, color=colors.get(col, "black"))
        ))

    # 2. Plot Wind Arrows (THE FIX)
    if show_arrows:
        # Downsample: 1 arrow every ~24 hours (or dynamic based on zoom)
        # If range is short (1 month), show more arrows. If long (3 years), show fewer.
        total_hours = len(filtered_df)
        step = max(1, total_hours // 30) # Aim for ~30 arrows total across the chart
        
        arrow_data = filtered_df.iloc[::step]
        
        # Place arrows at y=-0.1 (Below the 0 line so they don't overlap data)
        y_pos = -0.1 if normalize else filtered_df[selected_cols[0]].min() * 0.9
        
        fig.add_trace(go.Scatter(
            x=arrow_data['time'],
            y=[y_pos] * len(arrow_data), 
            mode='markers',
            marker=dict(
                symbol="arrow-up",  # The base shape
                size=12,            # Make them visible
                angle=arrow_data['wind_direction_10m'], # Rotates based on data (0=N, 90=E)
                color="teal",
                line=dict(width=1, color="black")
            ),
            name="Wind Direction",
            hoverinfo="text",
            hovertext=arrow_data['time'].dt.strftime('%Y-%m-%d %H:00') + "<br>Dir: " + arrow_data['wind_direction_10m'].astype(str) + "°"
        ))

    fig.update_layout(
        height=600,
        template="plotly_white",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        yaxis=dict(title="Normalized Value (0-1)" if normalize else "Value"),
        # Add padding at bottom for the arrows
        margin=dict(l=40, r=40, t=80, b=80),
        title=f"Weather Trends ({start_month} to {end_month})"
    )

    st.plotly_chart(fig, use_container_width=True)