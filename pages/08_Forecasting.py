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

# 1. SAFETY & STYLING
utils.check_session_state()
utils.render_sidebar()

st.title("📈 SARIMAX Energy Forecasting")
st.markdown("Forecast future energy patterns using **SARIMAX** with dynamic **Weather Exogenous Variables**.")

# 2. GLOBAL CONTEXT
current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

with st.container(border=True):
    c1, c2 = st.columns([1, 3])
    with c1:
        st.info(f"**Region:** {current_area}")
    with c2:
        st.info(f"**Weather Source:** Lat {coords['lat']:.4f}, Lon {coords['lon']:.4f}")

# ======================================================
# 3. CONTROLS (Dashboard)
# ======================================================
with st.container():
    # Row 1: Core Selection
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown("###### 1. Data Source")
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True, label_visibility="collapsed")
        
    with c2:
        st.markdown("###### 2. Base Year")
        # We select a year first to load the base dataset efficiently
        base_year = st.selectbox("Year", [2021, 2022, 2023, 2024], index=2, label_visibility="collapsed")
        
    # Load Data Step (Needed to populate groups)
    with st.spinner(f"Loading {base_year} data..."):
        df_energy = utils.load_yearly_data(data_type, base_year)
    
    if df_energy.empty:
        st.error(f"No data found for {base_year}.")
        st.stop()
        
    # Filter by Area
    df_energy = df_energy[df_energy['price_area'] == current_area]
    groups = sorted(df_energy['group'].unique())
    
    with c3:
        st.markdown("###### 3. Group")
        selected_group = st.selectbox("Group", groups, index=0, label_visibility="collapsed")
        
    with c4:
        st.markdown("###### 4. Horizon (Hours)")
        horizon = st.number_input("Horizon", min_value=1, max_value=168, value=48, label_visibility="collapsed")

    # Row 2: Detailed Parameters
    c5, c6 = st.columns([2, 1])
    
    with c5:
        st.markdown("###### 5. Training Timeframe")
        # Determine min/max dates from loaded data
        min_d = df_energy['date'].min().date()
        max_d = df_energy['date'].max().date()
        
        # Default to last 30 days of the year
        default_start = max_d - timedelta(days=30)
        
        train_range = st.slider(
            "Select Training Range",
            min_value=min_d,
            max_value=max_d,
            value=(default_start, max_d),
            format="DD.MM.YYYY",
            label_visibility="collapsed"
        )
        
    with c6:
        st.markdown("###### 6. Exogenous Variables (Bonus)")
        # Bonus: User selects which weather properties to use
        exog_vars = st.multiselect(
            "Weather Features", 
            utils.WEATHER_VARS, 
            default=["temperature_2m", "wind_speed_10m"],
            label_visibility="collapsed"
        )

# --- 4. MODEL HYPERPARAMETERS ---
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

# ======================================================
# 5. EXECUTION
# ======================================================
st.divider()

if st.button("🚀 Train & Forecast", type="primary", use_container_width=True):
    
    # --- A. PREPARE TARGET DATA ---
    train_start, train_end = train_range
    
    mask = (
        (df_energy['group'] == selected_group) & 
        (df_energy['date'].dt.date >= train_start) & 
        (df_energy['date'].dt.date <= train_end)
    )
    
    ts_train = df_energy[mask].set_index('date')['mwh'].sort_index().asfreq('h').interpolate()
    
    if len(ts_train) < 24:
        st.error("Not enough training data selected. Please increase the Timeframe.")
        st.stop()
        
    # --- B. PREPARE EXOGENOUS DATA (BONUS) ---
    # We need weather for: Training Period + Forecast Horizon
    fetch_start = train_start
    fetch_end = train_end + timedelta(hours=horizon + 24) # Buffer
    
    with st.spinner("Fetching & aligning weather data..."):
        df_w = utils.fetch_weather_api(
            coords['lat'], coords['lon'], 
            fetch_start.strftime("%Y-%m-%d"), 
            fetch_end.strftime("%Y-%m-%d")
        )
        
        if df_w.empty:
            st.error("Weather data unavailable.")
            st.stop()
            
        # 1. Handle Timezone & Duplicates
        if df_w['time'].dt.tz is None:
            df_w['time'] = pd.to_datetime(df_w['time'], utc=True)
        df_w['time'] = df_w['time'].dt.tz_convert("Europe/Oslo")
        df_w = df_w.drop_duplicates(subset=['time'])
        
        # 2. Create Full Series
        weather_full = df_w.set_index('time')[exog_vars].asfreq('h').interpolate()
        
        # 3. Split into Train / Forecast
        # Align exact indices
        exog_train = weather_full.reindex(ts_train.index).fillna(method='ffill').fillna(method='bfill')
        
        # Future Index
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
            
            # Get Results
            pred = res.predicted_mean
            conf = res.conf_int()
            
            # --- D. VISUALIZATION ---
            fig = go.Figure()
            
            # 1. Historical Data
            fig.add_trace(go.Scatter(
                x=ts_train.index, y=ts_train, 
                name="Training Data", 
                line=dict(color='gray', width=1)
            ))
            
            # 2. Forecast
            fig.add_trace(go.Scatter(
                x=pred.index, y=pred, 
                name="Forecast", 
                line=dict(color='#d62728', width=2)
            ))
            
            # 3. Confidence Interval
            fig.add_trace(go.Scatter(
                x=conf.index, y=conf.iloc[:, 0],
                mode='lines', line=dict(width=0), showlegend=False
            ))
            fig.add_trace(go.Scatter(
                x=conf.index, y=conf.iloc[:, 1],
                mode='lines', line=dict(width=0),
                fill='tonexty', fillcolor='rgba(214, 39, 40, 0.2)',
                name="95% Confidence"
            ))
            
            fig.update_layout(
                title=f"Forecast: {selected_group} ({horizon}h Horizon)",
                xaxis_title="Date",
                yaxis_title="MWh",
                template="plotly_white",
                height=500,
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary
            with st.expander("📊 View Statistical Summary"):
                st.text(model.summary())
                
        except Exception as e:
            st.error(f"Model Training Failed: {e}")
            st.caption("Tip: Try simplifying the parameters (e.g., d=0, D=0) or reducing the seasonal period.")