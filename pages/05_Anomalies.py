import streamlit as st
import plotly.graph_objects as go
import utils
import analysis_functions as af

st.set_page_config(page_title="Anomalies", layout="wide")

# 1. SAFETY & STYLING
utils.check_session_state()
utils.render_sidebar()

st.title("🚨 Anomaly Detection")
st.markdown("Detect extreme weather events using **Statistical Process Control (SPC)** and **Local Outlier Factor (LOF)**.")

# 2. CONTEXT & CONTROLS
# Inherit from Map Page
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

# 4. TABS
tab1, tab2 = st.tabs(["🌡️ Temperature (SPC)", "🌧️ Precipitation (LOF)"])

# ==================================================
# TAB 1: TEMPERATURE SPC
# ==================================================
with tab1:
    c_param, c_plot = st.columns([1, 3])
    
    with c_param:
        st.markdown("#### ⚙️ Parameters")
        cutoff = st.slider("DCT Cutoff", 100, 2000, 1500, help="Controls trend smoothness. Higher = More detailed trend.")
        n_std = st.slider("Sigma (σ)", 1.0, 5.0, 3.0, step=0.1, help="Width of the control limits.")
        
        st.caption("""
        **Method:** 1. **DCT Filter:** Separates Trend vs Noise (SATV).  
        2. **Robust Stats:** Calculates limits from Noise.  
        3. **Reconstruction:** Limits = Trend ± (σ * Noise_Std).
        """)

    # Calculation
    try:
        t, temp, upper, lower, outliers = af.detect_temperature_anomalies_spc(df, freq_cutoff=cutoff, n_std=n_std)
        
        with c_plot:
            fig = go.Figure()
            
            # A. Raw Data
            fig.add_trace(go.Scatter(x=t, y=temp, mode='lines', name="Temperature", line=dict(color='#1f77b4', width=1.5)))
            
            # B. Dynamic Boundaries (Professor's Requirement)
            # These lines follow the trend, they are NOT horizontal
            fig.add_trace(go.Scatter(x=t, y=upper, name="Upper Limit", line=dict(dash='dash', color='#ff7f0e', width=1)))
            fig.add_trace(go.Scatter(x=t, y=lower, name="Lower Limit", line=dict(dash='dash', color='#ff7f0e', width=1)))
            
            # C. Anomalies
            if outliers.sum() > 0:
                fig.add_trace(go.Scatter(
                    x=t[outliers], y=temp[outliers],
                    mode='markers', name="Anomaly",
                    marker=dict(color='red', size=8, symbol='x')
                ))
            
            fig.update_layout(
                title=f"SPC Analysis (Seasonally Adjusted)",
                yaxis_title="Temperature (°C)",
                template="plotly_white",
                height=500,
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Metrics
            m1, m2 = st.columns(2)
            m1.metric("Total Data Points", len(t))
            m2.metric("Outliers Detected", int(outliers.sum()), delta_color="inverse")

    except Exception as e:
        st.error(f"SPC Error: {e}")

# ==================================================
# TAB 2: PRECIPITATION LOF
# ==================================================
with tab2:
    c_param, c_plot = st.columns([1, 3])
    
    with c_param:
        st.markdown("#### ⚙️ Parameters")
        contam_pct = st.slider("Contamination %", 0.1, 10.0, 1.0, step=0.1)
        contam = contam_pct / 100.0
        
        st.caption("""
        **Method:** **Local Outlier Factor (LOF)** is an unsupervised algorithm that detects samples which have a substantially lower density than their neighbors.
        """)

    try:
        t, precip, outliers = af.detect_precipitation_anomalies_lof(df, contamination=contam)
        
        with c_plot:
            fig2 = go.Figure()
            
            # A. Precipitation
            fig2.add_trace(go.Scatter(x=t, y=precip, mode='lines', name="Precipitation", line=dict(color='#2ca02c', width=1)))
            
            # B. Anomalies
            if outliers.sum() > 0:
                fig2.add_trace(go.Scatter(
                    x=t[outliers], y=precip[outliers],
                    mode='markers', name="Extreme Event",
                    marker=dict(color='red', size=8, symbol='circle-open', line=dict(width=2))
                ))
            
            fig2.update_layout(
                title=f"Precipitation Anomalies (LOF)",
                yaxis_title="Precipitation (mm)",
                template="plotly_white",
                height=500,
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Metrics
            m1, m2 = st.columns(2)
            m1.metric("Rainy Hours", int((precip > 0).sum()))
            m2.metric("Anomalous Events", int(outliers.sum()), delta_color="inverse")

    except Exception as e:
        st.error(f"LOF Error: {e}")