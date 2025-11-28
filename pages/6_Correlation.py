import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import utils

st.set_page_config(page_title="Correlation Analysis", page_icon="🔗", layout="wide")
st.title("🔗 Weather vs Energy Correlation")

if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"
    
coords = st.session_state["selected_coords"]

# --- CONFIG ---
c1, c2, c3 = st.columns(3)
year = c1.selectbox("Year", [2021, 2022, 2023])
data_type = c2.radio("Energy Type", ["Production", "Consumption"])
w_var = c3.selectbox("Weather Variable", utils.WEATHER_VARS, index=2) # Wind speed default

# --- PARAMS ---
with st.sidebar:
    st.header("Sliding Window Params")
    window = st.number_input("Window Size (Hours)", 24, 1000, 168)
    lag = st.number_input("Lag (Hours)", -48, 48, 0, help="Positive = Weather Leads")

# --- DATA PREP ---
with st.spinner("Aligning Time Series..."):
    # 1. Get Energy
    df_e = utils.load_yearly_data(data_type, year)
    if df_e.empty: st.stop()
    df_e = df_e[df_e['price_area'] == st.session_state["selected_price_area"]]
    
    group = st.selectbox("Select Group", df_e['group'].unique())
    ts_e = df_e[df_e['group'] == group].set_index('date')['mwh'].sort_index().asfreq('h').interpolate()
    
    # 2. Get Weather
    df_w = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{year}-01-01", f"{year}-12-31")
    df_w['time'] = pd.to_datetime(df_w['time'], utc=True).dt.tz_convert("Europe/Oslo")
    ts_w = df_w.set_index('time')[w_var].sort_index().asfreq('h').interpolate()
    
    # 3. Align
    idx = ts_e.index.intersection(ts_w.index)
    ts_e, ts_w = ts_e.loc[idx], ts_w.loc[idx]

# --- CALCULATION ---
ts_w_shifted = ts_w.shift(lag)
corr = ts_e.rolling(window=window).corr(ts_w_shifted)

# --- PLOTTING ---
st.subheader("Correlation Dynamics")
st.line_chart(corr)

st.subheader("Dual Axis Comparison")
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=ts_e.index, y=ts_e, name="Energy"), secondary_y=False)
fig.add_trace(go.Scatter(x=ts_w.index, y=ts_w, name="Weather", line=dict(dash='dot')), secondary_y=True)
st.plotly_chart(fig, use_container_width=True)