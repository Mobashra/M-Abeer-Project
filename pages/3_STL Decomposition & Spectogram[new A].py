import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import utils
import analysis_functions as af

st.title("Elhub Analysis: STL & Spectrogram")

if "selected_price_area" not in st.session_state:
    st.warning("Please select a price area on the Map or Elhub Data page.")
    st.stop()

selected_area = st.session_state["selected_price_area"]
st.subheader(f"Analyzing: {selected_area} (2021)")

# Load 2021 Data
df = utils.load_elhub_data(year_filter=2021)
df_area = df[df['price_area'] == selected_area].copy()

if df_area.empty: st.stop()

prod_groups = sorted(df_area["production_group"].unique())
selected_group = st.selectbox("Production Group:", prod_groups)

# Prepare Series
mask = df_area["production_group"] == selected_group
series = df_area[mask].groupby("date")["production_mwh"].sum().asfreq("h").interpolate(method="time")

tab1, tab2 = st.tabs(["STL Decomposition", "Spectrogram"])

with tab1:
    res = af.compute_stl(series)
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, subplot_titles=("Original", "Trend", "Seasonal", "Resid"))
    fig.add_trace(go.Scatter(x=res.observed.index, y=res.observed), row=1, col=1)
    fig.add_trace(go.Scatter(x=res.trend.index, y=res.trend), row=2, col=1)
    fig.add_trace(go.Scatter(x=res.seasonal.index, y=res.seasonal), row=3, col=1)
    fig.add_trace(go.Scatter(x=res.resid.index, y=res.resid), row=4, col=1)
    fig.update_layout(height=800, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    f, t, Sxx = af.compute_spectrogram(series)
    fig = go.Figure(data=go.Heatmap(z=Sxx, x=t, y=f, colorscale="Viridis"))
    fig.update_layout(title="Spectrogram", yaxis_title="Freq (cycles/hour)", yaxis_range=[0, 0.1])
    st.plotly_chart(fig, use_container_width=True)