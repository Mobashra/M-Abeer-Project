import streamlit as st
import utils

st.set_page_config(page_title="Energy Atlas", page_icon="⚡", layout="wide")

# Render the sidebar grouping
utils.render_sidebar()

st.title("⚡ Norwegian Energy & Weather Atlas")

st.info("""
**Welcome!** This application requires you to select a geographical context first.
""")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 🚀 Step 1: Initialization")
    st.markdown("Please go to the **Map Selector** page to select a Price Area and specific coordinates.")
    
    st.page_link("pages/01_Map_Selector.py", label="Open Map Selector", icon="🗺️")

with col2:
    st.markdown("### 📊 Project Structure")
    st.markdown("""
    * **🟦 Explorative:** Visualizing history (Map, Energy, Weather).
    * **🟧 Anomalies:** Diagnostic analysis (Correlations, Outliers).
    * **🟪 Predictive:** Advanced modelling (Snow Drift, Forecasting).
    """)

st.divider()
st.caption("Developed for Data Science Engineering Project")