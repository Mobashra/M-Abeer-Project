import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import utils
import analysis_functions as af

st.set_page_config(page_title="Signal Processing", layout="wide")
utils.render_sidebar()

st.title("Signal Decomposition & Frequency Analysis")

# --- 1. INTELLIGENT DEFAULT LOGIC ---
# Read Global State (if exists), otherwise Default to NO1.
global_area = st.session_state.get("selected_price_area")
default_area = global_area if global_area else "NO1"

# --- 2. CONTROLS ---
with st.container():
    c1, c2, c3 = st.columns(3)
    
    with c1:
        # LOCAL REGION SELECTOR
        area_list = sorted(utils.CITIES.keys())
        try:
            start_index = area_list.index(default_area)
        except ValueError:
            start_index = 0
            
        local_area = st.selectbox("Region", area_list, index=start_index)

    with c2:
        year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)
    with c3:
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True)

st.info(f"📍 **Currently Viewing:** Price Area **{local_area}**")

# --- 3. FETCH DATA ---
with st.spinner("Fetching data..."):
    df = utils.load_yearly_data(data_type, year)

if df.empty: st.error(f"No data for {year}."); st.stop()

# Filter Data using LOCAL AREA
df_area = df[df['price_area'] == local_area]
groups = sorted(df_area['group'].unique())

if not groups: st.warning("No groups available."); st.stop()

selected_group = st.selectbox("Select Energy Group", groups)

# Prepare Time Series
mask = df_area["group"] == selected_group
val_col = 'mwh' if 'mwh' in df_area.columns else 'value'
series = df_area[mask].set_index("date")[val_col].sort_index().asfreq("h").interpolate(method="time")

if series.empty: st.error("Not enough data."); st.stop()

st.divider()

# --- 4. ANALYSIS TABS ---
tab1, tab2 = st.tabs(["📉 STL Decomposition", "〰️ Spectrogram"])

with tab1:
    st.markdown("### Seasonal-Trend Decomposition (LOESS)")
    c_p, c_s, c_t = st.columns(3)
    with c_p: period = st.number_input("Period (Hours)", min_value=2, value=168, step=1)
    with c_s: seasonal = st.number_input("Seasonal (Odd)", min_value=3, value=13, step=2)
    with c_t: trend = st.number_input("Trend (Odd)", min_value=3, value=169, step=2)

    if st.button("Run Decomposition", type="primary"):
        with st.spinner("Decomposing..."):
            try:
                res = af.compute_stl(series, period=period, seasonal=seasonal, trend=trend, robust=True)
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, subplot_titles=("Observed", "Trend", "Seasonal", "Residuals"))
                fig.add_trace(go.Scatter(x=res.observed.index, y=res.observed, name="Observed", line=dict(color='#1f77b4')), row=1, col=1)
                fig.add_trace(go.Scatter(x=res.trend.index, y=res.trend, name="Trend", line=dict(color='#ff7f0e')), row=2, col=1)
                fig.add_trace(go.Scatter(x=res.seasonal.index, y=res.seasonal, name="Seasonal", line=dict(color='#2ca02c')), row=3, col=1)
                fig.add_trace(go.Scatter(x=res.resid.index, y=res.resid, name="Residual", line=dict(color='gray')), row=4, col=1)
                fig.update_layout(height=800, template="plotly_white", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e: st.error(f"STL Failed: {e}")

with tab2:
    st.markdown("### Frequency Analysis (Spectrogram)")
    c1, c2 = st.columns(2)
    with c1: win_len = st.number_input("Window Length", min_value=10, max_value=1000, value=256)
    with c2: overlap = st.number_input("Overlap", min_value=0, max_value=win_len-1, value=int(win_len/2))

    if st.button("Generate Spectrogram", type="primary"):
        with st.spinner("Computing..."):
            try:
                f, t, Sxx = af.compute_spectrogram(series, window_length=win_len, overlap=overlap)
                fig = go.Figure(data=go.Heatmap(z=Sxx, x=t, y=f, colorscale="Viridis"))
                fig.update_layout(title=f"Spectrogram: {selected_group}", height=600, template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e: st.error(f"Spectrogram Failed: {e}")