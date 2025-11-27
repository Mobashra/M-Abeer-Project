import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import utils
from plotly.subplots import make_subplots


st.set_page_config(page_title="Correlation Analysis", layout="wide")
st.title("🔗 Sliding Window Correlation")
st.markdown("Analyze how **Weather** drivers impact **Energy** patterns over time.")


# --- 1. GLOBAL SETTINGS ---
if "selected_price_area" not in st.session_state:
   st.session_state["selected_price_area"] = "NO1"
   default = utils.CITIES["NO1"]
   st.session_state["selected_coords"] = {"lat": default["lat"], "lon": default["lon"]}


current_area = st.session_state["selected_price_area"]
coords = st.session_state["selected_coords"]


# Blue Context Box
st.info(f"**Analysis Scope:** {current_area} ({coords['lat']:.2f}, {coords['lon']:.2f})")


# --- 2. CONTROLS ---
# Row 1: Data Selection
c1, c2, c3 = st.columns(3)


with c1:
   selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)
   data_type = st.radio("Energy Type", ["Production", "Consumption"], horizontal=True)


# Load Energy Data First (to populate groups)
with st.spinner(f"Loading {data_type} data..."):
   df_energy = utils.load_yearly_data(data_type, selected_year)


if df_energy.empty:
   st.error(f"No energy data found for {selected_year}.")
   st.stop()


# Filter Energy by Area
df_energy_area = df_energy[df_energy['price_area'] == current_area]
available_groups = sorted(df_energy_area['group'].unique())


with c2:
   selected_group = st.selectbox(f"Select {data_type} Group", available_groups, index=0)
   selected_weather = st.selectbox("Select Weather Variable", utils.WEATHER_VARS, index=2) # Default to Wind Speed


with c3:
   # Analysis Parameters
   window_size = st.number_input("Window Size (Hours)", min_value=6, value=168, step=12, help="Size of the sliding window (168h = 1 Week)")
   lag = st.number_input("Lag (Hours)", min_value=-48, max_value=48, value=0, help="Shift weather relative to energy. Positive = Weather leads.")


# --- 3. DATA PREPARATION (THE FIX) ---
with st.spinner("Aligning datasets..."):
   # A. Prepare Energy Series (Hourly)
   energy_series = df_energy_area[df_energy_area['group'] == selected_group].set_index('date')['mwh']
   energy_series = energy_series.sort_index().asfreq('h').interpolate(method='time')


   # B. Fetch Weather Data
   # We fetch the exact year to match the energy data
   df_weather = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{selected_year}-01-01", f"{selected_year}-12-31")
  
   if df_weather.empty:
       st.error("No weather data found.")
       st.stop()


   # C. Standardize Weather Index
   # 1. Force UTC-aware
   df_weather['time'] = pd.to_datetime(df_weather['time'], utc=True)
   # 2. Convert to Oslo time (Same as Energy)
   df_weather['time'] = df_weather['time'].dt.tz_convert("Europe/Oslo")
  
   weather_series = df_weather.set_index('time')[selected_weather]
   weather_series = weather_series.sort_index().asfreq('h').interpolate(method='time')


   # D. Intersection (Align indices)
   common_idx = energy_series.index.intersection(weather_series.index)
  
   if len(common_idx) < 24:
       st.error(f"Date mismatch: Energy and Weather data do not overlap sufficiently for {selected_year}.")
       st.write(f"Energy Range: {energy_series.index.min()} to {energy_series.index.max()}")
       st.write(f"Weather Range: {weather_series.index.min()} to {weather_series.index.max()}")
       st.stop()
      
   ts_energy = energy_series.loc[common_idx]
   ts_weather = weather_series.loc[common_idx]


# --- 4. CALCULATIONS ---
# Apply Lag
ts_weather_shifted = ts_weather.shift(lag)


# Rolling Correlation
rolling_corr = ts_energy.rolling(window=window_size).corr(ts_weather_shifted)


# Statistics
avg_corr = rolling_corr.mean()
max_corr = rolling_corr.max()
min_corr = rolling_corr.min()


# --- 5. VISUALIZATION ---
st.divider()


# Metrics Row
m1, m2, m3, m4 = st.columns(4)
m1.metric("Avg Correlation", f"{avg_corr:.2f}")
m2.metric("Max Correlation", f"{max_corr:.2f}")
m3.metric("Min Correlation", f"{min_corr:.2f}")
m4.metric("Data Points", len(common_idx))


# Plot 1: Correlation
st.subheader("1. Correlation Dynamics")
st.caption(f"Shows how the relationship between **{selected_weather}** and **{selected_group}** changes over time.")


fig_corr = go.Figure()
fig_corr.add_trace(go.Scatter(
   x=rolling_corr.index, y=rolling_corr,
   mode='lines', name='Correlation',
   line=dict(color='#636EFA', width=2)
))
fig_corr.add_hline(y=0, line_dash="dash", line_color="gray")
fig_corr.update_layout(
   height=400, template="plotly_white",
   yaxis=dict(title="Correlation (-1 to 1)", range=[-1.1, 1.1]),
   margin=dict(l=40, r=40, t=20, b=40)
)
st.plotly_chart(fig_corr, use_container_width=True)


# Plot 2: Dual Axis Comparison
st.subheader("2. Visual Comparison")
st.caption("Directly compare the two time series to verify the relationship visually.")


fig_dual = make_subplots(specs=[[{"secondary_y": True}]])


# Trace 1: Energy
fig_dual.add_trace(
   go.Scatter(x=ts_energy.index, y=ts_energy, name=f"Energy ({selected_group})",
              line=dict(color='#EF553B', width=1.5)),
   secondary_y=False
)


# Trace 2: Weather
fig_dual.add_trace(
   go.Scatter(x=ts_weather.index, y=ts_weather, name=f"Weather ({selected_weather})",
              line=dict(color='#00CC96', width=1.5, dash='dot')),
   secondary_y=True
)


fig_dual.update_layout(
   height=500, template="plotly_white",
   legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"),
   margin=dict(l=40, r=40, t=20, b=40)
)
fig_dual.update_yaxes(title_text="Energy (MWh)", secondary_y=False)
fig_dual.update_yaxes(title_text=selected_weather, secondary_y=True)


st.plotly_chart(fig_dual, use_container_width=True)


st.info("""
**Interpretation Guide:**
* **Positive (near +1):** When weather goes UP, Energy goes UP (e.g., High Wind = High Production).
* **Negative (near -1):** When weather goes UP, Energy goes DOWN (e.g., High Temp = Low Heating Consumption).
* **Zero:** No clear relationship.
""")
