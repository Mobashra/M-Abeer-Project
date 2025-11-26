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
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

with col2:
    all_areas = sorted(list(utils.CITIES.keys()))
    default_area = st.session_state.get("selected_price_area", "NO1")
    if default_area not in all_areas: default_area = "NO1"
    selected_area = st.selectbox("Select Price Area", all_areas, index=all_areas.index(default_area))

# --- 2. FETCH DATA ---
city = utils.CITIES[selected_area]
st.caption(f"Data for **{city['city']} ({selected_area})** @ {city['lat']}, {city['lon']}")

with st.spinner(f"Fetching weather data for {selected_year}..."):
    start_date = f"{selected_year}-01-01"
    end_date = f"{selected_year}-12-31"
    df = utils.fetch_weather_api(city["lat"], city["lon"], start_date, end_date)

if df.empty:
    st.error("No weather data available.")
    st.stop()

df["month"] = df["time"].dt.month

# --- 3. TABS ---
tab1, tab2 = st.tabs(["📊 Data Table & Trends", "📈 Interactive Plot"])

# --- TAB 1: TABLE ---
with tab1:
    st.subheader(f"Weather Statistics ({selected_year})")
    summary_data = []
    for var in utils.WEATHER_VARS:
        summary_data.append({
            "Variable": var,
            "Min": df[var].min(),
            "Max": df[var].max(),
            "Average": round(df[var].mean(), 2),
            "Annual Trend": df[var].tolist()
        })
    
    st.dataframe(
        pd.DataFrame(summary_data), 
        column_config={
            "Annual Trend": st.column_config.LineChartColumn(
                f"Trend ({selected_year})", y_min=0, y_max=None
            )
        },
        hide_index=True, 
        use_container_width=True
    )

# --- TAB 2: PLOT (UPDATED) ---
with tab2:
    st.subheader("Variable Visualization")
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        months = list(calendar.month_name)[1:]
        m_range = st.select_slider("Select Month Range", options=months, value=(months[0], months[-1]))
        start_idx = months.index(m_range[0]) + 1
        end_idx = months.index(m_range[1]) + 1
    
    with c2:
        # Added "All Variables" option
        plot_options = ["All Variables"] + utils.WEATHER_VARS
        selected_var = st.selectbox("Select Variable to Plot", plot_options)
    
    # Filter Data
    subset = df[(df["month"] >= start_idx) & (df["month"] <= end_idx)]
    
    # Determine Y-Axis
    if selected_var == "All Variables":
        y_data = utils.WEATHER_VARS  # Plotly will plot multiple lines
        title_text = "All Weather Variables"
    else:
        y_data = selected_var
        title_text = selected_var

    # Plot
    fig = px.line(
        subset, 
        x='time', 
        y=y_data, 
        title=f"{title_text} ({m_range[0]} - {m_range[1]} {selected_year})",
        template="plotly_white"
    )
    
    # Move legend to top so it doesn't squash the chart
    fig.update_layout(legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
    
    st.plotly_chart(fig, use_container_width=True)