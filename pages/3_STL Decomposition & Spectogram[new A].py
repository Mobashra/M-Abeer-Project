import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import utils
import analysis_functions as af

st.set_page_config(page_title="STL & Spectrogram", layout="wide")
st.title("📉 Time Series Analysis: STL & Spectrogram")

# --- 1. SAFETY DEFAULTS ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

# --- 2. CONTROLS ---
col1, col2 = st.columns(2)
with col1:
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
with col2:
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

# --- 3. LOAD DATA (FAST) ---
with st.spinner(f"Fetching hourly data for {selected_year}..."):
    # Uses the optimized loader from utils
    df = utils.get_year_data(data_type, selected_year)

if df.empty:
    st.warning(f"No data found for {selected_year}.")
    st.stop()

# --- 4. SPECIFIC SELECTION ---
# Filter by Area (from Session State or Default)
current_area = st.session_state["selected_price_area"]
price_areas = sorted(df['price_area'].unique())

# Ensure current area exists in data
if current_area not in price_areas:
    current_area = price_areas[0]

st.subheader(f"Analyzing: {current_area} ({selected_year})")

# Filter Dataframe
df_area = df[df['price_area'] == current_area].copy()

# Select Group
groups = sorted(df_area["group"].unique())
selected_group = st.selectbox(f"Select {data_type} Group:", groups, index=0)

# Prepare Time Series (Critical for STL/Spectrogram)
# 1. Filter by group
# 2. Set Date Index
# 3. Resample to Hourly ('h') to ensure no missing steps
# 4. Interpolate missing values so math doesn't break
mask = df_area["group"] == selected_group
series = df_area[mask].set_index("date")["mwh"].asfreq("h").interpolate(method="time")

if series.empty:
    st.error("Not enough data to generate analysis.")
    st.stop()

# --- 5. VISUALIZATION TABS ---
tab1, tab2 = st.tabs(["STL Decomposition", "Spectrogram"])

with tab1:
    st.markdown("### Seasonal-Trend Decomposition using LOESS (STL)")
    st.caption("Deconstructs the time series into Trend, Seasonal, and Residual components.")
    
    try:
        # Compute STL (using analysis_functions)
        res = af.compute_stl(series)
        
        # Plot
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                            subplot_titles=("Original", "Trend", "Seasonal", "Residual"))
        
        fig.add_trace(go.Scatter(x=res.observed.index, y=res.observed, name="Original"), row=1, col=1)
        fig.add_trace(go.Scatter(x=res.trend.index, y=res.trend, name="Trend", line=dict(color='orange')), row=2, col=1)
        fig.add_trace(go.Scatter(x=res.seasonal.index, y=res.seasonal, name="Seasonal", line=dict(color='green')), row=3, col=1)
        fig.add_trace(go.Scatter(x=res.resid.index, y=res.resid, name="Residual", line=dict(color='gray', width=0.5)), row=4, col=1)
        
        fig.update_layout(height=800, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"STL Calculation failed: {e}")

with tab2:
    st.markdown("### Frequency Analysis (Spectrogram)")
    st.caption("Visualizes the intensity of different frequencies (cycles) over time.")
    
    try:
        # Compute Spectrogram
        f, t, Sxx = af.compute_spectrogram(series)
        
        # Plot
        fig = go.Figure(data=go.Heatmap(
            z=Sxx, 
            x=t, 
            y=f, 
            colorscale="Viridis",
            colorbar=dict(title="Power (dB)")
        ))
        
        fig.update_layout(
            title=f"Spectrogram: {selected_group} in {current_area}",
            yaxis_title="Frequency (cycles/hour)",
            xaxis_title="Time",
            # Zoom in on 0-0.1 because Daily (0.04) and Weekly (0.006) cycles are low freq
            yaxis_range=[0, 0.1] 
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("""
        **How to read:**
        * **Bright Yellow Lines:** Strong repeating patterns.
        * **~0.041 (1/24):** Daily Cycle.
        * **~0.083 (1/12):** 12-Hour Cycle.
        """)
        
    except Exception as e:
        st.error(f"Spectrogram failed: {e}")