import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import utils
import analysis_functions as af

st.set_page_config(page_title="Signal Processing", layout="wide")

utils.check_session_state()
utils.render_sidebar()

st.title("📡 Signal Decomposition (STL)")

c1, c2, c3, c4 = st.columns(4)
with c1: year = st.selectbox("Year", [2021, 2022, 2023])
with c2: dtype = st.radio("Type", ["Production", "Consumption"], horizontal=True)

df = utils.load_yearly_data(dtype, year)
if df.empty: st.stop()

df = df[df['price_area'] == st.session_state["selected_price_area"]]
groups = sorted(df['group'].unique())

with c3: group = st.selectbox("Group", groups)
with c4: 
    if st.button("Run Analysis", type="primary"):
        st.session_state.run_stl = True

if "run_stl" in st.session_state:
    series = df[df['group'] == group].set_index('date')['mwh'].asfreq('h').interpolate()
    
    with st.spinner("Performing STL..."):
        res = af.compute_stl(series, period=168)
        
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, subplot_titles=["Original", "Trend", "Seasonal", "Residual"])
        fig.add_trace(go.Scatter(x=res.observed.index, y=res.observed, name="Observed"), row=1, col=1)
        fig.add_trace(go.Scatter(x=res.trend.index, y=res.trend, name="Trend"), row=2, col=1)
        fig.add_trace(go.Scatter(x=res.seasonal.index, y=res.seasonal, name="Seasonal"), row=3, col=1)
        fig.add_trace(go.Scatter(x=res.resid.index, y=res.resid, name="Resid"), row=4, col=1)
        fig.update_layout(height=800, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)