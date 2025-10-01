import streamlit as st

from st_pages import Page, show_pages, add_page_title

# Optional -- adds the title and icon to the current page
#add_page_title()

# Specify what pages should be shown in the sidebar, and what their titles 
# and icons should be
show_pages(
    [
        #Page("streamlit_app.py", "Home", "🏠"),
        
        Page("pages/second page.py", "Page 2", "Data Table"),
    ]
)


st.set_page_config(page_title="Open Meteo App", layout="wide")

st.title("🌍 Open Meteo Data Explorer")
st.write("Welcome to the Open Meteo data app. Use the sidebar to navigate between pages.")

st.sidebar.title("Navigation")
st.sidebar.markdown("Select a page from the sidebar menu to explore the data.")
