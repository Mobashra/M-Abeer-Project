import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

@st.cache_data
def load_data():
    return pd.read_csv("open-meteo-subset.csv")

st.title("📈 Data Plot")

# Load dataset
df = load_data()

# --- Step 1: Month range selection ---
# Assume first column is "Month" or similar; if not, we'll use index
if "Month" in df.columns:
    months = df["Month"].tolist()
    df = df.set_index("Month")
else:
    months = list(range(1, len(df) + 1))
    df.index = months

selected_range = st.select_slider(
    "Select month range",
    options=months,
    value=(months[0], months[0])  # default: first month
)

# Subset data
if isinstance(selected_range, tuple):
    start, end = selected_range
    mask = (df.index >= start) & (df.index <= end)
    subset = df.loc[mask]
else:
    subset = df.loc[[selected_range]]

# --- Step 2: Column selection ---
columns = list(df.columns)
choice = st.selectbox("Select a column to plot", ["All"] + columns)

# --- Step 3: Plot ---
fig, ax = plt.subplots(figsize=(10, 5))

if choice == "All":
    subset.plot(ax=ax)
else:
    subset[choice].plot(ax=ax, label=choice)
    ax.legend()

ax.set_title("Open Meteo Data")
ax.set_xlabel("Month")
ax.set_ylabel("Values")
ax.grid(True, linestyle="--", alpha=0.6)

st.pyplot(fig)
