import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
import analysis_functions as af

st.set_page_config(page_title="Forecasting", page_icon="📈", layout="wide")
st.title("📈 SARIMAX Forecasting")

# --- SETUP ---
if "selected_price_area" not in st.session_state: st.session_state["selected_price_area"] = "NO1"
coords = st.session_state["selected_coords"]

c1, c2 = st.columns(2)
year = c1.selectbox("Training Year", [2022, 2023, 2024])
group = c2.text_input("Energy Group (Exact Name)", "hydro") # Flexible input

# --- MODEL PARAMS ---
with st.sidebar:
    st.header("ARIMA Order")
    p = st.number_input("p", 0, 5, 1)
    d = st.number_input("d", 0, 2, 1)
    q = st.number_input("q", 0, 5, 1)
    st.header("Seasonal Order")
    P = st.number_input("P", 0, 2, 1)
    D = st.number_input("D", 0, 1, 1)
    Q = st.number_input("Q", 0, 2, 1)
    s = st.number_input("s (Season)", 0, 168, 24)
    
    horizon = st.slider("Forecast Horizon (Hours)", 24, 168, 48)
    exog_vars = st.multiselect("Exogenous Vars", utils.WEATHER_VARS, default=["temperature_2m"])

# --- RUN ---
if st.button("Train & Forecast"):
    with st.spinner("Preparing Data..."):
        # 1. Load Energy
        df_e = utils.load_yearly_data("Production", year) # Defaulting to Prod
        if df_e.empty: st.error("No Energy Data"); st.stop()
        
        # Filter
        ts_train = df_e[(df_e['price_area'] == st.session_state['selected_price_area']) & (df_e['group'] == group)]
        ts_train = ts_train.set_index('date')['mwh'].sort_index().asfreq('h').interpolate()
        
        # 2. Load Weather (Exog)
        # We need weather for Training Period AND Forecast Horizon
        start_w = ts_train.index.min()
        end_w = ts_train.index.max() + pd.Timedelta(hours=horizon + 24)
        
        df_w = utils.fetch_weather_api(coords['lat'], coords['lon'], start_w.strftime("%Y-%m-%d"), end_w.strftime("%Y-%m-%d"))
        df_w['time'] = pd.to_datetime(df_w['time'], utc=True).dt.tz_convert("Europe/Oslo")
        ts_w = df_w.set_index('time')[exog_vars].asfreq('h').interpolate()
        
        # Align Exog
        exog_train = ts_w.loc[ts_train.index]
        future_idx = pd.date_range(ts_train.index[-1] + pd.Timedelta(hours=1), periods=horizon, freq='h')
        exog_future = ts_w.reindex(future_idx).fillna(method='ffill')

    with st.spinner("Fitting SARIMAX..."):
        try:
            model, forecast_res = af.train_sarimax(
                ts_train, exog=exog_train, 
                order=(p,d,q), seasonal_order=(P,D,Q,s), 
                forecast_steps=horizon, exog_forecast=exog_future
            )
            
            # Plot
            pred = forecast_res.predicted_mean
            conf = forecast_res.conf_int()
            
            fig = go.Figure()
            # History (Last 7 days only for clarity)
            fig.add_trace(go.Scatter(x=ts_train.index[-168:], y=ts_train[-168:], name="History"))
            # Forecast
            fig.add_trace(go.Scatter(x=pred.index, y=pred, name="Forecast", line=dict(color='red')))
            # Confidence
            fig.add_trace(go.Scatter(x=conf.index, y=conf.iloc[:,0], mode='lines', line=dict(width=0), showlegend=False))
            fig.add_trace(go.Scatter(x=conf.index, y=conf.iloc[:,1], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(255,0,0,0.2)', name="95% Conf"))
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Modeling Failed: {e}")