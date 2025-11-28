import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
import analysis_functions as af
from datetime import date, timedelta
from statsmodels.tsa.statespace.sarimax import SARIMAX

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Forecasting", layout="wide")

# 1. STYLING
utils.render_sidebar()

st.title("📈 SARIMAX Energy Forecasting")
st.markdown("Forecast future energy patterns using **SARIMAX** with dynamic **Weather Exogenous Variables**.")

# 2. STATE MANAGEMENT & LOCAL FALLBACK
# If no global area is selected, initialize with NO1 default
if "selected_price_area" not in st.session_state or not st.session_state["selected_price_area"]:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

# 3. CONTROLS (Dashboard)
with st.container():
    # Row 1: Core Selection
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown("###### 1. Data Source")
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True, label_visibility="collapsed")

        # Local Area Selector (Fallback)
        area_list = sorted(utils.CITIES.keys())
        current_idx = area_list.index(current_area) if current_area in area_list else 0
        selected_area = st.selectbox("Region", area_list, index=current_idx)
        
        # Update global state if changed locally
        if selected_area != current_area:
            st.session_state["selected_price_area"] = selected_area
            city = utils.CITIES[selected_area]
            st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}
            st.rerun()
            current_area = selected_area # Update current_area for immediate use

    with c2:
        st.markdown("###### 2. Training Start Time")
        # Default: Jan 1, 2021 (Start of data)
        min_full_date = date(2021, 1, 1)
        max_full_date = date(2024, 12, 31)

        train_start_date = st.date_input(
            "Start", 
            value=min_full_date, # Default 2021-01-01
            min_value=min_full_date, 
            max_value=max_full_date,
            label_visibility="collapsed"
        )
        
    with c3:
        st.markdown("###### 3. Training End Time")
        # Default: Feb 1, 2021 (1 month later)
        default_end = min_full_date + timedelta(days=30)
        
        train_end_date = st.date_input(
            "End", 
            value=default_end, # Default 1 month later
            min_value=min_full_date, 
            max_value=max_full_date,
            label_visibility="collapsed"
        )
        
        # Validation
        if train_start_date >= train_end_date:
            st.error("End Time must be after Start Time.")
            st.stop()

    with c4:
        st.markdown("###### 4. Forecast Horizon (Hours)")
        horizon = st.number_input("Horizon", min_value=1, max_value=168, value=48, label_visibility="collapsed")
        
    st.info(f"**Forecast Region:** {current_area} (Weather Source: Lat {coords['lat']:.4f}, Lon {coords['lon']:.4f})")
    
    # --- Row 2: Group & Exogenous ---
    c5, c6 = st.columns(2)

    # Load Data (Needed to populate groups)
    # Load the years spanned by the training range for robust data filtering
    start_y = train_start_date.year
    end_y = train_end_date.year
    
    if start_y != end_y:
        # Load both years and concatenate if the range spans Jan 1st
        with st.spinner(f"Loading data for {start_y} and {end_y}..."):
            df_start = utils.load_yearly_data(data_type, start_y)
            df_end = utils.load_yearly_data(data_type, end_y)
            df_energy = pd.concat([df_start, df_end]).drop_duplicates(subset=['date'])
    else:
        with st.spinner(f"Loading data for {start_y}..."):
            df_energy = utils.load_yearly_data(data_type, start_y)

    if df_energy.empty:
        st.error("No energy data found.")
        st.stop()
        
    # Filter by Area & Groups
    df_energy = df_energy[df_energy['price_area'] == current_area]
    groups = sorted(df_energy['group'].unique())
    
    with c5:
        selected_group = st.selectbox("Energy Group", groups, index=0)
        
    with c6:
        # Bonus: User selects which weather properties to use
        exog_vars = st.multiselect(
            "Exogenous Features", 
            utils.WEATHER_VARS, 
            default=["temperature_2m"]
        )

# --- 4. MODEL HYPERPARAMETERS & EXECUTION ---
with st.expander("⚙️ SARIMAX Model Parameters", expanded=False):
    c_p, c_d, c_q, c_s = st.columns(4)
    with c_p:
        p = st.number_input("AR (p)", 0, 5, 1, help="Auto-Regressive order")
        P = st.number_input("Seasonal AR (P)", 0, 2, 1)
    with c_d:
        d = st.number_input("Diff (d)", 0, 2, 1, help="Integrated (Differencing) order")
        D = st.number_input("Seasonal Diff (D)", 0, 1, 1)
    with c_q:
        q = st.number_input("MA (q)", 0, 5, 1, help="Moving Average order")
        Q = st.number_input("Seasonal MA (Q)", 0, 2, 1)
    with c_s:
        s = st.number_input("Seasonality (s)", 0, 168, 24, help="24=Daily, 168=Weekly")

st.divider()

if st.button("🚀 Train & Forecast", type="primary", use_container_width=True):
    
    # --- A. PREPARE TARGET DATA ---
    ts_train = df_energy[
        (df_energy['group'] == selected_group) & 
        (df_energy['date'].dt.date >= train_start_date) & 
        (df_energy['date'].dt.date <= train_end_date)
    ].set_index('date')['mwh'].sort_index().asfreq('h').interpolate()
    
    if len(ts_train) < 24:
        st.error("Not enough training data selected. Please increase the Timeframe.")
        st.stop()
        
    # --- B. PREPARE EXOGENOUS DATA (BONUS) ---
    fetch_start = train_start_date
    fetch_end = train_end_date + timedelta(hours=horizon + 24) # Buffer for forecast period
    
    with st.spinner("Fetching & aligning weather data..."):
        df_w = utils.fetch_weather_api(
            coords['lat'], coords['lon'], 
            fetch_start.strftime("%Y-%m-%d"), 
            fetch_end.strftime("%Y-%m-%d")
        )
        
        if df_w.empty and exog_vars:
            st.error("Weather data unavailable for selected period.")
            st.stop()
            
        # Timezone handling & alignment
        weather_full, exog_train, exog_fut = None, None, None
        if exog_vars:
            if df_w['time'].dt.tz is None:
                df_w['time'] = pd.to_datetime(df_w['time'], utc=True)
            df_w['time'] = df_w['time'].dt.tz_convert("Europe/Oslo")
            df_w = df_w.drop_duplicates(subset=['time'])
            
            weather_full = df_w.set_index('time')[exog_vars].asfreq('h').interpolate()
            
            # Split into Train / Forecast
            exog_train = weather_full.reindex(ts_train.index).fillna(method='ffill').fillna(method='bfill')
            fut_idx = pd.date_range(start=ts_train.index[-1] + timedelta(hours=1), periods=horizon, freq='h')
            exog_fut = weather_full.reindex(fut_idx).fillna(method='ffill').fillna(method='bfill')

    # --- C. TRAIN MODEL ---
    with st.spinner("Training SARIMAX Model..."):
        try:
            model, res = af.train_sarimax(
                ts_train, 
                exog=exog_train if exog_vars else None,
                order=(p, d, q), 
                seasonal_order=(P, D, Q, s),
                forecast_steps=horizon, 
                exog_forecast=exog_fut if exog_vars else None
            )
            
            # Get Results & Plotting
            pred = res.predicted_mean
            conf = res.conf_int()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_train.index, y=ts_train, name="Training Data", line=dict(color='gray', width=1)))
            fig.add_trace(go.Scatter(x=pred.index, y=pred, name="Forecast", line=dict(color='#d62728', width=2)))
            fig.add_trace(go.Scatter(x=conf.index, y=conf.iloc[:, 1], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(214, 39, 40, 0.2)', name="95% Confidence"))
            
            fig.update_layout(title=f"Forecast: {selected_group} ({horizon}h Horizon)", yaxis_title="MWh", template="plotly_white", height=500)
            
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("📊 View Statistical Summary"):
                st.text(model.summary())
                
        except Exception as e:
            st.error(f"Model Training Failed: {e}")