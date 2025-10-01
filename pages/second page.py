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
    "First Value (Jan)": [january[var].iloc[0] for var in variables],
    "Trend (Jan)": [pd.Series(january[var].values) for var in variables]
})

# Show table with LineChartColumn
st.dataframe(
    summary,
    column_config={
        "First Value (Jan)": st.column_config.NumberColumn("First January Value"),
        "Trend (Jan)": column_config.LineChartColumn("January Trend"),
    },
    hide_index=True,
    use_container_width=True,
)
