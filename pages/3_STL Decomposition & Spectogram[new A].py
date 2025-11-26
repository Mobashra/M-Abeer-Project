import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import utils
import analysis_functions as af

st.set_page_config(page_title="STL & Spectrogram", layout="wide")
st.title("📉 Time Series Analysis: STL & Spectrogram")

if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

# --- 1. CONTROLS ---
col1, col2 = st.columns(2)
with col1:
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
with col2:
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

# --- 2. LOAD DATA (RAW HOURLY) ---
with st.spinner(f"Fetching hourly resolution data for {selected_year}..."):
    df = utils.load_yearly_data(data_type, selected_year)

if df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# --- 3. FILTERING ---
current_area = st.session_state["selected_price_area"]
price_areas = sorted(df['price_area'].unique())

# Safety check
if current_area not in price_areas: 
    current_area = price_areas[0]

st.subheader(f"Analyzing: {current_area} ({selected_year})")

# Filter by Area
df_area = df[df['price_area'] == current_area].copy()

# Select Group
groups = sorted(df_area["group"].unique())
selected_group = st.selectbox(f"Select {data_type} Group:", groups, index=0)

# --- 4. PREPARE TIME SERIES ---
# Filter by group
mask = df_area["group"] == selected_group

# Create Series: Set Date as Index -> Select Value -> Resample to Hourly -> Interpolate
# We use 'mwh' because utils.py standardizes the column name to 'mwh'
series = df_area[mask].set_index("date")["mwh"].asfreq("h").interpolate(method="time")

if series.empty:
    st.error("Not enough data points to generate analysis.")
    st.stop()

# --- 5. VISUALIZATION TABS ---
tab1, tab2 = st.tabs(["STL Decomposition", "Spectrogram"])

# --- TAB 1: STL ---
with tab1:
    st.markdown("### Seasonal-Trend Decomposition (STL)")
    
    # --- STL PARAMETERS (Required by Part 3) ---
    with st.expander("⚙️ STL Settings", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            # Period: Default 168 (Weekly cycle for hourly data)
            period = st.number_input("Period Length", min_value=2, value=168, step=1)
        with c2:
            # Seasonal Smoother: Must be odd
            seasonal = st.number_input("Seasonal Smoother", min_value=3, value=13, step=2)
        with c3:
            # Trend Smoother: Must be odd (Default 169 is ~1 week smoothing)
            trend = st.number_input("Trend Smoother", min_value=3, value=169, step=2)
        with c4:
            robust = st.checkbox("Robust Fitting", value=True)

    try:
        # Pass parameters to function
        res = af.compute_stl(series, period=period, seasonal=seasonal, trend=trend, robust=robust)
        
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                            subplot_titles=("Original", "Trend", "Seasonal", "Residual"))
        
        fig.add_trace(go.Scatter(x=res.observed.index, y=res.observed, name="Original"), row=1, col=1)
        fig.add_trace(go.Scatter(x=res.trend.index, y=res.trend, name="Trend", line=dict(color='orange')), row=2, col=1)
        fig.add_trace(go.Scatter(x=res.seasonal.index, y=res.seasonal, name="Seasonal", line=dict(color='green')), row=3, col=1)
        fig.add_trace(go.Scatter(x=res.resid.index, y=res.resid, name="Residual", line=dict(color='gray', width=0.5)), row=4, col=1)
        
        fig.update_layout(height=800, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"STL Failed: {e}")

# --- TAB 2: SPECTROGRAM ---
with tab2:
    st.markdown("### Frequency Analysis")
    
    # --- SPECTROGRAM PARAMETERS (Required by Part 3) ---
    with st.expander("⚙️ Spectrogram Settings", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            win_len = st.number_input("Window Length", min_value=10, max_value=1000, value=256, step=10)
        with c2:
            # Overlap should be less than window length
            overlap = st.number_input("Window Overlap", min_value=0, max_value=win_len-1, value=int(win_len/2), step=10)

    try:
        # Pass parameters to function
        f, t, Sxx = af.compute_spectrogram(series, window_length=win_len, overlap=overlap)
        
        fig = go.Figure(data=go.Heatmap(
            z=Sxx, x=t, y=f, 
            colorscale="Viridis",
            colorbar=dict(title="Power (dB)")
        ))
        
        fig.update_layout(
            title=f"Spectrogram: {selected_group} in {current_area}",
            yaxis_title="Frequency (cycles/hour)",
            xaxis_title="Time",
            # Zoom in on 0 - 0.1 to see Daily (0.04) and Weekly (0.006) cycles clearly
            yaxis_range=[0, 0.1] 
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("Tip: **0.041** = Daily Cycle (24h). **0.083** = 12-Hour Cycle.")
        
    except Exception as e:
        st.error(f"Spectrogram Failed: {e}")