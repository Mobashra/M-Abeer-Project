import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import utils

st.set_page_config(page_title="Weather Statistics", layout="wide")

# 1. RENDER SIDEBAR (But DO NOT check/block session state)
utils.render_sidebar()

st.title("Weather Data Analysis")
st.header("Explore Weather Statistics & Trends (2021-2024)")

# --- 2. INTELLIGENT DEFAULT LOGIC ---
# Try to get global state, but default to NO1 if missing (Read-Only)
global_area = st.session_state.get("selected_price_area") 
default_area = global_area if global_area else "NO1"

# Layout Controls
c1, c2 = st.columns([1, 3])

with c1:
    area_list = sorted(utils.CITIES.keys())
    try:
        start_index = area_list.index(default_area)
    except ValueError:
        start_index = 0
    
    # LOCAL SELECTOR: Changes here do NOT affect the Global Map Pin
    local_area = st.selectbox("Analysis Region", area_list, index=start_index)

st.info(f"📍 **Currently Viewing:** Price Area **{local_area}**")

# --- 3. DERIVE LOCAL COORDINATES ---
# We look up coordinates for the LOCAL selection (ignoring global pin)
city_data = utils.CITIES[local_area]
local_lat = city_data["lat"]
local_lon = city_data["lon"]

# --- 4. FETCH DATA ---
@st.cache_data(ttl=3600)
def get_full_weather_history(lat, lon):
    return utils.fetch_weather_api(lat, lon, "2021-01-01", "2024-12-31")

with st.spinner(f"Fetching weather history for {local_area}..."):
    df_full = get_full_weather_history(local_lat, local_lon)

if df_full.empty:
    st.error("No weather data available.")
    st.stop()

df_full['Year'] = df_full['time'].dt.year
df_full['Month'] = df_full['time'].dt.month

# --- 5. VISUALIZATION TABS ---
tab1, tab2 = st.tabs(["📊 Dataset Overview", "📈 Yearly Trends"])

with tab1:
    st.subheader("Dataset Overview")
    stat_year = st.selectbox("Select Year:", [2021, 2022, 2023, 2024], index=0)
    
    df_year = df_full[df_full['Year'] == stat_year].copy()
    df_jan = df_year[df_year['Month'] == 1].copy()
    
    if not df_year.empty:
        summary_data = []
        for var in utils.WEATHER_VARS:
            mean_val = df_year[var].mean()
            std_val = df_year[var].std()
            jan_trend = df_jan[var].tolist()
            
            summary_data.append({
                "Variable Name": var, "Mean": round(mean_val, 2), "Std Dev": round(std_val, 2),
                "First Month Trend": jan_trend
            })
        
        st.dataframe(pd.DataFrame(summary_data), column_config={
            "First Month Trend": st.column_config.LineChartColumn(f"Trend (Jan {stat_year})")
        }, use_container_width=True)

with tab2:
    st.subheader("Yearly Trend Visualization")
    c_a, c_b = st.columns([3, 1])
    with c_a:
        df_full['YYYY-MM'] = df_full['time'].dt.to_period('M').astype(str)
        unique_months = sorted(df_full['YYYY-MM'].unique())
        start_month, end_month = st.select_slider("Time Range", options=unique_months, value=(unique_months[0], unique_months[-1]))
    with c_b:
        st.write("")
        normalize = st.checkbox("Normalize (0-1)", value=False)
        selected_cols = st.multiselect("Variables:", utils.WEATHER_VARS, default=["temperature_2m"])

    start_date = pd.to_datetime(start_month)
    end_date = (pd.to_datetime(end_month) + pd.offsets.MonthEnd(0)) + pd.Timedelta(days=1)
    mask = (df_full['time'] >= start_date) & (df_full['time'] <= end_date)
    df_plot = df_full.loc[mask].copy()

    if normalize:
        for col in selected_cols:
            mx, mn = df_plot[col].max(), df_plot[col].min()
            if mx != mn: df_plot[col] = (df_plot[col] - mn) / (mx - mn)

    fig = go.Figure()
    for col in selected_cols:
        fig.add_trace(go.Scatter(x=df_plot['time'], y=df_plot[col], mode='lines', name=col))
    
    fig.update_layout(height=500, template="plotly_white", xaxis_title="Time", title=f"Trends in {local_area}")
    st.plotly_chart(fig, use_container_width=True)