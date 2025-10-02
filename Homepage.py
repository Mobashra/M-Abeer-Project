import streamlit as st

# Set page configuration
st.set_page_config(page_title="IND320 PROJECT", layout="wide")

# Main page content
st.title("IND320 PROJECT")

st.header("Weather Data Exploration App")

# Colored text
st.markdown(
    "<p style='color:blue; font-size:20px;'>Here, you can explore the weather dataset through various interactive pages.</p>",
    unsafe_allow_html=True
)

st.markdown(
    """
    <h4 style='color:green;'>Dataset Used</h4>
    <ul>
        <li><span style='color:orange;'>open-meteo-subset.csv</span>: 
        A subset of weather data from Open-Meteo, including variables like 
        <span style='color:red;'>temperature</span>, 
        <span style='color:purple;'>humidity</span>, 
        <span style='color:teal;'>wind speed</span>, and more.</li>
    </ul>
    """,
    unsafe_allow_html=True
)
