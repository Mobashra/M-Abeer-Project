import streamlit as st
import plotly.express as px
import pandas as pd
import utils 

st.set_page_config(page_title="Elhub Data Explorer", layout="wide")
st.title("📊 Elhub Data Explorer")

# --- 1. SAFETY DEFAULTS ---
if "selected_price_area" not in st.session_state:
    st.session_state["selected_price_area"] = "NO1"

# --- 2. CONTROLS (Top Level) ---
col1, col2 = st.columns(2)
with col1:
    data_type = st.radio("Data Source", ["Production", "Consumption"], horizontal=True)
with col2:
    # Allow 2021-2024
    selected_year = st.selectbox("Select Year", [2021, 2022, 2023, 2024], index=0)

# --- 3. LOAD DATA ---
# Uses the new function in utils.py
with st.spinner(f"Loading {data_type} data for {selected_year}..."):
    df = utils.load_yearly_data(data_type, selected_year)

if df.empty:
    st.warning(f"No data found for **{data_type}** in **{selected_year}**.")
    st.stop()

# --- 4. VISUALIZATION ---
col_left, col_right = st.columns(2)

# LEFT: PIE CHART
with col_left:
    st.subheader(f"{data_type} Share")
    
    # Area Selector
    price_areas = sorted(df['price_area'].unique())
    curr = st.session_state["selected_price_area"]
    idx = price_areas.index(curr) if curr in price_areas else 0
    
    selected_area = st.selectbox("Price Area:", price_areas, index=idx)
    
    # Sync state
    if selected_area != st.session_state["selected_price_area"]:
        st.session_state["selected_price_area"] = selected_area
        st.rerun()

    # Filter & Plot
    df_area = df[df['price_area'] == selected_area]
    pie_data = df_area.groupby('group')['mwh'].sum().reset_index()
    
    fig1 = px.pie(pie_data, names='group', values='mwh', hole=0.4,
                  title=f"Total {data_type} by Group ({selected_area})")
    fig1.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig1, use_container_width=True)

# RIGHT: LINE CHART
with col_right:
    st.subheader(f"Daily Trend ({selected_year})")
    
    groups = sorted(df['group'].unique())
    selected_groups = st.multiselect("Filter Groups:", groups, default=groups)
    
    if selected_groups:
        # Filter
        df_line = df_area[df_area['group'].isin(selected_groups)].copy()
        
        # Resample to Daily (D) to make the chart readable and fast
        # (8760 hourly points is too crowded)
        df_line.set_index('date', inplace=True)
        df_resampled = df_line.groupby('group')['mwh'].resample('D').sum().reset_index()
        
        fig2 = px.line(
            df_resampled, 
            x='date', 
            y='mwh', 
            color='group',
            title=f"Daily {data_type} Trend",
            labels={'mwh': 'MWh', 'date': 'Date'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Select at least one group to see the trend.")

# --- 5. RAW DATA ---
with st.expander("View Raw Data (First 100 rows)"):
    st.dataframe(df.head(100), use_container_width=True)