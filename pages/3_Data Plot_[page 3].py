import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

@st.cache_data
def load_data():
    return pd.read_csv("open-meteo-subset.csv")

st.title("📈 Data Plot")

# Load dataset
df = load_data()

# --- Step 0: Parse datetime ---
datetime_col = df.columns[0]  # first column assumed to be datetime
df[datetime_col] = pd.to_datetime(df[datetime_col])
df['Month'] = df[datetime_col].dt.month  # extract month

# --- Step 1: Month range selection ---
months = list(range(1, 13))  # 12 months
selected_range = st.select_slider(
    "Select month range",
    options=months,
    value=(months[0], months[0])  # default: January
)

# Filter data based on selected month(s)
if isinstance(selected_range, tuple):
    start, end = selected_range
    subset = df[(df['Month'] >= start) & (df['Month'] <= end)]
else:
    subset = df[df['Month'] == selected_range]

# --- Step 2: Set datetime as index for plotting ---
subset_plot = subset.set_index(datetime_col)

# Only keep numeric columns for plotting
numeric_columns = subset_plot.select_dtypes(include='number').columns.tolist()

# --- Step 3: Column selection ---
choice = st.selectbox("Select a column to plot", ["All"] + numeric_columns)

# --- Step 4: Plot ---

fig, ax = plt.subplots(figsize=(14, 7))

if choice == "All":
    subset_plot[numeric_columns].plot(ax=ax)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')  # move outside
else:
    subset_plot[choice].plot(ax=ax, label=choice)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')  # move outside

ax.set_title("Graph of all the variables" if choice == "All" else f"Graph of {choice}")
ax.set_xlabel("Time")
ax.set_ylabel("Range of values of the variables")
ax.grid(True, linestyle="--", alpha=0.3)

st.pyplot(fig)

