# page_new_A_production_analysis.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from statsmodels.tsa.seasonal import STL
from scipy.signal import spectrogram

st.set_page_config(page_title="Production Analysis (STL & Spectrogram)", layout="wide")
st.title("⚙️ Production Analysis: STL Decomposition & Spectrogram")

# --- Ensure area selection exists ---
if "selected_price_area" not in st.session_state:
    st.warning("⚠️ Please select a price area in the 'Elhub API Data' page first.")
    st.stop()

selected_area = st.session_state["selected_price_area"]
st.subheader(f"Selected Price Area: {selected_area}")

# --- Load production data (replace with your Elhub API or cached dataset) ---
@st.cache_data(show_spinner=False)
@st.cache_data
def load_production_data():
    df = pd.read_csv("elhub_2021_production.csv")

    # Rename columns to consistent lowercase names
    df.rename(
        columns={
            "startTime": "time",
            "priceArea": "price_area",
            "productionGroup": "production_group",
            "quantityKwh": "production",
        },
        inplace=True,
    )

    # Convert time column to datetime (with timezone awareness)
    df["time"] = pd.to_datetime(df["time"], utc=True)

    # Sort by time to ensure correct ordering
    df = df.sort_values("time").reset_index(drop=True)

    return df


df_prod = load_production_data()
df_prod_area = df_prod[df_prod["price_area"] == selected_area]

if df_prod_area.empty:
    st.error(f"No data found for {selected_area}. Please check your Elhub data.")
    st.stop()

# --- Production groups ---
groups = [c for c in df_prod_area.columns if c not in ["time", "price_area"]]
if not groups:
    st.error("No production groups found in data.")
    st.stop()

# --- Tabs for STL & Spectrogram ---
tab1, tab2 = st.tabs(["📈 STL Decomposition", "🎵 Spectrogram"])

# ========================================
# Tab 1: STL Decomposition
# ========================================
with tab1:
    st.subheader("Seasonal-Trend Decomposition using STL")

    group = st.selectbox("Select production group:", groups, index=0)
    period = st.number_input("Period (hours):", value=168, min_value=24, max_value=1000)
    seasonal_smoother = st.slider("Seasonal smoother:", 3, 21, 7, step=2)
    trend_smoother = st.slider("Trend smoother:", 3, 101, 13, step=2)
    robust = st.checkbox("Use robust fitting", value=True)

    df_group = df_prod_area.set_index("time")[group].dropna()
    if df_group.empty:
        st.warning("No data available for this production group.")
    else:
        st.info(f"STL decomposition with period={period}, trend={trend_smoother}, seasonal={seasonal_smoother}")

        # Perform STL decomposition
        stl = STL(df_group, period=period, seasonal=seasonal_smoother, trend=trend_smoother, robust=robust).fit()

        # Plotly figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_group.index, y=df_group, name="Original", line=dict(width=1)))
        fig.add_trace(go.Scatter(x=df_group.index, y=stl.trend, name="Trend", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=df_group.index, y=stl.seasonal, name="Seasonal", line=dict(width=1, dash="dot")))
        fig.add_trace(go.Scatter(x=df_group.index, y=stl.resid, name="Residual", line=dict(width=1, dash="dash")))

        fig.update_layout(
            title=f"STL Decomposition for {group} in {selected_area} (2021)",
            xaxis_title="Time",
            yaxis_title="Production (MW)",
            template="plotly_white",
            legend=dict(x=0, y=1, bgcolor="rgba(0,0,0,0)")
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- Show stats summary ---
        st.write("### Decomposition Statistics")
        st.metric("Mean Production", f"{df_group.mean():.2f}")
        st.metric("Residual Std Dev", f"{stl.resid.std():.2f}")

# ========================================
# Tab 2: Spectrogram
# ========================================
with tab2:
    st.subheader("Spectrogram Analysis")

    group_spec = st.selectbox("Select production group for spectrogram:", groups, index=0, key="spec_group")
    window_length = st.number_input("Window length (hours):", value=168, min_value=24, max_value=1000)
    overlap = st.slider("Window overlap (%):", 0, 90, 50)

    df_spec = df_prod_area.set_index("time")[group_spec].dropna()
    if df_spec.empty:
        st.warning("No data available for this group.")
        st.stop()

    # Compute spectrogram
    fs = 1  # 1 sample/hour
    nperseg = window_length
    noverlap = int(nperseg * (overlap / 100))
    f, t, Sxx = spectrogram(df_spec.values, fs=fs, nperseg=nperseg, noverlap=noverlap)
    Sxx_dB = 10 * np.log10(Sxx + 1e-9)

    fig_spec = go.Figure(
        data=go.Heatmap(
            z=Sxx_dB,
            x=t,
            y=f,
            colorscale="Viridis",
            colorbar=dict(title="Power (dB)"),
        )
    )
    fig_spec.update_layout(
        title=f"Spectrogram of {group_spec} in {selected_area} (2021)",
        xaxis_title="Time (hours since start)",
        yaxis_title="Frequency (1/hour)",
        template="plotly_white",
    )
    st.plotly_chart(fig_spec, use_container_width=True)
