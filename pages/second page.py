import streamlit as st
import pandas as pd
from streamlit import column_config

@st.cache_data
def load_data():
    return pd.read_csv("open-meteo-subset.csv")

st.title("📊 Data Table")
df = load_data()

st.write("### Variables with First Month Value and Trend Preview")

# Build summary table
summary = pd.DataFrame({
    "Variable": df.columns,
    "First Month": [df[col].iloc[0] for col in df.columns],
    "Trend": [pd.Series(df[col].values) for col in df.columns]  # <-- fix here
})

# Show table with LineChartColumn for row-wise trends
st.dataframe(
    summary,
    column_config={
        "First Month": st.column_config.NumberColumn("First Month Value"),
        "Trend": column_config.LineChartColumn("Data Trend"),
    },
    hide_index=True,
    use_container_width=True,
)
