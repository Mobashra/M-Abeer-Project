import streamlit as st
import plotly.express as px
import pandas as pd
import utils

st.set_page_config(page_title="Weather History", page_icon="🌤️", layout="wide")
st.title("🌤️ Meteorological History")


# --- SIDEBAR NAVIGATION GROUPS ---
st.sidebar.markdown("### 🗺️ Exploration")
# The pages 01, 02, 03 will appear here naturally due to sorting

if st.sidebar.checkbox("Show Advanced Modules", value=True):
    st.sidebar.markdown("### 🔍 Diagnostics")
    # Pages 04, 05, 06 fall here visually
    
    st.sidebar.markdown("### 🔮 Prediction")
    # Pages 07, 08 fall here visually


# --- GLOBAL STATE CHECK ---
if "selected_coords" not in st.session_state:
    st.error("Please select a location on the Home Map first.")
    st.stop()

coords = st.session_state["selected_coords"]
area = st.session_state.get("selected_price_area", "Unknown")

st.sidebar.info(f"**Location:** {area}\n\nLat: {coords['lat']:.2f}, Lon: {coords['lon']:.2f}")

# --- CONTROLS ---
selected_year = st.sidebar.selectbox("Year", [2021, 2022, 2023, 2024], index=0)

# --- FETCH DATA ---
with st.spinner("Fetching ERA5 Reanalysis data..."):
    # Fetch full year
    df = utils.fetch_weather_api(
        coords['lat'], coords['lon'], 
        f"{selected_year}-01-01", f"{selected_year}-12-31"
    )

if df.empty:
    st.error("Could not retrieve weather data.")
    st.stop()

# --- TABS FOR REQUIREMENTS ---
tab1, tab2 = st.tabs(["📊 Statistical Overview", "📈 Deep Dive Plotter"])

with tab1:
    st.markdown("### First Month Trend & Annual Statistics")
    
    # Create Summary Stats
    summary = []
    df['Month'] = df['time'].dt.month
    
    for var in utils.WEATHER_VARS:
        jan_data = df[df['Month'] == 1][var].tolist()
        summary.append({
            "Metric": var.replace("_", " ").title(),
            "Avg": df[var].mean(),
            "Min": df[var].min(),
            "Max": df[var].max(),
            "January Trend": jan_data # For Sparkline
        })
    
    df_summ = pd.DataFrame(summary)
    
    st.dataframe(
        df_summ,
        column_config={
            "January Trend": st.column_config.LineChartColumn(y_min=0, y_max=None),
            "Avg": st.column_config.NumberColumn(format="%.2f"),
        },
        use_container_width=True,
        hide_index=True
    )

with tab2:
    st.subheader("Custom Weather Plots")
    vars_to_plot = st.multiselect("Select Variables", utils.WEATHER_VARS, default=["temperature_2m"])
    
    if vars_to_plot:
        # Normalize Option
        normalize = st.checkbox("Normalize Data (0-1 Scale)", help="Useful for comparing Wind vs Temp")
        
        plot_df = df.copy()
        if normalize:
            for v in vars_to_plot:
                plot_df[v] = (plot_df[v] - plot_df[v].min()) / (plot_df[v].max() - plot_df[v].min())
        
        fig = px.line(plot_df, x='time', y=vars_to_plot)
        fig.update_layout(hovermode="x unified", height=500)
        st.plotly_chart(fig, use_container_width=True)