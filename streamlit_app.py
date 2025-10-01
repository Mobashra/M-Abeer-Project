import streamlit as st

from st_pages import Page, show_pages, add_page_title



st.set_page_config(page_title="Open Meteo App", layout="wide")

st.title("🌍 Open Meteo Data Explorer")
st.write("Welcome to the Open Meteo data app. Use the sidebar to navigate between pages.")

st.sidebar.title("Navigation")
st.sidebar.markdown("Select a page from the sidebar menu to explore the data.")
