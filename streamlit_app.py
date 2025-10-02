import streamlit as st

# Setting page configuration
st.set_page_config(page_title="IND320 PROJECT", layout="wide")

# Main page content
st.title("IND320 PROJECT")
st.header("Welcome to the Weather Data Exploration App")

# Colored text
st.markdown(
    "<p style='color:blue; font-size:20px;'>Here, you can explore the weather dataset through various interactive pages.</p>",
    unsafe_allow_html=True
)

st.markdown(
    """
    <h4 style='color:green;'>Dataset Used</h4>
    <ul>
        <li><span style='color:orange;'>open-meteo-subset.csv</span>
    
    </ul>
    """,
    unsafe_allow_html=True
)
