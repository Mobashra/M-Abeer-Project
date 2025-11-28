import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import utils

st.set_page_config(page_title="Correlation Analysis", layout="wide")

# 1. STYLING
utils.render_sidebar()

st.title("Sliding Window Correlation")
st.markdown("Analyze how **Weather** drivers impact **Energy** patterns over time.")

# --- ACTIVE AREA CONTEXT ---
current_context_area = st.session_state.get("selected_price_area", "NO1")
st.info(f"📍 **Currently Viewing:** Price Area **{current_context_area}**")

# 2. STATE & DEFAULTS
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

# 3. GLOBAL CONTROLS
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    
    # Column 1: Region Selection
    with c1:
        area_list = sorted(utils.CITIES.keys())
        try:
            current_idx = area_list.index(st.session_state["selected_price_area"])
        except ValueError:
            current_idx = 0 
        
        # Added key to prevent duplicate ID errors
        selected_area = st.selectbox("Region", area_list, index=current_idx, key="corr_region_selector")
        
        if selected_area != st.session_state["selected_price_area"]:
            st.session_state["selected_price_area"] = selected_area
            city = utils.CITIES[selected_area]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()

    # Column 2: Year Selection
    with c2:
        selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

    # Column 3: Energy Type (Moved here for better layout)
    with c3:
        data_type = st.radio("Energy Type", ["Production", "Consumption"], horizontal=True)

    # Column 4: Weather Variable
    with c4:
        selected_weather = st.selectbox("Weather Variable", utils.WEATHER_VARS, index=2) # Default Wind Speed

st.divider()

# 4. LOAD ENERGY DATA
with st.spinner(f"Loading {data_type} data for {selected_year}..."):
    df_energy = utils.load_yearly_data(data_type, selected_year)

if df_energy.empty:
    st.error(f"No energy data found for {selected_year}.")
    st.stop()

# Filter by Selected Area
df_energy_area = df_energy[df_energy['price_area'] == selected_area]
available_groups = sorted(df_energy_area['group'].unique())

# 5. ANALYSIS CONFIGURATION
st.subheader("Analysis Configuration")
col_grp, col_win, col_lag = st.columns([1, 1, 1])

with col_grp:
    selected_group = st.selectbox(f"Select {data_type} Group", available_groups, index=0)

with col_win:
    window_size = st.slider("Window Size (Hours)", 24, 720, 168)

with col_lag:
    lag = st.number_input("Lag (Hours)", -48, 48, 0, help="Positive = Weather leads Energy")

# 6. DATA PROCESSING
with st.spinner("Aligning time series..."):
    # A. Energy Series
    energy_series = df_energy_area[df_energy_area['group'] == selected_group].set_index('date')['mwh']
    energy_series = energy_series.sort_index().asfreq('h').interpolate(method='time')

    # B. Weather Data
    coords = st.session_state["selected_coords"]
    df_weather = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{selected_year}-01-01", f"{selected_year}-12-31")
    
    if df_weather.empty:
        st.error("No weather data found.")
        st.stop()

    # C. Align Weather Index
    if df_weather['time'].dt.tz is None:
        df_weather['time'] = pd.to_datetime(df_weather['time'], utc=True)
        
    df_weather['time'] = df_weather['time'].dt.tz_convert("Europe/Oslo")
    
    weather_series = df_weather.set_index('time')[selected_weather]
    weather_series = weather_series.sort_index().asfreq('h').interpolate(method='time')

    # D. Intersection
    common_idx = energy_series.index.intersection(weather_series.index)
    
    if len(common_idx) < 24:
        st.error(f"Data mismatch: Energy and Weather data do not overlap sufficiently for {selected_year}.")
        st.stop()
        
    ts_energy = energy_series.loc[common_idx]
    ts_weather = weather_series.loc[common_idx]

# 7. CALCULATIONS & PLOTS
ts_weather_shifted = ts_weather.shift(lag)
rolling_corr = ts_energy.rolling(window=window_size).corr(ts_weather_shifted)

# Statistics Row
st.markdown("### Results")

# Fixed: Defined columns INSIDE the container so the border wraps them
with st.container(border=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avg Correlation", f"{rolling_corr.mean():.2f}")
    m2.metric("Max Correlation", f"{rolling_corr.max():.2f}")
    m3.metric("Min Correlation", f"{rolling_corr.min():.2f}")
    m4.metric("Data Points", len(common_idx))

# Plot 1: Correlation Dynamics
st.subheader("Correlation Dynamics")
st.markdown(f"Sliding window correlation (window={window_size} hrs) with lag of {lag} hours.")






fig_corr = go.Figure()
fig_corr.add_trace(go.Scatter(x=rolling_corr.index, y=rolling_corr, mode='lines', name='Correlation', line=dict(color='#636EFA', width=2)))
fig_corr.add_hline(y=0, line_dash="dash", line_color="gray")
fig_corr.update_layout(
    height=400, 
    template="plotly_white", 
    yaxis=dict(title="Correlation (-1 to 1)", range=[-1.1, 1.1]),
    margin=dict(l=40, r=40, t=40, b=40)
)
st.plotly_chart(fig_corr, use_container_width=True)

# Plot 2: Dual Axis Comparison
st.subheader("Visual Comparison")
st.markdown(f"Weather Variable vs {data_type} Group over Time") # Fixed typo 'Varibale'






fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

fig_dual.add_trace(
    go.Scatter(x=ts_energy.index, y=ts_energy, name=f"Energy ({selected_group})", line=dict(color='#EF553B', width=1.5)),
    secondary_y=False
)
fig_dual.add_trace(
    go.Scatter(x=ts_weather.index, y=ts_weather, name=f"Weather ({selected_weather})", line=dict(color='#00CC96', width=1.5, dash='dot')),
    secondary_y=True
)

fig_dual.update_layout(
    height=500, 
    template="plotly_white", 
    legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
    margin=dict(l=40, r=40, t=40, b=40)
)
fig_dual.update_yaxes(title_text="Energy (MWh)", secondary_y=False)
fig_dual.update_yaxes(title_text=selected_weather, secondary_y=True)

st.plotly_chart(fig_dual, use_container_width=True)