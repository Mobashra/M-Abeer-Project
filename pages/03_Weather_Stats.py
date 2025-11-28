import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import utils

st.set_page_config(page_title="Weather Statistics", layout="wide")

# --- DEFAULT FALLBACK: Initialize to NO1 if accessed directly ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    # Auto-fill coords for NO1
    city_def = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": city_def["lat"], "lon": city_def["lon"]}

# 1. SAFETY & STYLING
# Now this check will always pass because we set the default above
utils.check_session_state() 
utils.render_sidebar()

st.title("Weather Data Analysis")
st.header("Explore Weather Statistics & Trends (2021-2024)")

# --- ACTIVE AREA CONTEXT ---
global_area = st.session_state.get("selected_price_area", "NO1")

# 2. GLOBAL SETTINGS & LOCAL OVERRIDE
c1, c2 = st.columns([1, 3])

with c1:
    area_list = sorted(utils.CITIES.keys())
    try:
        default_index = area_list.index(global_area)
    except ValueError:
        default_index = 0
    
    selected_area_local = st.selectbox(
        "Analysis Region", 
        area_list, 
        index=default_index
    )

st.info(f"📍 **Currently Viewing:** Price Area **{selected_area_local}**")

# 3. GET COORDINATES FOR LOCAL SELECTION
city_data = utils.CITIES[selected_area_local]
local_lat = city_data["lat"]
local_lon = city_data["lon"]

# 4. FETCH DATA
@st.cache_data(ttl=3600)
def get_full_weather_history(lat, lon):
    return utils.fetch_weather_api(lat, lon, "2021-01-01", "2024-12-31")

with st.spinner(f"Fetching weather history for {selected_area_local}..."):
    df_full = get_full_weather_history(local_lat, local_lon)

if df_full.empty:
    st.error("No weather data available.")
    st.stop()

df_full['Year'] = df_full['time'].dt.year
df_full['Month'] = df_full['time'].dt.month

# 5. TABS
tab1, tab2 = st.tabs(["📊 Dataset Overview (First Month)", "📈 Yearly Trend Visualization"])

# ==================================================
# TAB 1: DATASET OVERVIEW
# ==================================================
with tab1:
    st.subheader("Dataset Overview with First Month Trends")
    st.caption("Each row represents a variable from the dataset, with a line chart showing the **January** trend.")
    
    stat_year = st.selectbox("Select Year:", [2021, 2022, 2023, 2024], index=0)
    
    df_year = df_full[df_full['Year'] == stat_year].copy()
    df_jan = df_year[df_year['Month'] == 1].copy()
    
    if not df_year.empty:
        summary_data = []
        for var in utils.WEATHER_VARS:
            mean_val = df_year[var].mean()
            std_val = df_year[var].std()
            min_val = df_year[var].min()
            max_val = df_year[var].max()
            jan_trend = df_jan[var].tolist()
            
            summary_data.append({
                "Variable Name": var,
                "Mean": round(mean_val, 2),
                "Std Dev": round(std_val, 2),
                "Min": round(min_val, 2),
                "Max": round(max_val, 2),
                "First Month Trend": jan_trend
            })
        
        stats_df = pd.DataFrame(summary_data)
        
        st.dataframe(
            stats_df,
            column_config={
                "Variable Name": st.column_config.TextColumn("Variable Name", width="medium"),
                "First Month Trend": st.column_config.LineChartColumn(
                    f"Trend (Jan {stat_year})",
                    y_min=0,
                    y_max=None
                ),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("No data.")

# ==================================================
# TAB 2: YEARLY TREND
# ==================================================
with tab2:
    st.subheader("Yearly Trend Visualization")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
        unique_months = sorted(df_full['YYYY-MM'].unique())
        
        start_month, end_month = st.select_slider(
            "Select Time Range",
            options=unique_months,
            value=(unique_months[0], unique_months[-1])
        )
        
    with c2:
        st.write("") 
        normalize = st.checkbox("Normalize (0-1)", value=False)
        select_all = st.checkbox("Select All Variables", value=False)

    if select_all:
        default_selection = utils.WEATHER_VARS
    else:
        default_selection = ["temperature_2m"]
            
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
    
    colors = {
        "temperature_2m": "#1f77b4", "precipitation": "#2ca02c",
        "wind_speed_10m": "#ff7f0e", "wind_gusts_10m": "#7f7f7f",
        "wind_direction_10m": "purple"
    }

    for col in selected_cols:
        fig.add_trace(go.Scatter(
            x=df_plot['time'],
            y=df_plot[col],
            mode='lines',
            name=col,
            line=dict(width=1.5, color=colors.get(col, "black"))
        ))

    fig.update_layout(
        height=500, template="plotly_white",
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
        margin=dict(l=40, r=40, t=80, b=40),
        xaxis=dict(title="Time", showgrid=False),
        yaxis=dict(title="Normalized Value (0-1)" if normalize else "Value", showgrid=True),
        title=f"Weather Trends ({start_month} to {end_month})"
    )

    st.plotly_chart(fig, use_container_width=True)