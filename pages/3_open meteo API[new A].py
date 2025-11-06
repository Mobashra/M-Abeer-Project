import streamlit as st
import pandas as pd
import numpy as np
from pymongo import MongoClient
from statsmodels.tsa.seasonal import STL
from scipy.signal import spectrogram
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Streamlit page setup ---
st.set_page_config(page_title="Elhub Analysis (STL & Spectrogram)", layout="wide")
st.title("⚡ Elhub Production Analysis: STL & Spectrogram")

# --- Check for selected price area (from page 2) ---
if "selected_price_area" not in st.session_state:
    st.warning("⚠️ Please select a price area on the 'Elhub API Data' page first.")
    st.stop()

selected_area = st.session_state["selected_price_area"]
st.subheader(f"Selected Price Area: {selected_area}")

# --- MongoDB connection ---
@st.cache_resource
def get_mongo_collection():
    client = MongoClient(st.secrets["mongo"]["uri"])
    db = client[st.secrets["mongo"]["database"]]
    collection = db[st.secrets["mongo"]["collection"]]
    return collection

collection = get_mongo_collection()

# --- Load and filter data ---
@st.cache_data(ttl=600)
def load_elhub_data(price_area: str):
    data = list(collection.find({"price_area": price_area}))
    df = pd.DataFrame(data)

    if df.empty:
        return df

    df["production_group"] = df["production_group"].fillna("Unknown")
    df["date"] = pd.to_datetime(df["start_time"], unit="ms")
    df.rename(columns={"value": "production_mwh"}, inplace=True)
    df = df[df["date"].dt.year == 2021]
    df = df.sort_values("date")
    return df

with st.spinner(f"Loading data for {selected_area} from MongoDB..."):
    df_area = load_elhub_data(selected_area)

if df_area.empty:
    st.error(f"No data found for {selected_area}.")
    st.stop()

st.success(f"✅ Data loaded for {selected_area} (2021)")
st.caption("Source: Elhub API → MongoDB → Streamlit")

# --- Tabs for STL and Spectrogram ---
tab_stl, tab_spec = st.tabs(["📈 STL Decomposition", "🎵 Spectrogram"])

# ====================================================================================
# TAB 1: STL DECOMPOSITION
# ====================================================================================
with tab_stl:
    st.subheader("STL (Seasonal-Trend Decomposition using LOESS)")

    # Select production group
    production_groups = sorted(df_area["production_group"].unique())
    selected_group = st.selectbox("Select Production Group:", production_groups)

    df_filtered = df_area[df_area["production_group"] == selected_group]

    if df_filtered.empty:
        st.warning("No data for this production group.")
    else:
        # Aggregate by hour
        df_ts = (
            df_filtered.groupby("date")["production_mwh"]
            .sum()
            .asfreq("h")
            .interpolate(method="time")
        )

        st.info("Performing STL decomposition with weekly periodicity (period=24×7).")
        stl = STL(df_ts, period=24 * 7, robust=True).fit()
        
       

# --- Create Plotly 4-row subplot ---
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(
                "Original Series",
                "Trend Component",
                "Seasonal Component",
                "Residuals"
            )
        )

        fig.add_trace(go.Scatter(x=df_ts.index, y=df_ts, name="Original", line=dict(width=1.2, color="royalblue")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_ts.index, y=stl.trend, name="Trend", line=dict(width=1.2, color="darkorange")), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_ts.index, y=stl.seasonal, name="Seasonal", line=dict(width=1.2, color="green")), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_ts.index, y=stl.resid, name="Residuals", line=dict(width=1.2, color="crimson")), row=4, col=1)

        fig.update_layout(
            height=900,
            title_text=f"STL Decomposition – {selected_group} ({selected_area}, 2021)",
            showlegend=False,
            template="plotly_white",
            margin=dict(t=80, b=40)
        )

        fig.update_xaxes(title_text="Time", row=4, col=1)
        fig.update_yaxes(title_text="Production (MWh)", row=1, col=1)

        st.plotly_chart(fig, use_container_width=True)

        
        
        
        
        
        
        
        
        
        
        


# ====================================================================================
# TAB 2: SPECTROGRAM
# ====================================================================================
with tab_spec:
    st.subheader("Spectrogram Analysis")

    production_groups = sorted(df_area["production_group"].unique())
    selected_group = st.selectbox(
        "Select Production Group for Spectrogram:",
        production_groups,
        key="spec_group"
    )

    df_filtered = df_area[df_area["production_group"] == selected_group]

    if df_filtered.empty:
        st.warning("No data for this production group.")
    else:
        df_ts = (
            df_filtered.groupby("date")["production_mwh"]
            .sum()
            .asfreq("h")
            .interpolate(method="time")
        )

        # Parameters for spectrogram
        window_length = st.number_input("Window Length (hours)", min_value=2, value=168, step=1)
        window_overlap = st.number_input("Window Overlap (hours)", min_value=0, value=84, step=1)

        # Compute spectrogram
        fs = 1  # 1 sample/hour
        f, t, Sxx = spectrogram(df_ts.values, fs=fs, nperseg=window_length, noverlap=window_overlap)
        Sxx_dB = 10 * np.log10(Sxx + 1e-9)

        # Convert t → timestamps for x-axis
        time_axis = df_ts.index[0] + pd.to_timedelta(t, unit="h")

        fig_spec = go.Figure(
            data=go.Heatmap(
                z=Sxx_dB,
                x=time_axis,
                y=f,
                colorscale="Viridis",
                colorbar=dict(title="Power (dB)"),
            )
        )
        fig_spec.update_layout(
            title=f"Spectrogram – {selected_group} ({selected_area}, 2021)",
            xaxis_title="Time",
            yaxis_title="Frequency (1/hour)",
            template="plotly_white",
        )

        st.plotly_chart(fig_spec, use_container_width=True)
