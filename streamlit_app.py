import streamlit as st




st.set_page_config(page_title="IND320 PROJECT", layout="wide")

st.title("WELCOME TO THE IND320 PROJECT APP")
st.write("Here, you can explore the weather dataset through various interactive pages.")
st.markdown(
    """
    **Dataset**  
    - `open-meteo-subset.csv`: A subset of weather data from Open-Meteo, including variables like temperature, humidity, wind speed, and more.
    """
)

st.sidebar.title("Pages")
#st.sidebar.markdown("Select a page from the sidebar menu to explore the data.")
