import streamlit as st
import pandas as pd
from streamlit import column_config

@st.cache_data
def load_data():
    df = pd.read_csv("open-meteo-subset.csv", parse_dates = ["time"])
    df["month"] = df["time"].dt.month
    return df


st.title("📊 Data Table")
st.markdown("### January Overview")
st.markdown("This table shows the variables and a small trend preview for the month.")

df = load_data()

# Filter January
january = df[df["month"] == 1]

# Build summary table
variables = df.columns.drop(["time", "month"])
summary = pd.DataFrame({
    "Variable": variables,
    "January Trend": [january[var].tolist() for var in variables]
})

st.markdown("---")

st.dataframe(
    summary,
    column_config = {
        "January Trend": column_config.LineChartColumn("January Trend"),
    },
    hide_index = True,
    use_container_width = True,
)


