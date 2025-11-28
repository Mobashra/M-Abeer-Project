import streamlit as st
import plotly.express as px
import utils

st.set_page_config(page_title="Weather Stats", layout="wide")

# 1. SAFETY & STYLING
utils.check_session_state()
utils.render_sidebar()

coords = st.session_state["selected_coords"]

# 2. HEADER
st.title("🌤️ Local Weather History")
st.success(f"**Location:** Lat {coords['lat']:.4f}, Lon {coords['lon']:.4f}")

# 3. CONTROLS
c1, c2 = st.columns([1, 3])
with c1:
    year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=2)
with c2:
    vars_to_plot = st.multiselect("Variables to Plot", utils.WEATHER_VARS, default=["temperature_2m", "wind_speed_10m"])

# 4. LOAD DATA
with st.spinner(f"Fetching ERA5 reanalysis data for {year}..."):
    df = utils.fetch_weather_api(coords['lat'], coords['lon'], f"{year}-01-01", f"{year}-12-31")

if df.empty:
    st.error("Weather data unavailable.")
    st.stop()

# 5. VISUALIZATION
st.divider()

if vars_to_plot:
    is_norm = st.checkbox("Normalize Values (0-1 Scale) for Comparison", value=False)
    
    plot_df = df.copy()
    if is_norm:
        for v in vars_to_plot:
            min_v, max_v = plot_df[v].min(), plot_df[v].max()
            if max_v != min_v:
                plot_df[v] = (plot_df[v] - min_v) / (max_v - min_v)

    fig = px.line(plot_df, x='time', y=vars_to_plot, title=f"Weather Dynamics ({year})")
    fig.update_layout(hovermode="x unified", height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select variables above to visualize trends.")