import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.fft import dct, idct
from sklearn.neighbors import LocalOutlierFactor
import utils

# ======================================================
# PAGE CONFIG & SETUP
# ======================================================
st.set_page_config(page_title="Weather Anomalies", layout="wide")
utils.render_sidebar()
utils.check_session_state()

# Header
st.title("Weather Anomalies Detection")
st.header("Temperature Outliers and Precipitation Anomalies")
st.markdown("Detect unusual weather patterns using advanced statistical methods.")

# --- ACTIVE AREA CONTEXT ---
current_context_area = st.session_state.get("selected_price_area", "NO1")
st.info(f"📍 **Currently Viewing:** Price Area **{current_context_area}**")

st.markdown("---")

# ======================================================
# DATA LOADING
# ======================================================
# Ensure coords exist, default to NO1 if not
if "selected_coords" not in st.session_state:
    city = utils.CITIES.get(current_context_area, utils.CITIES["NO1"])
    st.session_state["selected_coords"] = {"lat": city["lat"], "lon": city["lon"]}

coords = st.session_state["selected_coords"]

# Year Selector
c_year, _ = st.columns([1, 3])
with c_year:
    year = st.selectbox("Select Analysis Year", [2021, 2022, 2023, 2024], index=0)

@st.cache_data(ttl=3600)
def get_data(lat, lon, y):
    return utils.fetch_weather_api(lat, lon, f"{y}-01-01", f"{y}-12-31")

with st.spinner("Loading weather data..."):
    df = get_data(coords['lat'], coords['lon'], year)

if df.empty:
    st.error("No data available.")
    st.stop()

st.success(f"Weather data loaded: {len(df)} records")

# ======================================================
# LOGIC FUNCTIONS
# ======================================================
def detect_temperature_outliers(df, freq_cutoff=0.05, n_std=3):
    # 1. Prepare Data
    temp = df['temperature_2m'].ffill().bfill().values
    time = pd.to_datetime(df['time'])
    
    # 2. DCT
    temp_dct = dct(temp, type=2, norm='ortho')
    
    # 3. Filter for SATV (High Pass)
    cutoff_index = int(len(temp_dct) * freq_cutoff)
    temp_dct_filtered = temp_dct.copy()
    temp_dct_filtered[:cutoff_index] = 0
    satv = idct(temp_dct_filtered, type=2, norm='ortho')
    
    # 4. Filter for Trend (Low Pass)
    temp_dct_trend = np.zeros_like(temp_dct)
    temp_dct_trend[:cutoff_index] = temp_dct[:cutoff_index]
    trend = idct(temp_dct_trend, type=2, norm='ortho')
    
    # 5. Robust Statistics
    median_satv = np.median(satv)
    mad_satv = np.median(np.abs(satv - median_satv))
    std_satv = mad_satv * 1.4826
    
    # 6. Boundaries (Dynamic)
    upper_boundary = median_satv + n_std * std_satv
    lower_boundary = median_satv - n_std * std_satv
    
    upper_dynamic = trend + upper_boundary
    lower_dynamic = trend + lower_boundary
    
    # 7. Outliers
    outliers_mask = (satv > upper_boundary) | (satv < lower_boundary)
    n_outliers = np.sum(outliers_mask)
    outlier_percentage = (n_outliers / len(temp)) * 100
    
    # 8. Plot
    fig = go.Figure()
    
    # Normal
    fig.add_trace(go.Scatter(
        x=time[~outliers_mask], y=temp[~outliers_mask],
        mode='lines', name='Normal Temperature',
        line=dict(color='green', width=1), opacity=0.7
    ))
    
    # Outliers
    fig.add_trace(go.Scatter(
        x=time[outliers_mask], y=temp[outliers_mask],
        mode='markers', name=f'Outliers (n={n_outliers})',
        marker=dict(color='red', size=6, symbol='circle')
    ))
    
    # Limits
    fig.add_trace(go.Scatter(x=time, y=upper_dynamic, mode='lines', name='Upper Limit', line=dict(color='gray', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=time, y=lower_dynamic, mode='lines', name='Lower Limit', line=dict(color='gray', width=1, dash='dash'), fill='tonexty'))
    
    fig.update_layout(
        title=f'Temperature Outliers (DCT + SPC) - Cutoff: {freq_cutoff}, ±{n_std}σ',
        xaxis_title='Time', yaxis_title='Temperature (°C)',
        template='plotly_white', height=500
    )
    
    return fig, n_outliers, outlier_percentage, time[outliers_mask], temp[outliers_mask]

def detect_precipitation_anomalies(df, outlier_prop=0.01, n_neighbors=50):
    precip = df['precipitation'].values
    time = pd.to_datetime(df['time'])
    
    precip_diff = np.diff(precip, prepend=precip[0])
    X = np.column_stack([precip, precip_diff])
    
    # Jitter
    rng = np.random.RandomState(42)
    X_jittered = X + rng.normal(0, 1e-6, X.shape)
    
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=outlier_prop)
    pred = lof.fit_predict(X_jittered)
    
    mask = pred == -1
    n_anom = np.sum(mask)
    pct = (n_anom / len(precip)) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=time[~mask], y=precip[~mask], name='Normal', marker_color='blue', opacity=0.6))
    fig.add_trace(go.Bar(x=time[mask], y=precip[mask], name=f'Anomaly (n={n_anom})', marker_color='red', opacity=1))
    fig.add_trace(go.Scatter(x=time[mask], y=precip[mask], mode='markers', name='Marker', marker=dict(color='red', size=8, line=dict(color='white', width=1)), showlegend=False))
    
    fig.update_layout(title=f'Precipitation Anomalies (LOF) - Prop: {outlier_prop*100:.1f}%', xaxis_title='Time', yaxis_title='Precipitation (mm)', template='plotly_white', height=500)
    
    return fig, n_anom, pct, time[mask], precip[mask]

# ======================================================
# VISUALIZATION LAYOUT
# ======================================================
tab1, tab2 = st.tabs(["🌡️ Temperature Outliers (SPC)", "🌧️ Precipitation Anomalies (LOF)"])

# --- TAB 1 ---
with tab1:
    st.subheader("Temperature Outlier Detection using DCT and SPC")
    
    # Controls in 2 Columns
    c1, c2 = st.columns(2)
    with c1:
        freq_cutoff = st.slider("Frequency Cutoff", 0.01, 0.20, 0.05, 0.01, help="Lower = removes more seasonal trends")
    with c2:
        n_std = st.slider("Standard Deviations", 1.0, 5.0, 3.0, 0.5, help="Number of σ for SPC boundaries")
        
    # Full Width Button
    if st.button("Detect Temperature Outliers", type="primary", use_container_width=True):
        with st.spinner("Analyzing..."):
            fig, n_out, pct, dates, vals = detect_temperature_outliers(df, freq_cutoff, n_std)
            
            # Full Width Plot
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📊 Outlier Statistics")
            
            # Metrics Below Plot
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Outliers", int(n_out))
            m2.metric("Percentage", f"{pct:.2f}%")
            m3.metric("Boundary Range", f"±{n_std}σ")
            
            if n_out > 0:
                with st.expander("🔍 View Outlier Details"):
                    out_df = pd.DataFrame({"Date": dates, "Temperature": vals})
                    st.dataframe(out_df, use_container_width=True)

# --- TAB 2 ---
with tab2:
    st.subheader("Precipitation Anomaly Detection using LOF")
    
    c1, c2 = st.columns(2)
    with c1:
        prop = st.slider("Expected Outlier Proportion", 0.001, 0.05, 0.01, 0.001, format="%.3f")
    with c2:
        neighbors = st.slider("Number of Neighbors", 20, 200, 50, 10)
    
    # REMOVED: The st.info line about expected anomalies
    
    if st.button("Detect Precipitation Anomalies", type="primary", use_container_width=True):
        with st.spinner("Analyzing..."):
            fig, n_out, pct, dates, vals = detect_precipitation_anomalies(df, prop, neighbors)
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📊 Anomaly Statistics")
            
            m1, m2 = st.columns(2)
            m1.metric("Total Anomalies", int(n_out))
            m2.metric("Percentage", f"{pct:.2f}%")
            
            if n_out > 0:
                with st.expander("🔍 View Anomaly Details"):
                    anom_df = pd.DataFrame({"Date": dates, "Precipitation": vals}).sort_values("Precipitation", ascending=False)
                    st.dataframe(anom_df, use_container_width=True)