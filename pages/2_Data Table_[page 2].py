import streamlit as st
import pandas as pd
from streamlit import column_config

@st.cache_data
def load_data():
    df = pd.read_csv("open-meteo-subset.csv", parse_dates=["time"])
    df["month"] = df["time"].dt.month
    return df

st.title("📊 Data Table")
df = load_data()

st.write("### Variables with January First Value and Trend Preview")

# Filter January only
january = df[df["month"] == 1]

# Build summary table
variables = df.columns.drop(["time", "month"])
summary = pd.DataFrame({
    "Variable": variables,
    "First January Value": [january[var].iloc[0] for var in variables],
    "January Trend": [january[var].tolist() for var in variables]  # keep lists here
})

# Show table with LineChartColumn
st.dataframe(
    summary,
    column_config={
        "First January Value": st.column_config.NumberColumn("First January Value"),
        "January Trend": column_config.LineChartColumn("January Trend"),
    },
    hide_index=True,
    use_container_width=True,
)
