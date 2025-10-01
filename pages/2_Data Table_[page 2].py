import streamlit as st
import pandas as pd
from streamlit import column_config

@st.cache_data
def load_data():
    df = pd.read_csv("open-meteo-subset.csv", parse_dates=["time"])
    df["month"] = df["time"].dt.month
    return df

st.title("📊 Data Table")
st.markdown("### January Overview: First Value & Trend")

df = load_data()

# Filter January
january = df[df["month"] == 1]

# Build summary table
variables = df.columns.drop(["time", "month"])
summary = pd.DataFrame({
    "Variable": variables,
    "First January Value": [january[var].iloc[0] for var in variables],
    "January Trend": [january[var].tolist() for var in variables]
})

# Display table with enhanced column formatting
st.dataframe(
    summary,
    column_config={
        "First January Value": column_config.NumberColumn(
            "First January Value",
            format="%.2f",
            help="First recorded value of the month",
            min_value=summary["First January Value"].min(),
            max_value=summary["First January Value"].max()
        ),
        "January Trend": column_config.LineChartColumn(
            "January Trend",
            color="#1f77b4",
            line_width=2,
            height=60
        ),
    },
    hide_index=True,
    use_container_width=True,
)
