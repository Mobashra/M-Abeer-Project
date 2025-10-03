import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import calendar

# --- Load data ---
@st.cache_data
def load_data():
    return pd.read_csv("open-meteo-subset.csv")

st.title("📈 Data Plot")

df = load_data()

# --- Prepare datetime and month columns ---
datetime_col = df.columns[0]  
df[datetime_col] = pd.to_datetime(df[datetime_col])
df['Month'] = df[datetime_col].dt.month  

# --- Month names for slider ---
months = list(calendar.month_name)[1:]  

selected_range = st.select_slider(
    "Select month range",
    options=months,
    value=(months[0], months[0])  # default: January
)

# --- Filter data based on selected months ---
if isinstance(selected_range, tuple):
    start, end = [months.index(m) + 1 for m in selected_range]
    subset = df[(df['Month'] >= start) & (df['Month'] <= end)]
else:
    month_num = months.index(selected_range) + 1
    subset = df[df['Month'] == month_num]

# --- Prepare data for plotting ---
subset_plot = subset.set_index(datetime_col)
numeric_columns = subset_plot.select_dtypes(include='number').columns.tolist()
choice = st.selectbox("Select a column to plot", ["All"] + numeric_columns)

# --- Plot with Plotly Graph Objects ---
fig = go.Figure()

if choice == "All":
    for col in numeric_columns:
        fig.add_trace(go.Scatter(
            x=subset_plot.index,
            y=subset_plot[col],
            mode="lines",
            name=col
        ))
    plot_title = "Graph of all variables"
else:
    fig.add_trace(go.Scatter(
        x=subset_plot.index,
        y=subset_plot[choice],
        mode="lines",
        name=choice
    ))
    plot_title = f"Graph of {choice}"

# --- Add selected month(s) to title ---
if isinstance(selected_range, tuple):
    plot_title += f" ({selected_range[0]} - {selected_range[1]})"
else:
    plot_title += f" ({selected_range})"

# --- Layout settings ---
fig.update_layout(
    title=plot_title,
    xaxis_title="Time",
    yaxis_title="Range of values of the variables",
    template="plotly_white",
    legend=dict(x=1, y=1, bgcolor="rgba(0,0,0,0)")
)


fig.update_xaxes(dtick = "M1", tickformat = "%b")
# --- Show chart in Streamlit ---
st.plotly_chart(fig, use_container_width=True)
