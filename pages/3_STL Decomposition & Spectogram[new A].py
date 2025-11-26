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

# --- 3. LOAD DATA ---
# Use the NEW function 'load_yearly_data' which works for both Prod/Cons
with st.spinner(f"Fetching hourly data for {selected_year}..."):
    if hasattr(utils, 'load_yearly_data'):
        df = utils.load_yearly_data(data_type, selected_year)
    else:
        # Fallback just in case utils isn't updated yet
        st.error("Please ensure utils.py contains 'load_yearly_data'")
        st.stop()

if df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# --- 4. SMART COLUMN DETECTION ---
# Ensures we find the value column regardless of naming (value, mwh, quantityKwh)
if 'mwh' in df.columns:
    val_col = 'mwh'
elif 'value' in df.columns:
    val_col = 'value'
elif 'quantityKwh' in df.columns:
    val_col = 'quantityKwh'
else:
    st.error(f"Could not find value column. Available columns: {df.columns.tolist()}")
    st.stop()

# --- 5. PREPARE DATA ---
# Filter by Area
current_area = st.session_state["selected_price_area"]
price_areas = sorted(df['price_area'].unique())

# Safety check if selected area isn't in the current dataset
if current_area not in price_areas: 
    current_area = price_areas[0]

st.subheader(f"Analyzing: {current_area} ({selected_year})")

df_area = df[df['price_area'] == current_area].copy()

# Standardize 'group' column name if needed
if 'group' not in df_area.columns:
    if 'production_group' in df_area.columns:
        df_area.rename(columns={'production_group': 'group'}, inplace=True)
    elif 'consumption_group' in df_area.columns:
        df_area.rename(columns={'consumption_group': 'group'}, inplace=True)

# Group Selector
groups = sorted(df_area["group"].unique())
selected_group = st.selectbox(f"Select {data_type} Group:", groups, index=0)

# Create Time Series
mask = df_area["group"] == selected_group

# Ensure datetime index
if 'date' not in df_area.columns:
    date_col = 'start_time' if 'start_time' in df_area.columns else 'startTime'
    df_area['date'] = pd.to_datetime(df_area[date_col])

# Resample to Hourly ('h') and Interpolate to fix missing gaps
series = df_area[mask].set_index("date")[val_col].asfreq("h").interpolate(method="time")

if series.empty:
    st.error("Not enough data to generate analysis.")
    st.stop()

# --- 6. TABS ---
tab1, tab2 = st.tabs(["STL Decomposition", "Spectrogram"])

with tab1:
    st.markdown("### Seasonal-Trend Decomposition (STL)")
    try:
        res = af.compute_stl(series)
        
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

with tab2:
    st.markdown("### Frequency Analysis")
    try:
        f, t, Sxx = af.compute_spectrogram(series)
        fig = go.Figure(data=go.Heatmap(z=Sxx, x=t, y=f, colorscale="Viridis"))
        fig.update_layout(
            title=f"Spectrogram: {selected_group} in {current_area}",
            yaxis_title="Frequency (cycles/hour)", 
            # Zoom in on low freq (Daily/Weekly cycles)
            yaxis_range=[0, 0.1]
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Spectrogram Failed: {e}")