import streamlit as st
import pandas as pd
import numpy as np
from pymongo import MongoClient
from statsmodels.tsa.seasonal import STL
from scipy.signal import spectrogram
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# STREAMLIT PAGE SETUP 
st.set_page_config(page_title="Elhub Analysis (STL & Spectrogram)", layout="wide")
st.title("Elhub Production Analysis: STL & Spectrogram") # Page title

# CHECK SELECTED PRICE AREA 
if "selected_price_area" not in st.session_state:
    # If the user has not selected a price area previously, show warning and stop
    st.warning("Please select a price area on the 'Elhub API Data' page first.")
    st.stop()

# Retrieve the selected price area from the session state
selected_area = st.session_state["selected_price_area"]
st.subheader(f"Selected Price Area: {selected_area}")

# MONGODB CONNECTION 
@st.cache_resource # Caches the connection so it is reused on page reloads.
def get_mongo_collection():
    client = MongoClient(st.secrets["mongo"]["uri"])
    db = client[st.secrets["mongo"]["database"]]
    collection = db[st.secrets["mongo"]["collection"]]
    return collection

# Initialize collection
collection = get_mongo_collection()

# DATA LOADING 
@st.cache_data(ttl=600)
def load_elhub_data(price_area: str) -> pd.DataFrame:
    data = list(collection.find({"price_area": price_area}))  # Fetch all records for the price area
    df = pd.DataFrame(data)

    if df.empty:
        return df  # Return empty DataFrame if no data found

    # Fill missing production groups with "Unknown"
    df["production_group"] = df["production_group"].fillna("Unknown")

    # Convert timestamps from milliseconds to datetime in Oslo timezone
    df["date"] = pd.to_datetime(df["start_time"], unit="ms").dt.tz_convert("Europe/Oslo")

    # Rename production column for consistency
    df.rename(columns={"value": "production_mwh"}, inplace=True)

    # Filter to include only data from 2021
    df = df[df["date"].dt.year == 2021]

    # Sort by datetime to ensure correct time order
    df = df.sort_values("date")

    return df

# Load data for the selected area
with st.spinner(f"Loading data for {selected_area}"):
    df_area = load_elhub_data(selected_area)

# Stop execution if no data is available
if df_area.empty:
    st.error(f"No data found for {selected_area}.")
    st.stop()

st.success(f"Data loaded for {selected_area} (2021)")


# HELPER FUNCTIONS 
def prepare_hourly_series(df: pd.DataFrame, group_col: str, value_col: str = "production_mwh") -> pd.Series:
   
    df_filtered = df[df["production_group"] == group_col]
    # Group by datetime, sum production if multiple records exist per hour, reindex hourly, interpolate missing
    series = df_filtered.groupby("date")[value_col].sum().asfreq("h").interpolate(method="time")
    return series # Returns a pandas Series indexed by hourly datetime.


# STL DECOMPOSITION
def compute_stl(series: pd.Series, period: int = 24*7, robust: bool = True):
    stl_result = STL(series, period=period, robust=robust).fit()
    return stl_result



#Plot the components of STL decomposition using Plotly subplots
#Original series, Trend, Seasonal, Residuals.
def plot_stl(series: pd.Series, stl_result, title: str):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=("Original Series", "Trend Component", "Seasonal Component", "Residuals"))

    # Add traces for each component
    fig.add_trace(go.Scatter(x=series.index, y=series, name="Original", line=dict(width=1.2, color="royalblue")), row=1, col=1)
    fig.add_trace(go.Scatter(x=series.index, y=stl_result.trend, name="Trend", line=dict(width=1.2, color="darkorange")), row=2, col=1)
    fig.add_trace(go.Scatter(x=series.index, y=stl_result.seasonal, name="Seasonal", line=dict(width=1.2, color="green")), row=3, col=1)
    fig.add_trace(go.Scatter(x=series.index, y=stl_result.resid, name="Residuals", line=dict(width=1.2, color="crimson")), row=4, col=1)

    # Set layout and axis labels
    fig.update_layout(height=900, title_text=title, showlegend=False, template="plotly_white", margin=dict(t=80, b=40))
    fig.update_xaxes(title_text="Time", row=4, col=1)
    fig.update_yaxes(title_text="Production (MWh)", row=1, col=1)

    return fig

# SPECTROGRAM COMPUTATION AND PLOTTING
def compute_spectrogram(series: pd.Series, window_length: int = 168, window_overlap: int = 84):
    """series (pd.Series): Hourly production time series.
       window_length (int): Number of samples per FFT segment (controls frequency resolution) -> 168 for weekly.
       window_overlap (int): Number of overlapping samples between segments (controls smoothing) -> 84 for 50% overlap.
    """

    fs = 1  # Sampling frequency: 1 sample per hour

    # Compute spectrogram:
    f, t, Sxx = spectrogram(series.values,fs=fs, nperseg=window_length, noverlap=window_overlap, window='hann', scaling='density',
        mode='psd') # Power Spectral Density

    # Convert power to decibels for better visualization
    # Adding a tiny value (1e-9) avoids log(0)
    Sxx_dB = 10 * np.log10(Sxx + 1e-9)

    # Convert time bins (t) to actual timestamps for x-axis:
    # t is in hours since the start of the series
    time_axis = series.index[0] + pd.to_timedelta(t, unit="h")

    # f: frequency axis, in cycles per hour
    # t_axis: timestamps corresponding to each FFT segment
    # Sxx_dB: spectrogram power in dB, shape = (len(f), len(t))
    return f, time_axis, Sxx_dB


# SPECTROGRAM PLOTTING 
def plot_spectrogram(f, t_axis, Sxx_dB, title: str):

    fig = go.Figure(
        data=go.Heatmap(
            z=Sxx_dB,          # Power values (dB)
            x=t_axis,          # Time axis
            y=f,               # Frequency axis
            colorscale="Viridis",
            colorbar=dict(title="Power (dB)")))

    # Set axis labels and title
    fig.update_layout(title=title, xaxis_title="Time", yaxis_title="Frequency (cycles/hour)", template="plotly_white")

    return fig

  

# STREAMLIT TABS 
tab_stl, tab_spec = st.tabs(["STL Decomposition", "Spectrogram"])


# TAB 1: STL
with tab_stl:
    st.subheader("STL (Seasonal-Trend Decomposition using LOESS)")
    production_groups = sorted(df_area["production_group"].unique())
    selected_group = st.selectbox("Select Production Group:", production_groups)
    series = prepare_hourly_series(df_area, selected_group)
    
    if series.empty:
        st.warning("No data for this production group.")
    else:
        stl_result = compute_stl(series)
        fig_stl = plot_stl(series, stl_result, f"STL Decomposition – {selected_group} ({selected_area}, 2021)")
        st.plotly_chart(fig_stl, use_container_width=True)

# TAB 2: SPECTROGRAM
with tab_spec:
    st.subheader("Spectrogram Analysis")
    selected_group_spec = st.selectbox("Select Production Group for Spectrogram:", production_groups, key="spec_group")
    series_spec = prepare_hourly_series(df_area, selected_group_spec)
    
    if series_spec.empty:
        st.warning("No data for this production group.")
    else:
        # User-defined parameters for spectrogram
        window_length = st.number_input("Window Length (hours)", min_value=2, value=168, step=1)
        window_overlap = st.number_input("Window Overlap (hours)", min_value=0, value=84, step=1)

        # Compute spectrogram
        f, t_axis, Sxx_dB = compute_spectrogram(series_spec, window_length, window_overlap)
        
        # Plot spectrogram
        fig_spec = plot_spectrogram(f, t_axis, Sxx_dB, f"Spectrogram - {selected_group_spec} ({selected_area}, 2021)")
        st.plotly_chart(fig_spec, use_container_width=True)
