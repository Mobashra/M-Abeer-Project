import streamlit as st
import pandas as pd

# Caching to speed up reloads
@st.cache_data
def load_data():
    return pd.read_csv("open-meteo-subset.csv")

st.title("📊 Data Table")
df = load_data()

# Show table with line chart preview
st.write("### Dataset Overview")
st.dataframe(
    df.T.style.bar(color="lightblue", axis=1),  # Transposed for row view
    use_container_width=True
)

# Alternative with st.data_editor + LineChartColumn
st.write("### Table with LineChartColumn Example")

if "st" in dir(st):  # Check Streamlit version supports LineChartColumn
    from streamlit import column_config

    st.dataframe(
        df.T,
        column_config={
            df.columns[0]: column_config.LineChartColumn("First Month")
        },
        use_container_width=True
    )
