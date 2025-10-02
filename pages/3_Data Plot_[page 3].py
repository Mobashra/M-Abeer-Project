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

# --- Step 4: Plot ---
fig, ax = plt.subplots(figsize=(12, 5))

if choice == "All":
    subset_plot[numeric_columns].plot(ax=ax)
    ax.legend(bbox_to_anchor=(1, 1), loc='upper left')
else:
    subset_plot[choice].plot(ax=ax, label=choice)
    ax.legend(bbox_to_anchor=(1, 1), loc='upper left')

# ----- Customize axis labels -----
ax.set_title("Graph of all the variables" if choice == "All" else f"Graph of {choice}",
             fontsize=14, pad=15)  # title font size

ax.set_xlabel("Time", fontsize=12, labelpad=10)   # x-axis label font size + padding
ax.set_ylabel("Range of values of the variables", fontsize=12, labelpad=10)  # y-axis

# ----- Customize tick labels (numbers) -----
ax.tick_params(axis="x", labelsize=10)  # font size of x-axis ticks
ax.tick_params(axis="y", labelsize=10)  # font size of y-axis ticks

# ----- Move x-axis position (example: put it on top) -----
ax.xaxis.set_ticks_position("bottom")   # can be 'bottom' or 'top'
ax.xaxis.set_label_position("bottom")   # move x-axis label too

ax.grid(True, linestyle="--", alpha=0.6)

st.pyplot(fig)

