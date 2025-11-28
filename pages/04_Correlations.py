import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils

st.set_page_config(page_title="Correlations", layout="wide")

utils.check_session_state()
utils.render_sidebar()

st.title("🔗 Weather-Energy Correlations")

# 1. CONTROLS
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    with c1: year = st.selectbox("Year", [2021, 2022, 2023])
    with c2: dtype = st.radio("Energy Type", ["Production", "Consumption"], horizontal=True)
    with c3: w_var = st.selectbox("Weather Driver", utils.WEATHER_VARS, index=2) # Wind Speed
    
# 2. DATA PREP
with st.spinner("Aligning datasets..."):
    # Load Energy
    df_e = utils.load_yearly_data(dtype, year)
    if df_e.empty: st.error("No Energy Data"); st.stop()
    
    # Filter Region
    df_e = df_e[df_e['price_area'] == st.session_state["selected_price_area"]]
    groups = sorted(df_e['group'].unique())
    
    with c4: selected_group = st.selectbox("Energy Group", groups)
    
    # Align Series
    ts_e = df_e[df_e['group'] == selected_group].set_index('date')['mwh'].sort_index().asfreq('h').interpolate()
    
    coords = st.session_state["selected_coords"]
    df_w = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{year}-01-01", f"{year}-12-31")
    
    if not df_w.empty:
        df_w['time'] = pd.to_datetime(df_w['time'], utc=True).dt.tz_convert("Europe/Oslo")
        ts_w = df_w.set_index('time')[w_var].asfreq('h').interpolate()
        
        # Intersection
        idx = ts_e.index.intersection(ts_w.index)
        ts_e, ts_w = ts_e.loc[idx], ts_w.loc[idx]
    else:
        st.stop()

# 3. PARAMS
with st.expander("⚙️ Correlation Parameters", expanded=False):
    c_a, c_b = st.columns(2)
    window = c_a.slider("Rolling Window (Hours)", 24, 720, 168)
    lag = c_b.number_input("Lag (Hours)", -24, 24, 0)

# 4. PLOT
st.divider()
ts_w_shifted = ts_w.shift(lag)
corr = ts_e.rolling(window=window).corr(ts_w_shifted)

c_m, c_p = st.columns([1, 3])
c_m.metric("Avg Correlation", f"{corr.mean():.2f}")
c_m.metric("Max Correlation", f"{corr.max():.2f}")

fig = go.Figure()
fig.add_trace(go.Scatter(x=corr.index, y=corr, fill='tozeroy', name="Corr"))
fig.update_layout(title=f"Rolling Correlation ({selected_group} vs {w_var})", yaxis_range=[-1, 1], height=400)
c_p.plotly_chart(fig, use_container_width=True)