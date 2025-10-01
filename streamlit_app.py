import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Open Meteo App", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Data Table", "Data Plot", "Extra Page", "Meme Page"])

if page == "Home":
    st.title("🌍 Open Meteo Data Explorer")
    st.write("Welcome! Use the sidebar to navigate.")
    
elif page == "Data Table":
    st.title("📊 Data Table")
    df = pd.read_csv("open-meteo-subset.csv")
    st.dataframe(df.head())

elif page == "Data Plot":
    st.title("📈 Data Plot")
    st.write("Here you’d put the plotting code from page 2.")

elif page == "Extra Page":
    st.title("ℹ️ Extra Page")
    st.write("Dummy content.")

elif page == "Meme Page":
    st.title("😂 Meme Page")
    st.write("Here goes your meme code.")
