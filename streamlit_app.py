import streamlit as st

# Setting page configuration
st.set_page_config(page_title="IND320 PROJECT", layout="wide")

# Main page content
st.title("IND320 PROJECT")
st.header("Welcome to the Weather Data Exploration App")

# For Colored text
st.markdown(
    "<p style='color:blue; font-size:20px;'>Here, you can explore the weather dataset through various interactive pages.</p>",
    
    # Allows to pass raw HTML inside the markdown string
    unsafe_allow_html = True
)

st.subheader("DATASET")
st.markdown("""
- open-meteo-subset.csv
""")
