import streamlit as st

# Set page configuration
st.set_page_config(page_title="IND320 PROJECT", layout="wide")

# Main page content
st.title("IND320 PROJECT")
st.header("Weather Data Exploration App")
st.write("Here, you can explore the weather dataset through various interactive pages.")
st.markdown(
    """
    **Dataset**  
    - `open-meteo-subset.csv`: A subset of weather data from Open-Meteo, including variables like temperature, humidity, wind speed, and more.
    """
)
