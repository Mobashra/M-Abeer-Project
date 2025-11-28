import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import utils

st.set_page_config(page_title="Energy Explorer", page_icon="📊", layout="wide")
st.title("📊 Energy Production & Consumption")


# --- SIDEBAR NAVIGATION GROUPS ---
st.sidebar.markdown("### 🗺️ Exploration")
# The pages 01, 02, 03 will appear here naturally due to sorting

if st.sidebar.checkbox("Show Advanced Modules", value=True):
    st.sidebar.markdown("### 🔍 Diagnostics")
    # Pages 04, 05, 06 fall here visually
    
    st.sidebar.markdown("### 🔮 Prediction")
    # Pages 07, 08 fall here visually

# --- GLOBAL STATE CHECK ---
if "selected_price_area" not in st.session_state:
    st.warning("⚠️ No Price Area selected. Defaulting to NO1.")
    st.session_state["selected_price_area"] = "NO1"

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Data Selection")
    data_type = st.radio("Type", ["Production", "Consumption"])
    selected_year = st.selectbox("Year", [2021, 2022, 2023, 2024], index=0)
    
    st.divider()
    st.info(f"📍 Active Region: **{st.session_state['selected_price_area']}**")

# --- LOAD DATA ---
with st.spinner(f"Loading {selected_year} data for {st.session_state['selected_price_area']}..."):
    df = utils.load_yearly_data(data_type, selected_year)

if df.empty:
    st.error(f"No data found for {selected_year}. Please ensure MongoDB is connected.")
    st.stop()

# Filter by Global State Area
current_area = st.session_state["selected_price_area"]
df_area = df[df['price_area'] == current_area].copy()

if df_area.empty:
    st.warning(f"No {data_type} data for {current_area} in {selected_year}.")
    st.stop()

# --- MAIN DASHBOARD ---
val_col = 'mwh' # Standardized in utils.py

# 1. METRICS ROW
total_vol = df_area[val_col].sum() / 1e6 # TWh
avg_vol = df_area[val_col].mean()
peak_vol = df_area[val_col].max()

m1, m2, m3 = st.columns(3)
m1.metric("Total Volume", f"{total_vol:.2f} TWh")
m2.metric("Average Hourly", f"{avg_vol:.2f} MWh")
m3.metric("Peak Hour", f"{peak_vol:.2f} MWh")

st.divider()

# 2. CHARTS LAYOUT
c1, c2 = st.columns([1, 2])

with c1:
    st.subheader("Market Share")
    # Aggregation
    pie_data = df_area.groupby('group')[val_col].sum().reset_index().sort_values(val_col, ascending=False)
    
    fig_pie = px.pie(
        pie_data, values=val_col, names='group',
        hole=0.4, 
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig_pie.update_layout(legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    st.subheader("Time Series Analysis")
    # Downsample for performance if needed, but Plotly handles 8760 points okay
    # We allow filtering specific groups
    all_groups = sorted(df_area['group'].unique())
    sel_groups = st.multiselect("Filter Groups", all_groups, default=all_groups[:2])
    
    if sel_groups:
        mask = df_area['group'].isin(sel_groups)
        fig_line = px.line(
            df_area[mask], x='date', y=val_col, color='group',
            labels={'mwh': 'MWh', 'date': 'Time'},
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_line.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Select at least one group to view the timeline.")

with st.expander("🔎 View Raw Data"):
    st.dataframe(df_area.head(1000), use_container_width=True)