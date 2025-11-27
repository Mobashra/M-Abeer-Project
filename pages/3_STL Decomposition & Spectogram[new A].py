import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import utils
import analysis_functions as af


st.set_page_config(page_title="Time Series Decomposition", layout="wide")


# --- 1. TITLE & CONFIG ---
st.title("Time Series Decomposition and Frequency Analysis")


if "selected_price_area" not in st.session_state:
   st.session_state["selected_price_area"] = "NO1"


current_area = st.session_state["selected_price_area"]


# --- 2. GLOBAL CONTROLS (Sidebar) ---
with st.sidebar:
   st.header("Data Settings")
   data_type = st.radio("Data Source", ["Production", "Consumption"])
   selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)


# --- 3. LOAD DATA ---
# We use the raw hourly loader
with st.spinner(f"Fetching hourly data for {current_area} ({selected_year})..."):
   df = utils.load_yearly_data(data_type, selected_year)


if df.empty:
   st.warning(f"No data found for {selected_year}.")
   st.stop()


# --- 4. INFO BOX (The Blue Box in your image) ---
# Filter for current area
df_area = df[df['price_area'] == current_area].copy()


# Standardize group column
if 'group' not in df_area.columns:
   if 'production_group' in df_area.columns: df_area.rename(columns={'production_group': 'group'}, inplace=True)
   elif 'consumption_group' in df_area.columns: df_area.rename(columns={'consumption_group': 'group'}, inplace=True)


# Get available groups
available_groups = sorted(df_area["group"].unique())
group_str = ", ".join([g.capitalize() for g in available_groups])


# Render the "Scope" box
st.info(f"""
**Analysis Scope (by explorer page configuration):**
* **Price Area:** {current_area}
* **Available Groups:** {group_str}
""")


# --- 5. MAIN SELECTION ---
selected_group = st.selectbox("Select Production Group for Detailed Analysis:", available_groups, index=0)


# Prepare Series
mask = df_area["group"] == selected_group
# Smart column detection
val_col = 'mwh' if 'mwh' in df_area.columns else 'value'
if val_col not in df_area.columns: val_col = 'quantityKwh'


series = df_area[mask].set_index("date")[val_col].asfreq("h").interpolate(method="time")


if series.empty:
   st.error("Not enough data points.")
   st.stop()


# --- 6. TABS ---
tab1, tab2 = st.tabs(["STL Decomposition", "Spectrogram"])


# --- TAB 1: STL DECOMPOSITION ---
with tab1:
   st.markdown(f"### Seasonal-Trend Decomposition (STL): {selected_group.capitalize()} in {current_area}")
  
   # --- HORIZONTAL PARAMETERS (Like your image) ---
   with st.container():
       c1, c2, c3 = st.columns(3)
       with c1:
           period = st.number_input("Period (e.g., 168 for weekly)", min_value=2, value=168, step=1)
       with c2:
           seasonal = st.number_input("Seasonal Smoothing (Odd)", min_value=3, value=13, step=2)
       with c3:
           trend = st.number_input("Trend Smoothing (Odd)", min_value=3, value=169, step=2)
          
       # Hidden robust option (or add a 4th column)
       robust = True


   st.divider()


   try:
       res = af.compute_stl(series, period=period, seasonal=seasonal, trend=trend, robust=robust)
      
       # Plotting
       fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                           subplot_titles=("Observed", "Trend", "Seasonal", "Remainder"),
                           vertical_spacing=0.05)
      
       # Thin lines for a cleaner look
       fig.add_trace(go.Scatter(x=res.observed.index, y=res.observed, name="Observed", line=dict(width=1, color='#1f77b4')), row=1, col=1)
       fig.add_trace(go.Scatter(x=res.trend.index, y=res.trend, name="Trend", line=dict(width=1.5, color='#ff7f0e')), row=2, col=1)
       fig.add_trace(go.Scatter(x=res.seasonal.index, y=res.seasonal, name="Seasonal", line=dict(width=1, color='#2ca02c')), row=3, col=1)
       fig.add_trace(go.Scatter(x=res.resid.index, y=res.resid, name="Remainder", line=dict(width=0.5, color='#7f7f7f')), row=4, col=1)
      
       fig.update_layout(height=900, showlegend=False, template="plotly_white")
       st.plotly_chart(fig, use_container_width=True)
      
   except Exception as e:
       st.error(f"STL Failed: {e}")


# --- TAB 2: SPECTROGRAM ---
with tab2:
   st.markdown(f"### Frequency Analysis: {selected_group.capitalize()}")
  
   # Horizontal Params for Spectrogram too
   c1, c2 = st.columns(2)
   with c1:
       win_len = st.number_input("Window Length", min_value=10, max_value=1000, value=256, step=10)
   with c2:
       overlap = st.number_input("Window Overlap", min_value=0, max_value=win_len-1, value=int(win_len/2), step=10)


   try:
       f, t, Sxx = af.compute_spectrogram(series, window_length=win_len, overlap=overlap)
      
       fig = go.Figure(data=go.Heatmap(
           z=Sxx, x=t, y=f,
           colorscale="Viridis",
           colorbar=dict(title="Power (dB)")
       ))
      
       fig.update_layout(
           title="Spectrogram (Intensity of Cycles)",
           yaxis_title="Frequency (cycles/hour)",
           xaxis_title="Time",
           yaxis_range=[0, 0.1],
           template="plotly_white",
           height=600
       )
       st.plotly_chart(fig, use_container_width=True)
      
   except Exception as e:
       st.error(f"Spectrogram Failed: {e}")
