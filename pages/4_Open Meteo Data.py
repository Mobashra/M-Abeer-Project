import streamlit as st
import plotly.express as px
import utils
import calendar
import pandas as pd

st.title("Weather Data (2021)")

area = st.session_state.get("selected_price_area", "NO1")
city = utils.CITIES[area]
st.write(f"Data for **{city['city']} ({area})**")

# Fetch
df = utils.fetch_weather_api(city["latitude"], city["longitude"], "2021-01-01", "2021-12-31")

if df.empty: st.stop()

tab1, tab2 = st.tabs(["Data Table", "Plot Variable"])

with tab1:
    # Your Summary Table Logic
    df["month"] = df["time"].dt.month
    jan = df[df["month"] == 1]
    summary = pd.DataFrame({"Variable": utils.WEATHER_VARS, "Jan Trend": [jan[v].tolist() for v in utils.WEATHER_VARS]})
    st.dataframe(summary, column_config={"Jan Trend": st.column_config.LineChartColumn("Trend")}, use_container_width=True)

with tab2:
    # Your Plot Logic
    months = list(calendar.month_name)[1:]
    m_range = st.select_slider("Month Range", options=months, value=(months[0], months[-1]))
    var = st.selectbox("Variable", utils.WEATHER_VARS)
    
    start_idx = months.index(m_range[0]) + 1
    end_idx = months.index(m_range[1]) + 1
    subset = df[(df["month"] >= start_idx) & (df["month"] <= end_idx)]
    
    fig = px.line(subset, x='time', y=var, title=f"{var} ({m_range[0]}-{m_range[1]})")
    st.plotly_chart(fig, use_container_width=True)