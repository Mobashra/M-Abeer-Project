import streamlit as st
import pandas as pd
from streamlit import column_config

@st.cache_data
def load_data():
    df = pd.read_csv("open-meteo-subset.csv", parse_dates = ["time"])
    df["month"] = df["time"].dt.month
    return df

# View the data in table format
df = load_data()
st.dataframe(df.drop(columns=["month"]), use_container_width = True)

st.title("📊 Data Table")
st.markdown("### January Overview: First Value & Trend")
st.markdown(
    "This table shows the **first recorded value in January** for each variable "
    "and a small trend preview for the month."
)

df = load_data()

# Filter January
january = df[df["month"] == 1]

# Build summary table
variables = df.columns.drop(["time", "month"])
summary = pd.DataFrame({
    "Variable": variables,
    "First Recorded Value": [january[var].iloc[0] for var in variables],
    "January Trend": [january[var].tolist() for var in variables]
})

# Adding some spacing before the table
st.markdown("---")

# Showing table with enhanced column configuration
st.dataframe(
    summary,
    column_config={
        "First Recorded Value": column_config.NumberColumn(
            "First Recorded Value",
            format="%.2f",
            help="First recorded value of the month"
        ),
        "January Trend": column_config.LineChartColumn("January Trend"),
    },
    hide_index=True,
    use_container_width=True,
)

st.markdown(
    """
    **Notes:**  
    - `First January Value` is the first value of the all the variables recorded in January.  
    - `January Trend` shows a mini chart of the variable's progression over the month.  
    """
)
