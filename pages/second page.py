import streamlit as st
import pandas as pd
from streamlit import column_config

# Caching to speed up reloads
@st.cache_data
def load_data():
    return pd.read_csv("open-meteo-subset.csv")

st.title("📊 Data Table")
df = load_data()

st.write("### Variables with First Month Value and Trend Preview")

# Build summary table:
# - One row per variable (CSV column)
# - First month value
# - Full series for sparkline
summary = pd.DataFrame({
    "Variable": df.columns,
    "First Month": [df[col].iloc[0] for col in df.columns],
    "Trend": [df[col].tolist() for col in df.columns]
})

st.dataframe(
    summary,
    column_config={
        "First Month": st.column_config.NumberColumn("First Month Value"),
        "Trend": column_config.LineChartColumn("Data Trend")
    },
    hide_index=True,
    use_container_width=True,
)
