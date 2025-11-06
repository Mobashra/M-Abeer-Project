# page_1_welcome.py
import streamlit as st

st.set_page_config(page_title="IND320 PROJECT", layout="wide")

# Title and subtitle
st.title("⚡ IND320 PROJECT – Norwegian Electricity & Weather Data Explorer")
st.header("Welcome!")

# Info box with introduction
st.info(
    "This interactive app lets you explore Norwegian electricity production and weather data for 2021. "
    "Use the navigation on the left to move through the pages."
)

st.divider()

# What you can do section
st.subheader("📊 What you can do in this app")

st.write("- **Explore electricity production by price area (Elhub API)**")
st.write("  - View production share, monthly trends, and compare production groups.")
st.write("- **Analyze weather data (Open-Meteo ERA5)**")
st.write("  - Examine temperature, precipitation, wind speed, and wind direction using tables, line charts, STL decomposition, and spectrograms.")
st.write("- **Perform production analysis**")
st.write("  - Detect outliers, monitor SPC charts, and identify anomalies using LOF for different production groups.")
st.write("- **Interactive plots**")
st.write("  - All charts are interactive (Plotly) – hover, zoom, and explore trends in detail.")
st.write("- **Customizable selection**")
st.write("  - Choose a price area, month, variable, or production group to focus your analysis.")

st.divider()

# Data sources section
st.subheader("📂 Data Sources")
st.write("1. **Elhub electricity production 2021**")
st.write("   - Data retrieved from the [Elhub API](https://api.elhub.no) and stored in MongoDB.")
st.write("   - Includes production per price area and production group.")
st.write("2. **Open-Meteo ERA5 weather reanalysis**")
st.write("   - Hourly weather data for selected Norwegian cities: temperature, precipitation, wind speed/gust/direction.")

st.divider()

# Tips for users
st.subheader("💡 Tips for Users")
st.success(
    "- Start by selecting a **price area** on the 'Elhub API Data' page.\n"
    "- Use the tabs in each page to explore different analyses.\n"
    "- Hover over charts to see detailed values and trends.\n"
    "- SPC and LOF analyses help detect unusual patterns in production data."
)
