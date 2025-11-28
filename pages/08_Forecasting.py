import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
import analysis_functions as af

st.set_page_config(page_title="Forecasting", layout="wide")

utils.check_session_state()
utils.render_sidebar()

st.title("📈 SARIMAX Forecasting")

c1, c2, c3 = st.columns([1, 1, 2])
with c1: year = st.selectbox("Training Year", [2022, 2023])
with c2: horizon = st.number_input("Forecast Hours", 24, 168, 48)

df_e = utils.load_yearly_data("Production", year)
if df_e.empty: st.stop()
df_e = df_e[df_e['price_area'] == st.session_state["selected_price_area"]]
groups = sorted(df_e['group'].unique())

with c3: group = st.selectbox("Energy Group", groups)

if st.button("Train & Forecast", type="primary"):
    with st.spinner("Training Model..."):
        ts_train = df_e[df_e['group'] == group].set_index('date')['mwh'].asfreq('h').interpolate()
        
        # Safe Exogenous Fetch
        coords = st.session_state["selected_coords"]
        start_w = ts_train.index.min()
        end_w = ts_train.index.max() + pd.Timedelta(hours=horizon + 24)
        
        df_w = utils.fetch_weather_api(coords['lat'], coords['lon'], start_w.strftime("%Y-%m-%d"), end_w.strftime("%Y-%m-%d"))
        
        if not df_w.empty:
            # Drop duplicates to handle DST
            df_w = df_w.drop_duplicates(subset=['time'])
            
            # Localize manually if naive
            if df_w['time'].dt.tz is None:
                df_w['time'] = df_w['time'].dt.tz_localize("Europe/Oslo", ambiguous='NaT', nonexistent='shift_forward')
            else:
                df_w['time'] = df_w['time'].dt.tz_convert("Europe/Oslo")
                
            ts_w = df_w.set_index('time')['temperature_2m'].asfreq('h').interpolate()
            exog_train = ts_w.reindex(ts_train.index).fillna(method='ffill').fillna(method='bfill')
            
            # Future Exog
            fut_idx = pd.date_range(ts_train.index[-1] + pd.Timedelta(hours=1), periods=horizon, freq='h')
            exog_fut = ts_w.reindex(fut_idx).fillna(method='ffill').fillna(method='bfill')
            
            try:
                model, res = af.train_sarimax(ts_train, exog=exog_train, order=(1,1,1), forecast_steps=horizon, exog_forecast=exog_fut)
                
                pred = res.predicted_mean
                conf = res.conf_int()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=ts_train.index[-168:], y=ts_train[-168:], name="History"))
                fig.add_trace(go.Scatter(x=pred.index, y=pred, name="Forecast", line=dict(color='red')))
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Model Error: {e}")