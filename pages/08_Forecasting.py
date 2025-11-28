import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
import analysis_functions as af
from datetime import date, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX

st.set_page_config(page_title="Forecasting", layout="wide")
utils.render_sidebar()

st.title("SARIMAX Energy Forecasting")
st.markdown("Forecast future energy patterns using **SARIMAX** with dynamic **Weather Exogenous Variables**.")

# --- 1. INTELLIGENT DEFAULT LOGIC ---
# Read Global State (if exists), otherwise Default to NO1.
# This does NOT set the global variable, so Snow Drift/Anomalies will still warn the user.
global_area = st.session_state.get("selected_price_area")
default_area = global_area if global_area else "NO1"

# --- 2. CONTROLS ---
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown("###### Energy Group")
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True, label_visibility="collapsed")
        
        # Local Area Selector
        area_list = sorted(utils.CITIES.keys())
        try:
            start_index = area_list.index(default_area)
        except ValueError:
            start_index = 0
            
        # LOCAL VARIABLE ONLY
        local_area = st.selectbox("Region", area_list, index=start_index)

    with c2:
        st.markdown("###### Training Start Time")
        min_date, max_date = date(2021, 1, 1), date(2024, 12, 31)
        train_start = st.date_input("Start", value=min_date, min_value=min_date, max_value=max_date, label_visibility="collapsed")
        
    with c3:
        st.markdown("######  Training End Time")
        default_end = min_date + timedelta(days=30)
        train_end = st.date_input("End", value=default_end, min_value=min_date, max_value=max_date, label_visibility="collapsed")

    with c4:
        st.markdown("###### Forecast Horizon (Hours)")
        horizon = st.number_input("Horizon", min_value=1, max_value=168, value=48, label_visibility="collapsed")
    
    # Derive Local Coords for Weather Data
    city_data = utils.CITIES[local_area]
    local_lat, local_lon = city_data["lat"], city_data["lon"]
    
    st.info(f"**Forecast Region:** {local_area} (Weather Source: Lat {local_lat:.4f}, Lon {local_lon:.4f})")
    
    # Secondary Controls
    c5, c6 = st.columns(2)
    start_y, end_y = train_start.year, train_end.year
    
    with st.spinner(f"Loading data..."):
        if start_y != end_y:
            df1 = utils.load_yearly_data(data_type, start_y)
            df2 = utils.load_yearly_data(data_type, end_y)
            df_energy = pd.concat([df1, df2]).drop_duplicates(subset=['date'])
        else:
            df_energy = utils.load_yearly_data(data_type, start_y)
            
    if df_energy.empty: st.error("No energy data."); st.stop()
    
    # Filter by LOCAL area
    df_energy = df_energy[df_energy['price_area'] == local_area]
    groups = sorted(df_energy['group'].unique())
    
    with c5: selected_group = st.selectbox("Energy Group", groups, index=0)
    with c6: exog_vars = st.multiselect("Exogenous Features", utils.WEATHER_VARS, default=["temperature_2m"])

# --- 3. MODEL PARAMS ---
with st.expander(" SARIMAX Model Parameters", expanded=False):
    c_p, c_d, c_q, c_s = st.columns(4)
    with c_p: p = st.number_input("AR (p)", 0, 5, 1); P = st.number_input("Seasonal AR (P)", 0, 2, 1)
    with c_d: d = st.number_input("Diff (d)", 0, 2, 1); D = st.number_input("Seasonal Diff (D)", 0, 1, 1)
    with c_q: q = st.number_input("MA (q)", 0, 5, 1); Q = st.number_input("Seasonal MA (Q)", 0, 2, 1)
    with c_s: s = st.number_input("Seasonality (s)", 0, 168, 24)

st.divider()

if st.button("Train & Forecast", type="primary", use_container_width=True):
    # A. Target
    ts_train = df_energy[
        (df_energy['group'] == selected_group) & 
        (df_energy['date'].dt.date >= train_start) & 
        (df_energy['date'].dt.date <= train_end)
    ].set_index('date')['mwh'].sort_index().asfreq('h').interpolate()
    
    if len(ts_train) < 24: st.error("Not enough training data."); st.stop()
        
    # B. Exogenous (Using Local Coords)
    fetch_end = train_end + timedelta(hours=horizon + 24)
    with st.spinner("Fetching weather data..."):
        df_w = utils.fetch_weather_api(local_lat, local_lon, train_start.strftime("%Y-%m-%d"), fetch_end.strftime("%Y-%m-%d"))
        
        exog_train, exog_fut = None, None
        if exog_vars and not df_w.empty:
            if df_w['time'].dt.tz is None: df_w['time'] = pd.to_datetime(df_w['time'], utc=True)
            df_w['time'] = df_w['time'].dt.tz_convert("Europe/Oslo")
            df_w = df_w.drop_duplicates(subset=['time'])
            w_full = df_w.set_index('time')[exog_vars].asfreq('h').interpolate()
            
            exog_train = w_full.reindex(ts_train.index).fillna(method='ffill').fillna(method='bfill')
            fut_idx = pd.date_range(start=ts_train.index[-1] + timedelta(hours=1), periods=horizon, freq='h')
            exog_fut = w_full.reindex(fut_idx).fillna(method='ffill').fillna(method='bfill')

    # C. Train
    with st.spinner("Training Model..."):
        try:
            model, res = af.train_sarimax(
                ts_train, exog=exog_train, order=(p,d,q), seasonal_order=(P,D,Q,s),
                forecast_steps=horizon, exog_forecast=exog_fut
            )
            pred, conf = res.predicted_mean, res.conf_int()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_train.index, y=ts_train, name="Train", line=dict(color='gray')))
            fig.add_trace(go.Scatter(x=pred.index, y=pred, name="Forecast", line=dict(color='red')))
            fig.add_trace(go.Scatter(x=conf.index, y=conf.iloc[:,1], line=dict(width=0), fill='tonexty', fillcolor='rgba(255,0,0,0.2)', name="Conf"))
            fig.update_layout(title=f"Forecast: {selected_group}", template="plotly_white", height=500)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e: st.error(f"Error: {e}")