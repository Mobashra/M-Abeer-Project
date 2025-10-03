import streamlit as st
import pandas as pd
from streamlit import column_config


# Loading data with caching
@st.cache_data
def load_data():
    df = pd.read_csv("open-meteo-subset.csv", parse_dates = ["time"])
    df["month"] = df["time"].dt.month # Extract month as number
    return df

st.title("📊 Data Table")
st.markdown("### January Overview")
st.markdown("This table shows the variables and a small trend preview for the month.")

df = load_data()

# Filter data for January
january = df[df["month"] == 1]

# Build summary df with variable names and January trends
variables = df.columns.drop(["time", "month"]) # Exclude non-numeric columns

summary = pd.DataFrame({
    "Variable": variables,
    
    # we take the January data (january[var]) for each variable,
    # convert it to a Python list, resulting in column of lists.
    # Streamlit can render  this as small line charts.
    "January Trend": [january[var].tolist() for var in variables]
})


st.markdown("---")


# Displays a pandas DataFrame (summary) as an interactive table
# You can sort, resize, and scroll through the table.
st.dataframe(
    summary,
    column_config = {
        
        # the column "January Trend" is turned into a sparkline-style line chart 
        "January Trend": column_config.LineChartColumn("January Trend"),
    },
    hide_index = True,
    use_container_width = True,
)


