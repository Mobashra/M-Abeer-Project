import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

@st.cache_data
def load_data():
    return pd.read_csv("open-meteo-subset.csv")

st.title("📈 Data Plot")

# Load dataset
df = load_data()

# --- Step 0: Ensure datetime is parsed ---
datetime_col = df.columns[0]  # first column assumed to be datetime
df[datetime_col] = pd.to_datetime(df[datetime_col])
df['Month'] = df[datetime_col].dt.month  # extract month number

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

# Drop the helper 'Month' column for plotting
subset_plot = subset.drop(columns=['Month'])

# --- Step 2: Column selection ---
columns = list(subset_plot.columns)
choice = st.selectbox("Select a column to plot", ["All"] + columns)

# --- Step 3: Plot ---
fig, ax = plt.subplots(figsize=(12, 5))

if choice == "All":
    subset_plot.plot(ax=ax)
else:
    subset_plot[choice].plot(ax=ax, label=choice)
    ax.legend()

ax.set_title("Open Meteo Data")
ax.set_xlabel("Datetime")
ax.set_ylabel("Values")
ax.grid(True, linestyle="--", alpha=0.6)

# --- Step 4: Limit x-axis to selected month(s) ---
ax.set_xlim(subset_plot[datetime_col].min(), subset_plot[datetime_col].max())

st.pyplot(fig)
