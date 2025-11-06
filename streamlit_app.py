# page_1_welcome.py
import streamlit as st

st.set_page_config(page_title="IND320 PROJECT", layout="wide")
st.title("IND320 PROJECT")
st.header("Welcome to the Weather Data Exploration App")

st.markdown(
    "<p style='color:blue; font-size:20px;'>Here, you can explore Norwegian electricity production and weather data interactively.</p>",
    unsafe_allow_html=True
)

st.subheader("DATASET")
st.markdown("- Elhub electricity production 2021 (CSV / API)")
st.markdown("- Open-Meteo ERA5 weather reanalysis")
