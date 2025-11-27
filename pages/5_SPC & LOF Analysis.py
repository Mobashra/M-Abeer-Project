import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from analysis_functions import (
    detect_temperature_anomalies_spc,
    detect_precip_anomalies_lof
)

st.set_page_config(layout="wide")

st.title("🔧 SPC & LOF — Standard Process Control and Local Outlier Factor")

# ---------------------------------------------------------------------
# 1. Load Data (from session state or parquet)
# ---------------------------------------------------------------------
if "weather_data" not in st.session_state:
    st.error("Weather data not loaded. Please load data from the Open-Meteo page first.")
    st.stop()

df = st.session_state["weather_data"]

# Ensure datetime index
df = df.copy()
if not isinstance(df.index, pd.DatetimeIndex):
    df.index = pd.to_datetime(df["time"])

# =====================================================================
# --------------------------   SPC SECTION   ---------------------------
# =====================================================================

st.subheader("📈 SPC on Dry-Bulb Temperature (with **rolling boundaries**)")

colA, colB = st.columns(2)

with colA:
    dct_cutoff = st.slider("DCT Cutoff", 50, 2000, 400, step=25)

with colB:
    sigma = st.slider("Sigma threshold", 1.5, 5.0, 3.0, step=0.1)

# --- Run SPC (DCT detrending) ---
spc_result = detect_temperature_anomalies_spc(
    df["temperature_2m"],
    dct_cutoff=dct_cutoff,
    sigma=sigma
)

detrended = spc_result["detrended"]
raw = df["temperature_2m"]

# ---------------------------------------------------------------------
# ★★★★★ NEW REQUIREMENT IMPLEMENTED: “Boundaries must follow the data”
# ---------------------------------------------------------------------
# Compute rolling mean & rolling std that follow the temperature trend
ROLL_WINDOW = 48  # 2 days — smooth but still responsive
rolling_mean = raw.rolling(ROLL_WINDOW, min_periods=12).mean()
rolling_std = raw.rolling(ROLL_WINDOW, min_periods=12).std()

upper_dynamic = rolling_mean + sigma * rolling_std
lower_dynamic = rolling_mean - sigma * rolling_std

# Identify anomalies using dynamic boundaries
spc_anomalies = (raw > upper_dynamic) | (raw < lower_dynamic)

# ---------------------------------------------------------------------
# Plot SPC with DYNAMIC boundaries
# ---------------------------------------------------------------------
fig_spc = go.Figure()

fig_spc.add_trace(go.Scatter(
    x=raw.index,
    y=raw,
    mode="lines",
    line=dict(color="steelblue", width=2),
    name="Temperature 2m"
))

fig_spc.add_trace(go.Scatter(
    x=upper_dynamic.index,
    y=upper_dynamic,
    mode="lines",
    line=dict(color="red", width=1, dash="dot"),
    name="Upper SPC Boundary (Dynamic)"
))

fig_spc.add_trace(go.Scatter(
    x=lower_dynamic.index,
    y=lower_dynamic,
    mode="lines",
    line=dict(color="red", width=1, dash="dot"),
    name="Lower SPC Boundary (Dynamic)"
))

# Anomaly markers
fig_spc.add_trace(go.Scatter(
    x=raw[spc_anomalies].index,
    y=raw[spc_anomalies],
    mode="markers",
    marker=dict(color="crimson", size=7),
    name="Anomalies"
))

fig_spc.update_layout(
    height=400,
    margin=dict(l=20, r=20, t=20, b=20),
    legend=dict(orientation="h")
)

st.plotly_chart(fig_spc, use_container_width=True)

# =====================================================================
# ---------------------------   LOF SECTION   --------------------------
# =====================================================================

st.subheader("🌧 LOF Anomaly Detection on Precipitation")

contam = st.slider("Anomaly contamination (%)", 0.1, 10.0, 2.0)

lof_result = detect_precip_anomalies_lof(
    df[["precipitation"]].fillna(0),
    contamination=contam / 100.0,
)

lof_anomalies = lof_result["anomalies"]

fig_lof = go.Figure()

fig_lof.add_trace(go.Scatter(
    x=df.index,
    y=df["precipitation"],
    mode="lines",
    line=dict(color="darkgreen", width=2),
    name="Precipitation"
))

fig_lof.add_trace(go.Scatter(
    x=df.index[lof_anomalies],
    y=df["precipitation"][lof_anomalies],
    mode="markers",
    marker=dict(color="orange", size=8),
    name="Anomalies"
))

fig_lof.update_layout(
    height=400,
    margin=dict(l=20, r=20, t=20, b=20),
    legend=dict(orientation="h")
)

st.plotly_chart(fig_lof, use_container_width=True)

