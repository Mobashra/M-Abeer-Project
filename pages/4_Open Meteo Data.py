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

st.info(f"""
**Analysis Scope:**
* **Location:** {current_area} ({coords['lat']:.2f}, {coords['lon']:.2f})
""")

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
# TAB 2: ADVANCED VISUALIZATION (FIXED)
# ==================================================
with tab2:
    st.subheader("Interactive Weather Plot")
    
    # --- CONTROLS ---
    c1, c2 = st.columns([3, 1])
    with c1:
        # Create Year-Month strings for slider
        df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
        unique_months = sorted(df_full['YYYY-MM'].unique())
        
        # FIX: Default to Jan 2021 - Feb 2021 (First 2 months)
        default_start = unique_months[0] # Jan 2021
        default_end = unique_months[1]   # Feb 2021
        
        start_month, end_month = st.select_slider(
            "Select Time Range",
            options=unique_months,
            value=(default_start, default_end) 
        )
        
    with c2:
        normalize = st.checkbox("Normalize (0-1 scale)", value=False)
        select_all = st.checkbox("Select All Variables")

    # Variable Selection
    default_cols = ["temperature_2m", "precipitation"]
    if select_all:
        default_cols = utils.WEATHER_VARS
        
    selected_cols = st.multiselect("Select variables:", utils.WEATHER_VARS, default=default_cols)

    # --- FILTER DATA ---
    # FIX: Use MonthEnd(0) so it stops at the END of the selected month, not the NEXT month
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
        # Don't plot wind direction as a jagged line (it looks bad), we use arrows instead
        if col == "wind_direction_10m": 
            continue 
        
        fig.add_trace(go.Scatter(
            x=filtered_df['time'], 
            y=filtered_df[col], 
            mode='lines', 
            name=col,
            line=dict(width=1.5, color=colors.get(col, "black"))
        ))

    # 2. Plot Wind Arrows (FIXED VISIBILITY)
    # Logic: Show arrows if "wind_direction_10m" OR "wind_speed_10m" is selected
    if "wind_direction_10m" in selected_cols or "wind_speed_10m" in selected_cols:
        
        # Downsample: Plot 1 arrow every ~20 points to avoid clutter
        step = max(1, len(filtered_df) // 30)
        arrow_data = filtered_df.iloc[::step]
        
        # Position arrows at y=0 (or slightly below)
        y_pos = 0 if normalize else arrow_data[selected_cols[0]].min()
        
        fig.add_trace(go.Scatter(
            x=arrow_data['time'],
            y=[y_pos] * len(arrow_data), 
            mode='markers',
            marker=dict(
                symbol="arrow-up",
                size=12,
                angle=arrow_data['wind_direction_10m'], # Rotates the arrow 0-360
                color="teal",
                line=dict(width=1, color="black")
            ),
            name="Wind Direction (Arrows)",
            hoverinfo="text",
            hovertext=arrow_data['wind_direction_10m'].astype(str) + "°"
        ))

    fig.update_layout(
        height=600,
        template="plotly_white",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        yaxis=dict(title="Normalized Value (0-1)" if normalize else "Value"),
        margin=dict(l=40, r=40, t=80, b=40),
        title=f"Weather Trends ({start_month} to {end_month})"
    )

    st.plotly_chart(fig, use_container_width=True)