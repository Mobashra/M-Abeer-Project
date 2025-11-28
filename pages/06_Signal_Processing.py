import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import utils
import analysis_functions as af

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Signal Processing", layout="wide")

# 1. SAFETY & STYLING
utils.check_session_state()
utils.render_sidebar()

st.title("📡 Signal Decomposition & Frequency Analysis")

# 2. CONTROLS (Dashboard Style)
with st.container():
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)
    with c2:
        data_type = st.radio("Source", ["Production", "Consumption"], horizontal=True)
    with c3:
        st.info(f"**Scope:** {st.session_state['selected_price_area']}")

# 3. LOAD DATA
with st.spinner("Fetching data..."):
    df = utils.load_yearly_data(data_type, year)

if df.empty:
    st.error(f"No data found for {year}.")
    st.stop()

# Filter Data
df_area = df[df['price_area'] == st.session_state["selected_price_area"]]
groups = sorted(df_area['group'].unique())

if not groups:
    st.warning("No groups available for this region.")
    st.stop()

# Select Group
selected_group = st.selectbox("Select Energy Group", groups)

# Prepare Time Series
mask = df_area["group"] == selected_group
# Standardize column name
val_col = 'mwh' if 'mwh' in df_area.columns else 'value'
series = df_area[mask].set_index("date")[val_col].sort_index().asfreq("h").interpolate(method="time")

if series.empty:
    st.error("Not enough data points for analysis.")
    st.stop()

st.divider()

# ======================================================
# 4. ANALYSIS TABS
# ======================================================
tab1, tab2 = st.tabs(["📉 STL Decomposition", "〰️ Spectrogram"])

# --- TAB 1: STL DECOMPOSITION ---
with tab1:
    st.markdown("### Seasonal-Trend Decomposition (LOESS)")
    
    # Parameters
    with st.container():
        c_p, c_s, c_t = st.columns(3)
        with c_p:
            period = st.number_input("Period (Hours)", min_value=2, value=168, step=1, help="168 = Weekly Seasonality")
        with c_s:
            seasonal = st.number_input("Seasonal Smoother (Odd)", min_value=3, value=13, step=2)
        with c_t:
            trend = st.number_input("Trend Smoother (Odd)", min_value=3, value=169, step=2)

    if st.button("Run Decomposition", type="primary"):
        with st.spinner("Decomposing signal..."):
            try:
                # Robust=True is generally better for energy data
                res = af.compute_stl(series, period=period, seasonal=seasonal, trend=trend, robust=True)
                
                # 4-Row Subplot
                fig = make_subplots(
                    rows=4, cols=1, 
                    shared_xaxes=True,
                    subplot_titles=("Observed Data", "Trend Component", "Seasonal Component", "Residuals"),
                    vertical_spacing=0.05
                )
                
                # 1. Observed
                fig.add_trace(go.Scatter(x=res.observed.index, y=res.observed, name="Observed", line=dict(color='#1f77b4', width=1)), row=1, col=1)
                # 2. Trend
                fig.add_trace(go.Scatter(x=res.trend.index, y=res.trend, name="Trend", line=dict(color='#ff7f0e', width=2)), row=2, col=1)
                # 3. Seasonal
                fig.add_trace(go.Scatter(x=res.seasonal.index, y=res.seasonal, name="Seasonal", line=dict(color='#2ca02c', width=1)), row=3, col=1)
                # 4. Residual
                fig.add_trace(go.Scatter(x=res.resid.index, y=res.resid, name="Residual", line=dict(color='#7f7f7f', width=0.5)), row=4, col=1)
                
                fig.update_layout(height=800, template="plotly_white", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"STL Failed: {e}")

# --- TAB 2: SPECTROGRAM ---
with tab2:
    st.markdown("### Frequency Analysis (Spectrogram)")
    
    # Parameters
    c1, c2 = st.columns(2)
    with c1:
        win_len = st.number_input("Window Length", min_value=10, max_value=1000, value=256, step=10)
    with c2:
        overlap = st.number_input("Window Overlap", min_value=0, max_value=win_len-1, value=int(win_len/2), step=10)

    if st.button("Generate Spectrogram", type="primary"):
        with st.spinner("Computing frequencies..."):
            try:
                f, t, Sxx = af.compute_spectrogram(series, window_length=win_len, overlap=overlap)
                
                fig = go.Figure(data=go.Heatmap(
                    z=Sxx, x=t, y=f,
                    colorscale="Viridis",
                    colorbar=dict(title="Power (dB)")
                ))
                
                fig.update_layout(
                    title=f"Spectrogram: {selected_group}",
                    yaxis_title="Frequency (cycles/hour)",
                    xaxis_title="Time",
                    yaxis_range=[0, 0.1], # Focus on low frequencies usually relevant for energy
                    template="plotly_white",
                    height=600
                )
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"Spectrogram Failed: {e}")