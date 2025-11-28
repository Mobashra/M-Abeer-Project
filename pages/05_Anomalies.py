import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.fft import dct, idct
from sklearn.neighbors import LocalOutlierFactor
import utils

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Anomalies", layout="wide")

# 1. SAFETY & STYLING
utils.check_session_state()
utils.render_sidebar()

st.title("🚨 Anomaly Detection")
st.markdown("Detect extreme weather events using **Statistical Process Control (SPC)** and **Local Outlier Factor (LOF)**.")

# 2. CONTEXT & CONTROLS
current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]

with st.container():
    c1, c2 = st.columns([1, 3])
    with c1:
        # Local Year Selector
        year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)
    with c2:
        st.info(f"**Analysis Scope:** {current_area} (Lat: {coords['lat']:.2f}, Lon: {coords['lon']:.2f})")

# 3. LOAD DATA
with st.spinner(f"Fetching {year} weather data..."):
    df = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{year}-01-01", f"{year}-12-31")

if df.empty:
    st.error("No weather data available for this location/year.")
    st.stop()

# ======================================================
# ANALYSIS LOGIC (Professor's Feedback Implemented)
# ======================================================

def detect_temperature_outliers(df, freq_cutoff=0.05, n_std=3):
    """
    Detect temperature outliers using DCT and SPC.
    
    IMPROVEMENT: 
    Boundaries are dynamic (Trend + Limit) rather than static.
    This ensures the SPC lines follow the seasonal temperature curve.
    """
    # Extract
    temp = df['temperature_2m'].ffill().bfill().values
    time = pd.to_datetime(df['time'])
    
    # 1. DCT Transform
    temp_dct = dct(temp, type=2, norm='ortho')
    
    # 2. High-pass filter (Isolate the Noise/SATV)
    cutoff_index = int(len(temp_dct) * freq_cutoff)
    temp_dct_filtered = temp_dct.copy()
    temp_dct_filtered[:cutoff_index] = 0
    
    # 3. SATV (Seasonally Adjusted Temperature Variation)
    satv = idct(temp_dct_filtered, type=2, norm='ortho')

    # 4. Reconstruct Trend (The Low-frequency part)
    # We need this to make the lines "follow the curve"
    temp_dct_trend = np.zeros_like(temp_dct)
    temp_dct_trend[:cutoff_index] = temp_dct[:cutoff_index]
    trend = idct(temp_dct_trend, type=2, norm='ortho')
    
    # 5. Robust Statistics on SATV
    median_satv = np.median(satv)
    mad_satv = np.median(np.abs(satv - median_satv))
    std_satv = mad_satv * 1.4826
    
    # 6. Calculate Limits
    upper_boundary_satv = median_satv + n_std * std_satv
    lower_boundary_satv = median_satv - n_std * std_satv

    # 7. DYNAMIC BOUNDARIES (The Fix)
    # Add the Trend back to the limits so they curve with the data
    upper_dynamic = trend + upper_boundary_satv
    lower_dynamic = trend + lower_boundary_satv
    
    # 8. Identify Outliers
    # We check if the SATV (noise) exceeds the statistical limit
    outliers_mask = (satv > upper_boundary_satv) | (satv < lower_boundary_satv)
    n_outliers = np.sum(outliers_mask)
    
    # Plotting
    fig = go.Figure()
    
    # Raw Data
    fig.add_trace(go.Scatter(x=time, y=temp, mode='lines', name='Temperature', line=dict(color='#1f77b4', width=1.5)))
    
    # Dynamic Limits (Curved Lines)
    fig.add_trace(go.Scatter(x=time, y=upper_dynamic, mode='lines', name='Upper Limit', line=dict(color='#ff7f0e', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=time, y=lower_dynamic, mode='lines', name='Lower Limit', line=dict(color='#ff7f0e', width=1, dash='dash')))
    
    # Outliers
    if n_outliers > 0:
        fig.add_trace(go.Scatter(
            x=time[outliers_mask], y=temp[outliers_mask],
            mode='markers', name='Anomaly',
            marker=dict(color='red', size=8, symbol='x')
        ))
        
    fig.update_layout(
        title=f"SPC Analysis (Dynamic Seasonality)", 
        yaxis_title="Temperature (°C)", 
        height=500, 
        template="plotly_white",
        legend=dict(orientation="h", y=1.1)
    )
    
    return fig, n_outliers, time[outliers_mask]

def detect_precipitation_anomalies(df, outlier_prop=0.01, n_neighbors=50):
    """Detects precipitation anomalies using LOF."""
    precip = df['precipitation'].values
    time = pd.to_datetime(df['time'])
    
    # Features: Value + Diff (Rate of change)
    precip_diff = np.diff(precip, prepend=precip[0])
    X = np.column_stack([precip, precip_diff])
    
    # Jitter for duplicates (LOF struggles with many 0.0s)
    rng = np.random.RandomState(42)
    X_jitter = X + rng.normal(0, 1e-6, X.shape)
    
    # LOF
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=outlier_prop)
    pred = lof.fit_predict(X_jitter)
    mask = pred == -1
    n_anom = np.sum(mask)
    
    # Plot
    fig = go.Figure()
    fig.add_trace(go.Bar(x=time[~mask], y=precip[~mask], name='Normal Rain', marker_color='#2ca02c'))
    fig.add_trace(go.Bar(x=time[mask], y=precip[mask], name='Anomaly', marker_color='red'))
    
    # Add Markers for visibility if bars are too thin
    fig.add_trace(go.Scatter(
        x=time[mask], y=precip[mask],
        mode='markers', name='Marker',
        marker=dict(color='red', size=8, symbol='circle-open'),
        showlegend=False
    ))
    
    fig.update_layout(title=f"LOF Anomaly Detection (Top {outlier_prop*100:.1f}%)", yaxis_title="Precipitation (mm)", height=500, template="plotly_white")
    
    return fig, n_anom, time[mask], precip[mask]

# ======================================================
# 4. TABS & UI
# ======================================================
tab1, tab2 = st.tabs(["🌡️ Temperature (SPC)", "🌧️ Precipitation (LOF)"])

# --- TAB 1: SPC ---
with tab1:
    c_param, c_plot = st.columns([1, 3])
    with c_param:
        st.markdown("#### ⚙️ Parameters")
        freq_cutoff = st.slider("Freq Cutoff", 0.01, 0.20, 0.05, step=0.01, help="Controls trend smoothness.")
        n_std = st.slider("Sigma (σ)", 1.0, 5.0, 3.0, step=0.1, help="Width of the boundary.")
        st.info("Boundaries adjust dynamically to seasonal trends.")

    try:
        fig, n_out, dates = detect_temperature_outliers(df, freq_cutoff, n_std)
        with c_plot:
            st.plotly_chart(fig, use_container_width=True)
            
            # Metrics
            m1, m2 = st.columns(2)
            m1.metric("Total Data Points", len(df))
            m2.metric("Outliers Detected", int(n_out), delta_color="inverse")
            
            if n_out > 0:
                with st.expander("View Outlier Dates"):
                    st.write(dates)
    except Exception as e:
        st.error(f"SPC Error: {e}")

# --- TAB 2: LOF ---
with tab2:
    c_param, c_plot = st.columns([1, 3])
    with c_param:
        st.markdown("#### ⚙️ Parameters")
        prop = st.slider("Outlier Proportion", 0.001, 0.05, 0.01, format="%.3f")
        neighbors = st.slider("Neighbors", 20, 200, 50)
        st.info("LOF identifies rain events with unusual intensity or pattern.")

    try:
        fig, n_anom, dates, vals = detect_precipitation_anomalies(df, prop, neighbors)
        with c_plot:
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Anomalous Events", int(n_anom), delta_color="inverse")
    except Exception as e:
        st.error(f"LOF Error: {e}")