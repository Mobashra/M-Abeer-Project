# page_1_welcome.py
import streamlit as st

st.set_page_config(page_title="IND320 PROJECT", layout="wide")

# Title and subtitle
st.title("Norwegian Electricity & Weather Data Explorer")
st.header("Welcome!")

# Info box with introduction
st.info("This interactive app lets you explore Norwegian electricity production and weather data for 2021. "
    "Use the navigation on the left to move through the pages.")

st.divider()

# Data sources section
st.subheader("Data Sources")
st.write("1. **Elhub electricity production 2021**")
st.write("   - Data retrieved from the [Elhub API](https://api.elhub.no)")
st.write("   - Includes production per price area and production group.")
st.write("2. **Open-Meteo ERA5 weather reanalysis**")
st.write("   - Hourly weather data for selected Norwegian cities: temperature, precipitation, wind speed/gust/direction.")

st.divider()

# Tips for users
st.subheader("User Guidance")
st.success(
    "- Start by selecting a **price area** on the 'Elhub API Data' page.\n"
    "- Use the tabs in each page to explore different analyses.\n"
    "- Hover over charts to see detailed values and trends.\n"
    "- SPC and LOF analyses help detect unusual patterns in production data."
)
