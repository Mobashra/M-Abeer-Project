import streamlit as st
import plotly.graph_objects as go
import utils

st.title("🔗 Correlation Analysis")
df_prod = utils.load_elhub_data(year_filter=2021)
area = st.selectbox("Area", df_prod['price_area'].unique())
group = st.selectbox("Group", df_prod['production_group'].unique())

coords = utils.CITIES.get(area, utils.CITIES["NO1"])
df_weather = utils.fetch_weather_api(coords["latitude"], coords["longitude"], "2021-01-01", "2021-12-31")
weather_var = st.selectbox("Weather Var", utils.WEATHER_VARS)

# Align Data
ts_p = df_prod[(df_prod['price_area']==area) & (df_prod['production_group']==group)].set_index('date')['production_mwh'].asfreq('h').interpolate()
ts_w = df_weather.set_index('time')[weather_var].asfreq('h').interpolate()
common = ts_p.index.intersection(ts_w.index)

# Sliding Window
window = st.slider("Window (Hours)", 24, 720, 168)
corr = ts_p.loc[common].rolling(window).corr(ts_w.loc[common])

fig = go.Figure()
fig.add_trace(go.Scatter(x=corr.index, y=corr, name="Correlation"))
fig.add_hline(y=0, line_dash="dash")
st.plotly_chart(fig, use_container_width=True)