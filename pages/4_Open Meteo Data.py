import streamlit as st
import plotly.express as px
import utils
import calendar
import pandas as pd

st.set_page_config(page_title="Weather Statistics", layout="wide")
st.title("🌤️ Open Meteo Weather Data")

# --- 1. CONTROLS ---
col1, col2 = st.columns(2)

with col1:
    # Year Selector (2021-2024)
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

with col2:
    # Area Selector (Defaults to global selection, but adjustable here)
    all_areas = sorted(list(utils.CITIES.keys()))
    default_area = st.session_state.get("selected_price_area", "NO1")
    
    # Ensure default is in list
    if default_area not in all_areas: default_area = "NO1"
    
    selected_area = st.selectbox("Select Price Area", all_areas, index=all_areas.index(default_area))

# --- 2. FETCH DATA ---
city = utils.CITIES[selected_area]
st.caption(f"Data for **{city['city']} ({selected_area})** @ {city['lat']}, {city['lon']}")

with st.spinner(f"Fetching weather data for {selected_year}..."):
    # Construct start/end dates based on selection
    start_date = f"{selected_year}-01-01"
    end_date = f"{selected_year}-12-31"
    
    df = utils.fetch_weather_api(city["lat"], city["lon"], start_date, end_date)

if df.empty:
    st.error("No weather data available.")
    st.stop()

# Add month column for filtering/grouping
df["month"] = df["time"].dt.month

# --- 3. TABS ---
tab1, tab2 = st.tabs(["📊 Data Table & Trends", "📈 Interactive Plot"])

# --- TAB 1: TABLE WITH SPARKLINES ---
with tab1:
    st.subheader(f"Weather Statistics ({selected_year})")
    
    # Create a summary dataframe
    # We list the full year's data in a list for the Sparkline column
    summary_data = []
    for var in utils.WEATHER_VARS:
        summary_data.append({
            "Variable": var,
            "Min": df[var].min(),
            "Max": df[var].max(),
            "Average": round(df[var].mean(), 2),
            "Annual Trend": df[var].tolist() # List of all values for sparkline
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    # Display with Streamlit's LineChartColumn
    st.dataframe(
        summary_df, 
        column_config={
            "Annual Trend": st.column_config.LineChartColumn(
                f"Trend ({selected_year})", 
                y_min=0, 
                y_max=None
            )
        },
        hide_index=True, 
        use_container_width=True
    )

# --- TAB 2: PLOT ---
with tab2:
    st.subheader("Variable Visualization")
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        # Month Range Slider
        months = list(calendar.month_name)[1:] # ['January', ... 'December']
        m_range = st.select_slider("Select Month Range", options=months, value=(months[0], months[-1]))
        
        start_idx = months.index(m_range[0]) + 1
        end_idx = months.index(m_range[1]) + 1
    
    with c2:
        # Variable Selector
        var = st.selectbox("Select Variable to Plot", utils.WEATHER_VARS)
    
    # Filter Data
    subset = df[(df["month"] >= start_idx) & (df["month"] <= end_idx)]
    
    # Plot
    fig = px.line(
        subset, 
        x='time', 
        y=var, 
        title=f"{var} in {selected_area} ({m_range[0]} - {m_range[1]} {selected_year})",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)