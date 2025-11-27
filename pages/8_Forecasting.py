import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
import analysis_functions as af

st.set_page_config(page_title="SARIMAX Forecasting", layout="wide")
st.title("📈 Energy Forecasting (SARIMAX)")

# --- 1. GLOBAL SETTINGS ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    default = utils.CITIES["NO1"]
    st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}

current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

st.info(f"**Forecast Region:** {current_area} ({coords['lat']:.2f}, {coords['lon']:.2f})")

# --- 2. DATA CONFIGURATION ---
c1, c2, c3 = st.columns(3)

with c1:
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

# Load Data (Cached)
with st.spinner(f"Loading {selected_year} data..."):
    df_energy = utils.load_yearly_data(data_type, selected_year)

if df_energy.empty:
    st.error(f"No data found for {selected_year}.")
    st.stop()

# Filter Area
df_energy = df_energy[df_energy['price_area'] == current_area]
groups = sorted(df_energy['group'].unique())

with c2:
    selected_group = st.selectbox("Select Group", groups, index=0)

with c3:
    # Exogenous Variables (Bonus)
    exog_vars = st.multiselect("Exogenous Variables (Weather)", utils.WEATHER_VARS, default=["temperature_2m"])

# --- 3. FORECAST SETTINGS ---
st.subheader("Model Configuration")
with st.expander("⚙️ SARIMAX Parameters", expanded=True):
    col_p, col_d, col_q, col_s = st.columns(4)
    with col_p:
        p = st.number_input("AR (p)", 0, 5, 1, help="Auto-Regressive order")
        P = st.number_input("Seasonal AR (P)", 0, 2, 1)
    with col_d:
        d = st.number_input("Diff (d)", 0, 2, 1, help="Integrated (Differencing) order")
        D = st.number_input("Seasonal Diff (D)", 0, 1, 1)
    with col_q:
        q = st.number_input("MA (q)", 0, 5, 1, help="Moving Average order")
        Q = st.number_input("Seasonal MA (Q)", 0, 2, 1)
    with col_s:
        s = st.number_input("Seasonality (s)", 0, 168, 24, help="24=Daily, 168=Weekly")
        horizon = st.number_input("Forecast Horizon (Hours)", 1, 168, 48)

# --- 4. TRAINING WINDOW ---
st.markdown("#### Training Data Selection")
# We let the user pick a date range within the selected year to train on
min_date = df_energy['date'].min()
max_date = df_energy['date'].max()

# Default: Train on last 2 weeks of available data (for speed)
default_start = max_date - pd.Timedelta(days=14)
train_range = st.slider(
    "Select Training Period",
    min_value=min_date.to_pydatetime(),
    max_value=max_date.to_pydatetime(),
    value=(default_start.to_pydatetime(), max_date.to_pydatetime()),
    format="MM-DD"
)

# --- 5. EXECUTION ---
if st.button("🚀 Train Model & Forecast"):
    
    # A. Prepare Energy Data (Target)
    mask = (df_energy['group'] == selected_group) & \
           (df_energy['date'] >= pd.Timestamp(train_range[0]).tz_localize("Europe/Oslo")) & \
           (df_energy['date'] <= pd.Timestamp(train_range[1]).tz_localize("Europe/Oslo"))
           
    y_train = df_energy[mask].set_index('date')['mwh'].sort_index().asfreq('h').interpolate()
    
    if len(y_train) < 24:
        st.error("Not enough training data. Please select a wider range.")
        st.stop()

    # B. Prepare Weather Data (Exogenous)
    # We need weather for Training Period + Forecast Period
    fetch_start = train_range[0].strftime("%Y-%m-%d")
    # We need 'horizon' hours AFTER the training end date
    future_end_date = train_range[1] + pd.Timedelta(hours=horizon + 24) # Buffer
    fetch_end = future_end_date.strftime("%Y-%m-%d")
    
    with st.spinner("Fetching weather data..."):
        df_weather = utils.fetch_weather_api(coords['lat'], coords['lon'], fetch_start, fetch_end)
    
    if df_weather.empty:
        st.error("Weather data unavailable.")
        st.stop()
        
    # Align Weather Index
    df_weather['time'] = pd.to_datetime(df_weather['time'], utc=True).dt.tz_convert("Europe/Oslo")
    weather_series = df_weather.set_index('time').asfreq('h').interpolate()
    
    # Split Exog into Train and Future
    # Align with y_train index
    exog_train = weather_series.loc[y_train.index, exog_vars] if exog_vars else None
    
    # Create Future Index for Exog
    future_index = pd.date_range(start=y_train.index[-1] + pd.Timedelta(hours=1), periods=horizon, freq='h')
    
    # Get future weather (We use actual historical weather as our "forecast" of weather)
    # Use .reindex method to handle potential missing hours safely
    exog_future = weather_series.reindex(future_index)[exog_vars] if exog_vars else None
    
    # C. Train & Forecast
    try:
        with st.spinner("Fitting SARIMAX model... (This may take a moment)"):
            model, forecast_res = af.train_sarimax(
                y_train, 
                exog=exog_train,
                order=(p, d, q), 
                seasonal_order=(P, D, Q, s),
                forecast_steps=horizon,
                exog_forecast=exog_future
            )
            
        # D. Visualization
        pred_mean = forecast_res.predicted_mean
        conf_int = forecast_res.conf_int()
        
        fig = go.Figure()
        
        # 1. Training Data
        fig.add_trace(go.Scatter(
            x=y_train.index, y=y_train, 
            name="Historical Data", 
            line=dict(color='gray')
        ))
        
        # 2. Forecast
        fig.add_trace(go.Scatter(
            x=pred_mean.index, y=pred_mean, 
            name="Forecast", 
            line=dict(color='red', width=2)
        ))
        
        # 3. Confidence Interval (Shaded Area)
        fig.add_trace(go.Scatter(
            x=conf_int.index, y=conf_int.iloc[:, 0], 
            mode='lines', line=dict(width=0), showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=conf_int.index, y=conf_int.iloc[:, 1], 
            mode='lines', line=dict(width=0), 
            fill='tonexty', fillcolor='rgba(255, 0, 0, 0.2)', 
            name="95% Confidence"
        ))
        
        fig.update_layout(
            title=f"SARIMAX Forecast: {selected_group} ({horizon} Hours Ahead)",
            xaxis_title="Date",
            yaxis_title="MWh",
            template="plotly_white",
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # E. Model Summary
        with st.expander("View Statistical Summary"):
            st.text(model.summary())

    except Exception as e:
        st.error(f"Modeling failed: {e}")
        st.info("Tip: Try reducing the training range or simplifying the parameters (e.g., set s=0).")