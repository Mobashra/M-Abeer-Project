# page_new_B_production_analysis.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.neighbors import LocalOutlierFactor

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(page_title="Production Analysis (SPC & LOF)", layout="wide")
st.title("⚡ Production Analysis: Outliers/SPC & Anomalies/LOF")

# Ensure a price area is selected from the previous page
if "selected_price_area" not in st.session_state:
    st.warning("⚠️ Please select a price area in the 'Elhub API Data' page first.")
    st.stop()

selected_area = st.session_state["selected_price_area"]


st.markdown(f"""
### Selected Price Area: **:blue[{selected_area}]**
""")

# ---------------- DATA LOADING FUNCTION ----------------
@st.cache_data
def load_elhub_data(price_area):
    """Load Elhub production data for the selected price area."""
    df = pd.read_csv("elhub_2021_production.csv", parse_dates=["startTime"])
    df.rename(columns={"quantityKwh": "production_kwh"}, inplace=True)
    df["production_group"] = df["productionGroup"]
    df["price_area"] = df["priceArea"]
    df = df[df["price_area"] == price_area]
    return df

df = load_elhub_data(selected_area)

if df.empty:
    st.warning(f"No production data found for {selected_area}.")
    st.stop()

# ---------------- UI SELECTION ----------------
production_groups = sorted(df["production_group"].unique())
selected_groups = st.multiselect(
    "Select production group(s):",
    options=production_groups,
    default=production_groups
)

# Filter dataset by selection
df_filtered = df[df["production_group"].isin(selected_groups)].copy()
df_filtered.set_index("startTime", inplace=True)
df_filtered.sort_index(inplace=True)

# ---------------- MAIN TABS ----------------
tab1, tab2 = st.tabs(["SPC Analysis", "LOF Analysis"])

# ==========================================================
# TAB 1 — OUTLIER & SPC ANALYSIS
# ==========================================================
with tab1:
    st.subheader("Outlier & SPC Analysis")
    st.markdown("""
    This tab detects outliers in electricity production using **Statistical Process Control (SPC)**.
    - Upper/Lower Control Limits = mean ± 3 × standard deviation  
    - Points outside these limits are marked as **outliers**.
    """)

    for group in selected_groups:
        df_group = df_filtered[df_filtered["production_group"] == group]["production_kwh"]

        # --- Compute SPC stats ---
        mean_val = df_group.mean()
        std_val = df_group.std()
        ucl = mean_val + 3 * std_val
        lcl = mean_val - 3 * std_val

        # Identify outliers
        outliers = df_group[(df_group > ucl) | (df_group < lcl)]
        outlier_count = len(outliers)
        outlier_percent = (outlier_count / len(df_group)) * 100 if len(df_group) > 0 else 0

        # --- Display metrics in columns ---
        st.markdown(f"### ⚙️ Production Group: {group}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Mean (kWh)", f"{mean_val:.2f}")
        col2.metric("Std. Dev", f"{std_val:.2f}")
        col3.metric("Outliers", f"{outlier_count}")
        col4.metric("Outlier %", f"{outlier_percent:.2f}%")

        # --- Plot SPC Chart ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_group.index, y=df_group, mode="lines", name="Production"))
        fig.add_trace(go.Scatter(x=df_group.index, y=[ucl]*len(df_group), mode="lines", name="UCL", line=dict(color="red", dash="dash")))
        fig.add_trace(go.Scatter(x=df_group.index, y=[lcl]*len(df_group), mode="lines", name="LCL", line=dict(color="red", dash="dash")))

        if not outliers.empty:
            fig.add_trace(go.Scatter(
                x=outliers.index, y=outliers.values,
                mode="markers", name="Outliers",
                marker=dict(color="orange", size=7, symbol="circle")
            ))

        fig.update_layout(
            title=f"SPC Analysis for {group} ({selected_area})",
            xaxis_title="Time",
            yaxis_title="Production (kWh)",
            template="plotly_white",
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")

# ==========================================================
# TAB 2 — LOF ANOMALY DETECTION
# ==========================================================
with tab2:
    st.subheader("Anomaly Detection using LOF")
    st.markdown("""
    This tab applies **Local Outlier Factor (LOF)** to detect unusual production patterns.
    LOF identifies anomalies based on how isolated a point is compared to its neighbors.
    """)

    # User control for anomaly detection sensitivity
    contamination = st.slider("Select proportion of anomalies (LOF contamination):", 0.001, 0.05, 0.01, step=0.001)

    for group in selected_groups:
        df_group = df_filtered[df_filtered["production_group"] == group]["production_kwh"].to_frame()

        if len(df_group) < 10:
            st.warning(f"⚠️ Not enough data for LOF analysis for {group}.")
            continue

        # --- Fit LOF Model ---
        lof = LocalOutlierFactor(n_neighbors=20, contamination=contamination)
        df_group["lof_outlier"] = lof.fit_predict(df_group[["production_kwh"]])
        df_group["anomaly_score"] = -lof.negative_outlier_factor_
        anomalies = df_group[df_group["lof_outlier"] == -1]

        # --- Display metrics ---
        st.markdown(f"### 🔍 Production Group: {group}")
        col1, col2 = st.columns(2)
        col1.metric("Detected Anomalies", f"{len(anomalies)}")
        col2.metric("Contamination Rate", f"{contamination * 100:.1f}%")

        # --- Plot LOF chart ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_group.index, y=df_group["production_kwh"], mode="lines", name="Production"))

        if not anomalies.empty:
            fig.add_trace(go.Scatter(
                x=anomalies.index, y=anomalies["production_kwh"],
                mode="markers", name="Anomalies",
                marker=dict(color="red", size=7, symbol="diamond")
            ))

        fig.update_layout(
            title=f"LOF Anomaly Detection for {group} ({selected_area})",
            xaxis_title="Time",
            yaxis_title="Production (kWh)",
            template="plotly_white",
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
