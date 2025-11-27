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

# --- 2. FETCH FULL HISTORY ---
with st.spinner("Fetching weather history (2021-2024)..."):
    df_full = utils.fetch_weather_api(coords['lat'], coords['lon'], "2021-01-01", "2024-12-31")

if df_full.empty:
    st.error("No weather data available.")
    st.stop()

df_full['Year'] = df_full['time'].dt.year

# --- 3. TABS ---
tab1, tab2 = st.tabs(["📊 Statistics Table", "📈 Advanced Visualization"])

# ==================================================
# TAB 1: STATISTICS (Year Specific)
# ==================================================
with tab1:
    st.subheader("Yearly Statistics")
    # Moved Year Selector INSIDE Tab 1 so it doesn't affect Tab 2
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
# TAB 2: VISUALIZATION (Full History + Custom Range)
# ==================================================
with tab2:
    st.subheader("Interactive Weather Plot")
    
    # 1. TIME RANGE SLIDER (Full Width)
    df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
    unique_months = sorted(df_full['YYYY-MM'].unique())
    
    # Default: Jan 2021 to Feb 2021 (First 2 months only)
    start_month, end_month = st.select_slider(
        "Select Time Range",
        options=unique_months,
        value=(unique_months[0], unique_months[1]) 
    )

    # 2. VARIABLE SELECTOR (New Line, Full Width)
    # Default: Select ALL numeric variables (exclude direction which is special)
    default_vars = [c for c in utils.WEATHER_VARS if c != "wind_direction_10m"]
    selected_cols = st.multiselect("Select Variables to Plot:", utils.WEATHER_VARS, default=default_vars)

    # 3. CHECKBOXES (Separate Columns)
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        normalize = st.checkbox("Normalize (0-1 scale)", value=False)
    with c2:
        show_arrows = st.checkbox("Show Wind Arrows", value=False)

    # --- FILTER DATA ---
    # Use MonthEnd(0) to get the exact last day of the end month
    start_date = pd.to_datetime(start_month)
    end_date = (pd.to_datetime(end_month) + pd.offsets.MonthEnd(0)) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    
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
    
    colors = {
        "temperature_2m": "#1f77b4", 
        "precipitation": "#2ca02c", 
        "wind_speed_10m": "#ff7f0e", 
        "wind_gusts_10m": "#7f7f7f", 
        "wind_direction_10m": "purple"
    }

    # 1. Lines
    for col in selected_cols:
        if col == "wind_direction_10m": continue 
        
        fig.add_trace(go.Scatter(
            x=df_plot['time'], 
            y=df_plot[col], 
            mode='lines', 
            name=col,
            line=dict(width=1.5, color=colors.get(col, "black"))
        ))

    # 2. Arrows (Only if checked)
    if show_arrows and "wind_direction_10m" in df_full.columns:
        # Downsample arrows based on zoom level
        step = max(1, len(df_plot) // 30)
        arrow_data = df_plot.iloc[::step].copy()
        
        # Position arrows below chart
        y_pos = -0.15 if normalize else df_plot[selected_cols[0]].min()
        
        # Rotate 180 to point with wind
        arrow_angles = (arrow_data['wind_direction_10m'] + 180) % 360

        fig.add_trace(go.Scatter(
            x=arrow_data['time'],
            y=[y_pos] * len(arrow_data), 
            mode='markers',
            marker=dict(
                symbol="arrow-up", 
                size=14, 
                angle=arrow_angles, 
                color="teal", 
                line=dict(width=1, color="darkslategray")
            ),
            name="Wind Direction",
            hoverinfo="text",
            hovertext=arrow_data['time'].dt.strftime('%Y-%m-%d %H:00') + "<br>Dir: " + arrow_data['wind_direction_10m'].astype(str) + "°"
        ))

    fig.update_layout(
        height=600,
        template="plotly_white",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        yaxis=dict(title="Normalized Value" if normalize else "Value", showgrid=True),
        xaxis=dict(showgrid=False),
        margin=dict(l=40, r=40, t=80, b=80),
        title=f"Weather Trends ({start_month} to {end_month})"
    )

    st.plotly_chart(fig, use_container_width=True)