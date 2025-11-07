# page_new_B_production_analysis.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.neighbors import LocalOutlierFactor

st.set_page_config(page_title="Production Analysis (SPC & LOF)", layout="wide")
st.title("Production Analysis: Outliers/SPC & Anomalies/LOF")

# Get selected area from session state
if "selected_price_area" not in st.session_state:
    st.warning("Please select a price area in the 'Elhub API Data' page first.")
    st.stop()

selected_area = st.session_state["selected_price_area"]

# Load Elhub production data 
@st.cache_data
def load_elhub_data():
    df = pd.read_csv("elhub_2021_production.csv", parse_dates=["startTime"])
    df.rename(columns={"quantityKwh": "production_kwh"}, inplace=True)
    df["production_group"] = df["productionGroup"]
    df["price_area"] = df["priceArea"]
    df = df[df["price_area"] == selected_area]
    return df

df = load_elhub_data()

if df.empty:
    st.warning(f"No production data found for {selected_area}.")
    st.stop()

# UI selectors 
production_groups = sorted(df["production_group"].unique())
selected_groups = st.multiselect(
    "Select production group(s):",
    options=production_groups,
    default=production_groups)

# Filter data
df_filtered = df[df["production_group"].isin(selected_groups)].copy()
df_filtered.set_index("startTime", inplace=True)
df_filtered = df_filtered.sort_index()

# tabs for SPC and LOF
tab1, tab2 = st.tabs(["SPC Analysis", "LOF Analysis"])

# Tab 1: SPC / Outlier
with tab1:
    st.subheader("Outlier & SPC Analysis")
    st.markdown("""
        This tab detects outliers in electricity production using simple statistical process control (SPC) rules:
        - Upper/Lower control limits: mean ± 3*std
        - Highlights points outside limits
    """)

    for group in selected_groups:
        df_group = df_filtered[df_filtered["production_group"] == group]["production_kwh"]
        mean_val = df_group.mean()
        std_val = df_group.std()
        ucl = mean_val + 3 * std_val
        lcl = mean_val - 3 * std_val
        outliers = df_group[(df_group > ucl) | (df_group < lcl)]

        st.markdown(f"**Production Group: {group}**")
        st.markdown(f"Mean: {mean_val:.2f} kWh, Std: {std_val:.2f} kWh, UCL: {ucl:.2f}, LCL: {lcl:.2f}, Outliers: {len(outliers)}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_group.index, y=df_group, mode="lines", name="Production"))
        fig.add_trace(go.Scatter(x=df_group.index, y=[ucl]*len(df_group), mode="lines", name="UCL", line=dict(color="red", dash="dash")))
        fig.add_trace(go.Scatter(x=df_group.index, y=[lcl]*len(df_group), mode="lines", name="LCL", line=dict(color="red", dash="dash")))
        if not outliers.empty:
            fig.add_trace(go.Scatter(x=outliers.index, y=outliers.values, mode="markers", name="Outliers", marker=dict(color="orange", size=6)))
        fig.update_layout(
            title=f"SPC Analysis for {group} ({selected_area})",
            xaxis_title="Time",
            yaxis_title="Production (kWh)",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

# Tab 2: LOF Anomaly Detection
with tab2:
    st.subheader("Anomaly Detection using LOF")
    st.markdown("""
        This tab uses Local Outlier Factor (LOF) to detect anomalous production patterns.
        LOF considers how isolated each point is compared to its neighbors.
    """)

    for group in selected_groups:
        df_group = df_filtered[df_filtered["production_group"] == group]["production_kwh"].to_frame()
        if len(df_group) < 10:
            st.warning(f"Not enough data for LOF analysis for {group}.")
            continue

        # Fit LOF model
        lof = LocalOutlierFactor(n_neighbors=20, contamination=0.01)
        df_group["lof_outlier"] = lof.fit_predict(df_group[["production_kwh"]])
        df_group["anomaly_score"] = -lof.negative_outlier_factor_
        anomalies = df_group[df_group["lof_outlier"] == -1]

        st.markdown(f"**Production Group: {group}**")
        st.markdown(f"Detected anomalies: {len(anomalies)}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_group.index, y=df_group["production_kwh"], mode="lines", name="Production"))
        if not anomalies.empty:
            fig.add_trace(go.Scatter(x=anomalies.index, y=anomalies["production_kwh"], mode="markers", name="Anomalies", marker=dict(color="red", size=6)))
        fig.update_layout(
            title=f"LOF Anomaly Detection for {group} ({selected_area})",
            xaxis_title="Time",
            yaxis_title="Production (kWh)",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
