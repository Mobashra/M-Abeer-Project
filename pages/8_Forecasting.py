import streamlit as st
import utils
from statsmodels.tsa.statespace.sarimax import SARIMAX
import plotly.graph_objects as go

st.title("🔮 SARIMAX Forecasting")
df = utils.load_elhub_data(year_filter=2021)
area = st.selectbox("Area", df['price_area'].unique())
group = st.selectbox("Group", df['production_group'].unique())

ts = df[(df['price_area']==area) & (df['production_group']==group)].set_index('date')['production_mwh'].asfreq('h').interpolate().iloc[-500:]

if st.button("Train & Forecast (48h)"):
    with st.spinner("Training..."):
        model = SARIMAX(ts, order=(1,1,1), seasonal_order=(1,1,1,24))
        res = model.fit(disp=False)
        fc = res.get_forecast(steps=48)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ts.index, y=ts, name="History"))
        fig.add_trace(go.Scatter(x=fc.predicted_mean.index, y=fc.predicted_mean, name="Forecast"))
        st.plotly_chart(fig, use_container_width=True)