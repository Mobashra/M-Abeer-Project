import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import calendar

# --- Load data ---
@st.cache_data
def load_data():
    return pd.read_csv("open-meteo-subset.csv")

st.title("📈 Data Plot")

df = load_data()

# --- Prepare datetime and month ---
datetime_col = df.columns[0]  # first column assumed to be datetime
df[datetime_col] = pd.to_datetime(df[datetime_col])
df['Month'] = df[datetime_col].dt.month  # extract month

# --- Month names for slider ---
months = list(calendar.month_name)[1:]  # ['January', 'February', ..., 'December']

selected_range = st.select_slider(
    "Select month range",
    options=months,
    value=(months[0], months[0])  # default: January
)

# --- Convert month names to numbers for filtering ---
if isinstance(selected_range, tuple):
    start, end = [months.index(m) + 1 for m in selected_range]
    subset = df[(df['Month'] >= start) & (df['Month'] <= end)]
else:
    month_num = months.index(selected_range) + 1
    subset = df[df['Month'] == month_num]

# --- Prepare plotting ---
subset_plot = subset.set_index(datetime_col)
numeric_columns = subset_plot.select_dtypes(include='number').columns.tolist()
choice = st.selectbox("Select a column to plot", ["All"] + numeric_columns)

# --- Plot ---
fig, ax = plt.subplots(figsize=(12, 5))
if choice == "All":
    subset_plot[numeric_columns].plot(ax=ax)
    ax.legend(bbox_to_anchor=(1, 1), loc='upper left')
else:
    subset_plot[choice].plot(ax=ax, label=choice)
    ax.legend(bbox_to_anchor=(1, 1), loc='upper left')

# --- Titles and labels ---
plot_title = "Graph of all variables" if choice == "All" else f"Graph of {choice}"
# Add selected month(s) to title
if isinstance(selected_range, tuple):
    plot_title += f" ({selected_range[0]} - {selected_range[1]})"
else:
    plot_title += f" ({selected_range})"

ax.set_title(plot_title, fontsize=14, pad=15)
ax.set_xlabel("Time", fontsize=12, labelpad=10)
ax.set_ylabel("Range of values of the variables", fontsize=12, labelpad=10)
ax.tick_params(axis="x", labelsize=10)
ax.tick_params(axis="y", labelsize=10)
ax.xaxis.set_ticks_position("bottom")
ax.xaxis.set_label_position("bottom")
ax.grid(True, linestyle="--", alpha=0.6)

# --- Show plot ---
st.pyplot(fig)
