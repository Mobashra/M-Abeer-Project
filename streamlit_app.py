# page_1_welcome.py
import streamlit as st

st.set_page_config(page_title="IND320 PROJECT", layout="wide")

# Title and subtitle
st.title("Norwegian Electricity & Weather Data Explorer")
st.header("Welcome!")

# Info box with introduction
st.info("This interactive app lets you explore Norwegian electricity production and weather data for 2021.")
st.markdown(":violet-badge[Use the navigation on the left to move through the pages.]")

st.divider()

# Data Source Description
st.subheader("Data Sources")

st.markdown("""
**Elhub Electricity Production (2021)**  
🔗 [Elhub API](https://api.elhub.no)  
- Provides hourly electricity **production data** for each Norwegian **price area** and **production group**.  

**Open-Meteo ERA5 Weather Reanalysis**  
🔗 [Open-Meteo API](https://open-meteo.com/en/docs)  
- Offers hourly weather parameters such as **temperature**, **precipitation**, **wind speed**, **gusts**, and **direction**.  
""")


st.divider()

# Tips for users
st.subheader("User Guidance")
st.success(
    "- Start by selecting a **price area** on the [Elhub API Data](https://m-abeer-project.streamlit.app/Elhub_API_Data) page.\n"
    "- Use the tabs in each page to explore different analyses.\n"
    "- Hover over charts to see detailed values and trends.")
