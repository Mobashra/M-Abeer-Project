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
# TAB 1: STATISTICS (YEARLY + MONTHLY)
# ==================================================
with tab1:
    st.subheader("Statistical Overview")
    
    # 1. Year Selector
    stat_year = st.selectbox("Select Year:", [2021, 2022, 2023, 2024], index=0)
    df_stats = df_full[df_full['Year'] == stat_year].copy()
    
    if not df_stats.empty:
        # --- SECTION A: ANNUAL SUMMARY ---
        st.markdown(f"### 📅 Annual Summary ({stat_year})")
        summary_data = []
        for var in utils.WEATHER_VARS:
            summary_data.append({
                "Variable": var,
                "Avg": round(df_stats[var].mean(), 2),
                "Min": round(df_stats[var].min(), 2),
                "Max": round(df_stats[var].max(), 2),
                "Std Dev": round(df_stats[var].std(), 2),
                "Trend": df_stats[var].tolist()
            })
        
        st.dataframe(
            pd.DataFrame(summary_data),
            column_config={"Trend": st.column_config.LineChartColumn(f"Trend ({stat_year})")},
            hide_index=True, use_container_width=True
        )

        st.divider()

        # --- SECTION B: MONTHLY BREAKDOWN ---
        st.markdown(f"### 🗓️ Monthly Breakdown ({stat_year})")
        
        # Add Month Name for grouping
        df_stats['Month'] = df_stats['time'].dt.month_name()
        df_stats['MonthNum'] = df_stats['time'].dt.month
        
        # Aggregate
        # We treat variables differently: Rain is usually "Total" (Sum), Temp is "Avg" (Mean)
        monthly_agg = df_stats.groupby(['MonthNum', 'Month']).agg({
            'temperature_2m': 'mean',      # Avg Temp
            'precipitation': 'sum',        # Total Rain
            'wind_speed_10m': 'mean',      # Avg Wind
            'wind_gusts_10m': 'max'        # Max Gust
        }).reset_index()
        
        # Rename for clarity
        monthly_agg.rename(columns={
            'Month': 'Month',
            'temperature_2m': 'Avg Temp (°C)',
            'precipitation': 'Total Rain (mm)',
            'wind_speed_10m': 'Avg Wind (m/s)',
            'wind_gusts_10m': 'Max Gust (m/s)'
        }, inplace=True)

        # Sort by Month Number and drop the number column for display
        monthly_agg = monthly_agg.sort_values('MonthNum').drop(columns=['MonthNum'])
        
        # Display
        st.dataframe(monthly_agg.style.format("{:.2f}", subset=monthly_agg.columns[1:]), use_container_width=True)

    else:
        st.warning("No data.")

# ==================================================
# TAB 2: VISUALIZATION (SAME AS BEFORE)
# ==================================================
with tab2:
    st.subheader("Interactive Weather Plot")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
        unique_months = sorted(df_full['YYYY-MM'].unique())
        start_month, end_month = st.select_slider("Select Time Range", options=unique_months, value=(unique_months[0], unique_months[1]))
    with c2:
        st.write("") 
        normalize = st.checkbox("Normalize (0-1)", value=False)
        select_all = st.checkbox("Select All Variables", value=False)

    if select_all:
        default_selection = utils.WEATHER_VARS
    else:
        default_selection = ["temperature_2m", "precipitation"]
            
    selected_cols = st.multiselect("Variables:", utils.WEATHER_VARS, default=default_selection, key=f"vars_{select_all}")

    start_date = pd.to_datetime(start_month)
    end_date = (pd.to_datetime(end_month) + pd.offsets.MonthEnd(0)) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    mask = (df_full['time'] >= start_date) & (df_full['time'] <= end_date)
    df_plot = df_full.loc[mask].copy()

    if normalize:
        for col in selected_cols:
            min_v, max_v = df_plot[col].min(), df_plot[col].max()
            if max_v != min_v:
                df_plot[col] = (df_plot[col] - min_v) / (max_v - min_v)

    fig = go.Figure()
    
    colors = {"temperature_2m": "#1f77b4", "precipitation": "#2ca02c", "wind_speed_10m": "#ff7f0e", "wind_gusts_10m": "#7f7f7f", "wind_direction_10m": "purple"}

    for col in selected_cols:
        fig.add_trace(go.Scatter(x=df_plot['time'], y=df_plot[col], mode='lines', name=col, line=dict(width=1.5, color=colors.get(col, "black"))))

    fig.update_layout(
        height=500, template="plotly_white", title=f"Weather Trends ({start_month} to {end_month})",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        margin=dict(l=40, r=40, t=80, b=40),
        xaxis=dict(title="Time", showgrid=False),
        yaxis=dict(title="Normalized Value" if normalize else "Value", showgrid=True)
    )
    st.plotly_chart(fig, use_container_width=True)